"""Live local API verification. Run after restarting Uvicorn; creates a demo conversation."""
import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, ProxyHandler, build_opener
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    opener = build_opener(ProxyHandler({}))

    def call(path, payload=None, expected=200):
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        req = Request(args.url.rstrip('/') + path, data=data, headers={'Content-Type': 'application/json'})
        try:
            response = opener.open(req, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            body = json.load(response)
            if response.code != expected:
                raise RuntimeError(f'{path}: expected {expected}, got {response.code}: {body}')
            return body

    health = call('/api/health')
    if health['dataset_status'] != 'validated':
        raise RuntimeError('Dataset not validated; check ANIME_DATASET_PATH and preparation.')
    if health.get('agent_mode') != 'rules':
        raise RuntimeError('Start scripts/start_api.py --mode rules before this check; no model calls were made.')
    meta = call('/api/dataset')
    ranking = call('/api/query', {'filters': {'formats': ['tv'], 'genres': ['Fantasy'], 'max_episodes': 26}, 'limit': 10})
    if not ranking['rows']:
        raise RuntimeError('Expected non-empty demo ranking')
    call('/api/query', {'order_by': 'members'}, 422)
    conversation = call('/api/conversations', {}, 201)
    cid = conversation['id']
    first_body = {'message': 'Muéstrame los 10 animes de fantasía mejor puntuados', 'base_turn_id': None, 'request_id': str(uuid4())}
    first = call(f'/api/conversations/{cid}/turns', first_body)
    retry = call(f'/api/conversations/{cid}/turns', first_body)
    if retry['id'] != first['id']:
        raise RuntimeError('Retry duplicated a turn')
    second = call(f'/api/conversations/{cid}/turns', {'message': 'Solo series de televisión de máximo 26 episodios', 'base_turn_id': first['id']})
    if second['response']['result']['evidence']['shown_ids'] != ranking['evidence']['shown_ids']:
        raise RuntimeError('Conversation and direct query disagree')
    ids = second['response']['result']['evidence']['shown_ids'][:2]
    pair = call(f'/api/conversations/{cid}/turns', {'message': 'Compara estos dos', 'selected_ids': ids, 'base_turn_id': second['id']})
    if pair['response']['result']['evidence']['shown_ids'] != ids:
        raise RuntimeError('Comparison failed')
    call(f'/api/conversations/{cid}/turns', {'message': 'Solo TV', 'base_turn_id': None}, 409)
    call(f'/api/conversations/{cid}/activate', {'turn_id': first['id'], 'expected_active_turn_id': pair['id']})
    restored = call(f'/api/conversations/{cid}')
    if restored['active_turn_id'] != first['id']:
        raise RuntimeError('History recovery failed')
    print('OK: dataset, ranking, validation, conversation, comparison, idempotency and history over real HTTP.')
    print('Records:', meta['records'], '| conversation:', cid)
    print('First 3 demo titles:', ', '.join(row['title'] for row in ranking['rows'][:3]))


if __name__ == '__main__':
    try:
        main()
    except (OSError, URLError, ValueError, RuntimeError, KeyError) as error:
        raise SystemExit(f'Live verification incomplete: {error}')
