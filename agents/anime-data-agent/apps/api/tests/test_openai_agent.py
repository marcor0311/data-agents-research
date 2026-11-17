"""Phase-7 logic with scripted provider responses; never contacts or bills OpenAI."""
import copy
import json
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

import httpx

from anime_agent.config import ROOT, Settings
from anime_agent.conversation import build_agent
from anime_agent.history import Conflict, History
from anime_agent.models import Filters, Query, TurnRequest
from anime_agent.openai_agent import ModelInterpreter, ModelUnavailable, OpenAIClient, tool_schemas
from anime_agent.queries import Repository


def tool(name, arguments):
    return dict(id='simulated-response', status='completed', usage=dict(input_tokens=100, output_tokens=30),
                output=[dict(type='function_call', call_id='simulated-call', name=name, arguments=json.dumps(arguments))])


def catalog(query, mode='new', changes=None):
    return tool('query_catalog', dict(mode=mode, query=query.model_dump(), changed_fields=changes or []))


def present(ids=None, style='brief'):
    return tool('present_result', dict(highlighted_ids=ids or [], style=style))


class Scripted:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.inputs = []

    def complete(self, inputs, remaining):
        self.inputs.append(copy.deepcopy(inputs))
        if not self.responses:
            raise AssertionError('Unexpected extra provider call')
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class OpenAIAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Repository(ROOT / 'data/processed/current.json')
        cls.settings = Settings(ROOT/'data/processed/current.json', ROOT/'data/unused-test.sqlite3', agent_mode='openai', openai_api_key='test-placeholder-not-a-real-key')

    def run_model(self, provider, message='Petición de prueba', previous=None, selected=None):
        model = ModelInterpreter(self.repo, self.settings, provider)
        agent = build_agent(self.repo, model)
        request = TurnRequest(message=message, base_turn_id=None, selected_ids=selected or [])
        return agent.invoke(dict(previous=previous, request=request))['response']

    def baseline(self):
        q = Query(filters=Filters(formats=['tv'], genres=['Fantasy'], max_episodes=12), limit=5)
        return self.run_model(Scripted(catalog(q), present()), 'Cinco series de fantasía de máximo doce episodios')

    def test_strict_schemas_keep_title_and_require_all_properties(self):
        for schema in tool_schemas():
            def check(node):
                if isinstance(node, list):
                    for v in node: check(v)
                elif isinstance(node, dict):
                    if node.get('type') == 'object':
                        self.assertEqual(set(node['required']), set(node.get('properties', {})))
                        self.assertFalse(node['additionalProperties'])
                    for v in node.values(): check(v)
            check(schema['parameters'])
        search = next(t for t in tool_schemas() if t['name'] == 'search_titles')
        self.assertIn('title', search['parameters']['properties'])

    def test_new_query_uses_real_repository_and_records_usage(self):
        answer = self.baseline()
        expected = self.repo.execute(Query(filters=Filters(formats=['tv'], genres=['Fantasy'], max_episodes=12), limit=5))
        self.assertEqual(answer.result.evidence['shown_ids'], expected.evidence['shown_ids'])
        self.assertEqual(answer.interpreter, 'openai_tools')
        self.assertEqual(answer.model_run['requests'], 2)
        self.assertEqual(answer.model_run['input_tokens'], 200)
        self.assertNotIn('source_values', str(answer.model_run))

    def test_refinement_only_applies_listed_fields_and_can_clear_one(self):
        previous = self.baseline()
        patch = Query(filters=Filters(year_from=2020))
        answer = self.run_model(Scripted(catalog(patch, 'refine', ['filters.year_from']), present()), previous=previous)
        f = answer.state.query.filters
        self.assertEqual((f.formats, f.genres, f.max_episodes, f.year_from), (['tv'], ['Fantasy'], 12, 2020))
        self.assertEqual(answer.state.query.limit, 5)
        cleared = self.run_model(Scripted(catalog(Query(), 'refine', ['filters.max_episodes']), present()), previous=answer)
        self.assertIsNone(cleared.state.query.filters.max_episodes)
        self.assertEqual(cleared.state.query.filters.year_from, 2020)

    def test_selected_compare_preserves_filters_and_grounds_differences(self):
        previous = self.baseline()
        ids = previous.result.evidence['shown_ids'][:2]
        answer = self.run_model(Scripted(tool('query_selected', {'action':'compare'}), present(ids, 'detailed')), 'Compará estos dos', previous, ids)
        self.assertEqual(answer.result.evidence['shown_ids'], ids)
        self.assertEqual(answer.state.query.filters, previous.state.query.filters)
        self.assertIn('Diferencia absoluta', answer.explanation)

    def test_missing_selection_makes_no_provider_call(self):
        provider = Scripted()
        answer = self.run_model(provider, 'Compará estos dos', self.baseline())
        self.assertEqual(answer.status, 'clarification')
        self.assertEqual(answer.model_run['requests'], 0)
        self.assertEqual(provider.inputs, [])

    def test_explicit_empty_selection_does_not_reuse_old_selected_ids(self):
        previous = self.baseline()
        ids = previous.result.evidence['shown_ids'][:2]
        comparison = self.run_model(Scripted(tool('query_selected', {'action':'compare'}), present(ids)), 'Compará estos dos', previous, ids)
        provider = Scripted()
        answer = self.run_model(provider, 'Compará estos dos', comparison, [])
        self.assertEqual(answer.status, 'clarification')
        self.assertEqual(provider.inputs, [])

    def test_ambiguous_title_cannot_be_chosen_without_resolution(self):
        search = self.repo.execute(Query(kind='search', filters=Filters(title='Naruto'), order_by='title'))
        ids = [r['anime_id'] for r in search.rows]
        provider = Scripted(tool('search_titles', dict(title='Naruto', limit=10)),
                            catalog(Query(kind='detail', ids=[ids[-1]])),
                            tool('ask_clarification', dict(reason='ambiguous_title', candidate_ids=ids[:3])))
        answer = self.run_model(provider, 'Busco Naruto')
        self.assertEqual(answer.status, 'clarification')
        self.assertEqual(answer.model_run['tools'][1]['status'], 'rejected')
        self.assertIn('Candidatos', answer.explanation)

    def test_fabricated_highlight_rejected_and_unsupported_metric_retains_result(self):
        previous = self.baseline()
        provider = Scripted(tool('inspect_current', {}), present([99999999]),
                            tool('ask_clarification', dict(reason='unsupported_metric', candidate_ids=[])))
        answer = self.run_model(provider, 'Ordená por seguidores', previous)
        self.assertEqual(answer.status, 'clarification')
        self.assertEqual(answer.result, previous.result)
        self.assertEqual(answer.state, previous.state)
        self.assertEqual(answer.model_run['tools'][1]['status'], 'rejected')

    def test_provider_failure_rolls_back_without_fallback(self):
        with tempfile.TemporaryDirectory(prefix='anime-model-history-') as folder:
            history = History(Path(folder)/'history.sqlite3')
            cid = history.create()['id']
            graph = build_agent(self.repo, ModelInterpreter(self.repo, self.settings, Scripted(ModelUnavailable('Provider unavailable'))))
            with self.assertRaises(ModelUnavailable):
                history.append(cid, TurnRequest(message='Probando', base_turn_id=None), graph)
            self.assertEqual(history.get(cid)['turns'], [])

    def test_provider_http_errors_redact_body_and_settings_repr(self):
        def fail(request):
            return httpx.Response(401, json={'error': 'secret test-placeholder-not-a-real-key'})
        client = OpenAIClient(self.settings, httpx.MockTransport(fail))
        with self.assertRaises(ModelUnavailable) as caught:
            client.complete([{'role':'user','content':'test'}], 2)
        self.assertNotIn('test-placeholder', str(caught.exception))
        self.assertNotIn('test-placeholder', repr(self.settings))
        no_key = replace(self.settings, openai_api_key=None)
        with self.assertRaises(ModelUnavailable):
            OpenAIClient(no_key, httpx.MockTransport(fail)).complete([], 1)

    def test_provider_request_is_bounded_and_stateless(self):
        observed = []
        def success(request):
            observed.append(json.loads(request.content))
            return httpx.Response(200, json=present())
        client = OpenAIClient(self.settings, httpx.MockTransport(success))
        client.complete([{'role':'user','content':'test'}], 2)
        self.assertFalse(observed[0]['store'])
        self.assertFalse(observed[0]['parallel_tool_calls'])
        self.assertEqual(observed[0]['max_output_tokens'], 2048)
        self.assertNotIn('source_values', json.dumps(observed[0]))

    def test_429_distinguishes_quota_from_temporary_rate_limit_without_leaking_body(self):
        for code, expected in [('insufficient_quota', 'facturación insuficiente'), ('rate_limit_exceeded', 'límite temporal'),
                               ('credit_balance_exhausted', 'se agotaron los créditos'),
                               ('project_spend_limit_exceeded', 'límite de gasto del proyecto')]:
            with self.subTest(code=code):
                def fail(request):
                    return httpx.Response(429, json={'error': {'code': code, 'message': 'secret-provider-body'}})
                client = OpenAIClient(self.settings, httpx.MockTransport(fail))
                with self.assertRaises(ModelUnavailable) as caught:
                    client.complete([], 1)
                self.assertIn(expected, str(caught.exception))
                self.assertNotIn('secret-provider-body', str(caught.exception))

    def test_unknown_tool_and_unfinished_responses_do_not_fake_success(self):
        with self.assertRaises(ModelUnavailable):
            self.run_model(Scripted(tool('execute_shell', {})))
        settings = replace(self.settings, model_max_requests=1)
        model = ModelInterpreter(self.repo, settings, Scripted(catalog(Query())))
        with self.assertRaises(ModelUnavailable):
            model.run(None, TurnRequest(message='test', base_turn_id=None))

    def test_model_wait_does_not_lock_database_and_stale_completion_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='anime-model-concurrency-') as folder:
            history = History(Path(folder)/'history.sqlite3')
            cid = history.create()['id']
            rules = build_agent(self.repo)
            first = history.append(cid, TurnRequest(message='Busca Death Note', base_turn_id=None), rules)
            second = history.append(cid, TurnRequest(message='Solo TV', base_turn_id=first['id']), rules)
            entered, release = threading.Event(), threading.Event()
            failures = []
            class Waiting:
                def invoke(self, work):
                    entered.set()
                    if not release.wait(5):
                        raise RuntimeError('Test synchronization timed out')
                    return {'response': work['previous']}
            def worker():
                try:
                    history.append(cid, TurnRequest(message='Consulta en curso', base_turn_id=second['id']), Waiting())
                except Exception as error:
                    failures.append(error)
            thread = threading.Thread(target=worker)
            thread.start()
            try:
                self.assertTrue(entered.wait(3))
                # Writing another conversation must not wait for the remote call.
                other = history.create()
                self.assertNotEqual(other['id'], cid)
                from anime_agent.models import ActivateRequest
                history.activate(cid, ActivateRequest(turn_id=first['id'], expected_active_turn_id=second['id']))
            finally:
                release.set()
                thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(failures), 1)
            self.assertIsInstance(failures[0], Conflict)
            self.assertEqual(len(history.get(cid)['turns']), 2)


if __name__ == '__main__':
    unittest.main()
