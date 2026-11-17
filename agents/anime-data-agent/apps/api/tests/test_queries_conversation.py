"""Real snapshot acceptance checks and isolated transactional history tests."""
import asyncio
import csv
import hashlib
import json
import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import httpx
from pydantic import ValidationError

from anime_agent.config import ROOT, Settings
from anime_agent.conversation import build_agent
from anime_agent.history import Conflict, History, NotFound
from anime_agent.main import create_app
from anime_agent.models import ActivateRequest, Filters, Query, TurnRequest
from anime_agent.queries import DatasetUnavailable, InvalidQuery, Repository


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pointer = ROOT / 'data/processed/current.json'
        cls.repo = Repository(cls.pointer)
        cls.graph = build_agent(cls.repo)
        pointer = json.loads(cls.pointer.read_text())
        with (cls.pointer.parent / pointer['load_id'] / 'source.csv').open(encoding='utf-8-sig', newline='') as stream:
            cls.raw = list(csv.DictReader(stream))

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='anime-history-')
        self.addCleanup(self.folder.cleanup)
        self.db_path = Path(self.folder.name) / 'history.sqlite3'
        self.history = History(self.db_path)

    def test_real_filtered_rank_matches_original_csv(self):
        expected = [r for r in self.raw if r['type'] == 'tv' and 'Fantasy' in r['genres'].split(';')
                    and 0 < int(r['episodes']) <= 26 and float(r['score']) > 0]
        expected.sort(key=lambda r: (-float(r['score']), int(r['anime_id'])))
        q = Query(filters=Filters(formats=['tv'], genres=['Fantasy'], max_episodes=26), limit=10)
        result = self.repo.execute(q)
        self.assertEqual([r['anime_id'] for r in result.rows], [int(r['anime_id']) for r in expected[:10]])
        self.assertEqual(result.total, len(expected))
        self.assertIsNone(result.applied_query.filters.min_votes)
        self.assertEqual(result.rows[0]['score'], float(expected[0]['score']))

    def test_votes_optional_and_popularity_direction(self):
        result = self.repo.execute(Query(order_by='popularity', filters=Filters(min_votes=1000)))
        self.assertEqual(result.applied_query.direction, 'asc')
        expected = sorted((r for r in self.raw if int(r['scored_by']) >= 1000), key=lambda r: (int(r['popularity']), int(r['anime_id'])))
        self.assertEqual([r['anime_id'] for r in result.rows], [int(r['anime_id']) for r in expected[:10]])

    def test_aggregate_uses_all_filtered_rows_not_limit(self):
        result = self.repo.execute(Query(kind='aggregate', limit=1, filters=Filters(formats=['tv'], year_from=2020)))
        expected = Counter(r['start_date'][:4] for r in self.raw if r['type'] == 'tv' and int(r['start_date'][:4]) >= 2020)
        self.assertEqual({g['key']: g['count'] for g in result.groups}, dict(expected))
        self.assertEqual(sum(g['count'] for g in result.groups), result.total)
        self.assertEqual(len(result.evidence['selected_ids']), result.total)

    def test_multiple_genre_operator_and_validation(self):
        with self.assertRaises(ValidationError):
            Filters(genres=['Action', 'Fantasy'])
        every = self.repo.execute(Query(filters=Filters(genres=['Action', 'Fantasy'], genre_mode='all')))
        either = self.repo.execute(Query(filters=Filters(genres=['Action', 'Fantasy'], genre_mode='any')))
        self.assertGreater(either.total, every.total)
        for row in every.rows:
            self.assertTrue({'Action', 'Fantasy'} <= set(row['genres']))
        with self.assertRaises(ValidationError):
            Query.model_validate({'order_by': 'members'})
        with self.assertRaises(InvalidQuery):
            self.repo.execute(Query(filters=Filters(genres=['nonexistent-genre'])))

    def test_empty_details_and_comparison(self):
        self.assertEqual(self.repo.execute(Query(kind='search', filters=Filters(title='NoSuchAnimeXYZ123'))).status, 'empty')
        detail = self.repo.execute(Query(kind='detail', ids=[1535]))
        self.assertEqual(detail.rows[0]['title'], 'Death Note')
        self.assertIn('synopsis', detail.rows[0])
        comparison = self.repo.execute(Query(kind='compare', ids=[1535, 16498]))
        self.assertEqual(comparison.evidence['shown_ids'], [1535, 16498])
        with self.assertRaises(ValidationError):
            Query(kind='compare', ids=[1535, 1535])
        with self.assertRaises(InvalidQuery):
            self.repo.execute(Query(kind='detail', ids=[999999999]))

    def test_full_conversation_branch_selection_and_restart(self):
        cid = self.history.create()['id']
        first = self.history.append(cid, TurnRequest(message='Muéstrame los 10 animes de fantasía mejor puntuados', base_turn_id=None), self.graph)
        second = self.history.append(cid, TurnRequest(message='Solo series de televisión de máximo 26 episodios', base_turn_id=first['id']), self.graph)
        f = second['response']['state']['query']['filters']
        self.assertEqual(f['genres'], ['Fantasy'])
        self.assertEqual(f['formats'], ['tv'])
        self.assertEqual(f['max_episodes'], 26)
        ids = [r['anime_id'] for r in second['response']['result']['rows'][:2]]
        comparison = self.history.append(cid, TurnRequest(message='Compara estos dos', base_turn_id=second['id'], selected_ids=ids), self.graph)
        self.assertEqual(comparison['response']['result']['evidence']['shown_ids'], ids)
        self.assertEqual(comparison['response']['state']['query']['filters'], f)
        self.history.activate(cid, ActivateRequest(turn_id=first['id'], expected_active_turn_id=comparison['id']))
        branch = self.history.append(cid, TurnRequest(message='Solo TV', base_turn_id=first['id']), self.graph)
        self.assertEqual(branch['parent_turn_id'], first['id'])
        self.assertIsNone(branch['response']['state']['query']['filters']['max_episodes'])
        restarted = History(self.db_path).get(cid)
        self.assertEqual(restarted['active_turn_id'], branch['id'])
        self.assertEqual(len(restarted['turns']), 4)
        self.assertEqual(restarted['turns'][0], first)

    def test_clarification_retains_result_and_filters(self):
        cid = self.history.create()['id']
        first = self.history.append(cid, TurnRequest(message='Busca Death Note', base_turn_id=None), self.graph)
        unsupported = self.history.append(cid, TurnRequest(message='Solo TV y con doblaje costarricense', base_turn_id=first['id']), self.graph)
        self.assertEqual(unsupported['response']['status'], 'clarification')
        self.assertEqual(unsupported['response']['state'], first['response']['state'])
        self.assertEqual(unsupported['response']['result'], first['response']['result'])
        invalid_selection = self.history.append(cid, TurnRequest(message='Compara estos dos', base_turn_id=unsupported['id'], selected_ids=[99999, 88888]), self.graph)
        self.assertEqual(invalid_selection['response']['status'], 'clarification')
        self.assertEqual(invalid_selection['response']['result'], first['response']['result'])

    def test_spanish_names_aggregate_explanation_and_ambiguous_reference(self):
        cid = self.history.create()['id']
        ambiguous = self.history.append(cid, TurnRequest(message='Compara estos dos', base_turn_id=None), self.graph)
        self.assertEqual(ambiguous['response']['status'], 'clarification')
        pair = self.history.append(cid, TurnRequest(message='Compara Death Note con Shingeki no Kyojin', base_turn_id=ambiguous['id']), self.graph)
        self.assertEqual(pair['response']['result']['evidence']['shown_ids'], [1535, 16498])
        counts = self.history.append(cid, TurnRequest(message='¿Cuántas series se estrenaron por año desde 2020?', base_turn_id=pair['id']), self.graph)
        self.assertEqual(counts['response']['result']['kind'], 'aggregate')
        explain = self.history.append(cid, TurnRequest(message='¿Qué filtros aplicaste y de dónde vienen los datos?', base_turn_id=counts['id']), self.graph)
        self.assertEqual(explain['response']['visualization_action'], 'retain')
        self.assertEqual(explain['response']['result'], counts['response']['result'])

    def test_isolation_stale_turn_idempotency_and_rollback(self):
        cid = self.history.create()['id']
        other = self.history.create()['id']
        request = TurnRequest(message='Busca Death Note', base_turn_id=None, request_id='repeat-safe')
        first = self.history.append(cid, request, self.graph)
        self.assertEqual(self.history.append(cid, request, self.graph), first)
        self.assertEqual(len(self.history.get(cid)['turns']), 1)
        with self.assertRaises(Conflict):
            self.history.append(cid, TurnRequest(message='Busca Naruto', base_turn_id=None), self.graph)
        with self.assertRaises(NotFound):
            self.history.activate(other, ActivateRequest(turn_id=first['id'], expected_active_turn_id=None))
        class Broken:
            def invoke(self, work):
                raise RuntimeError('injected failure')
        with self.assertRaises(RuntimeError):
            self.history.append(cid, TurnRequest(message='Solo TV', base_turn_id=first['id']), Broken())
        self.assertEqual(self.history.get(cid)['active_turn_id'], first['id'])
        self.assertEqual(len(self.history.get(cid)['turns']), 1)

    def test_missing_corrupt_or_escaping_snapshot_rejected(self):
        with self.assertRaises(DatasetUnavailable):
            Repository(Path(self.folder.name) / 'missing.json')
        pointer = Path(self.folder.name) / 'current.json'
        pointer.write_text(json.dumps({'manifest': '../outside.json', 'manifest_sha256': 'bad'}))
        with self.assertRaises(DatasetUnavailable):
            Repository(pointer)
        manifest = Path(self.folder.name) / 'manifest.json'
        manifest.write_text('{}')
        pointer.write_text(json.dumps({'manifest': 'manifest.json', 'manifest_sha256': 'bad'}))
        with self.assertRaises(DatasetUnavailable):
            Repository(pointer)

    @unittest.skipUnless(os.environ.get('ANIME_HTTP_TESTS') == '1', 'Opt-in ASGI test; this session cannot run the event loop reliably.')
    def test_http_contracts_in_process(self):
        async def run():
            app = create_app(Settings(self.pointer, self.db_path))
            app.state.repository = self.repo
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                response = await client.get('/api/health')
                self.assertEqual(response.json()['dataset_status'], 'validated')
                self.assertEqual((await client.get('/api/anime/1535')).status_code, 200)
                self.assertEqual((await client.get('/api/anime/999999')).status_code, 404)
                self.assertEqual((await client.post('/api/query', json={'order_by': 'members'})).status_code, 422)
                self.assertEqual((await client.post('/api/query', json={'filters': {'genres': ['invalid']}})).status_code, 422)
                cid = (await client.post('/api/conversations')).json()['id']
                first = await client.post(f'/api/conversations/{cid}/turns', json={'message': 'Busca Death Note', 'base_turn_id': None})
                self.assertEqual(first.status_code, 200)
                stale = await client.post(f'/api/conversations/{cid}/turns', json={'message': 'Solo TV', 'base_turn_id': None})
                self.assertEqual(stale.status_code, 409)
                self.assertEqual((await client.get('/api/conversations/absent')).status_code, 404)
                missing = create_app(Settings(Path(self.folder.name) / 'missing.json', self.db_path))
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=missing), base_url='http://test') as failed:
                    self.assertEqual((await failed.post('/api/query', json={})).status_code, 503)
                    self.assertEqual((await failed.get('/api/health')).json()['dataset_status'], 'unavailable')
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
