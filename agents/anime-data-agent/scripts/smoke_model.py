"""Live phase-7 acceptance: requires running OpenAI-mode API and consumes API usage."""
import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-api', action='store_true', help='Authorize three model turns with possible API usage charges.')
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    if not args.allow_api:
        raise SystemExit('Esta prueba usa el modelo real y puede generar consumo. Ejecutá con --allow-api cuando hayas configurado clave y saldo.')
    opener = build_opener(ProxyHandler({}))

    def call(path, body=None):
        request = Request(args.url.rstrip('/')+path, data=json.dumps(body).encode() if body is not None else None,
                          headers={'Content-Type': 'application/json'})
        try:
            with opener.open(request, timeout=90) as response:
                return json.load(response)
        except HTTPError as error:
            try:
                detail = json.load(error).get('detail', 'Error de API')
            except ValueError:
                detail = 'Respuesta no válida de API'
            raise RuntimeError(f'HTTP {error.code}: {detail}') from None

    health = call('/api/health')
    if health.get('agent_mode') != 'openai' or health.get('model_status') == 'missing_api_key':
        raise RuntimeError('La API no está configurada en modo OpenAI con clave. Iniciá scripts/start_api.py.')
    if health['dataset_status'] != 'validated':
        raise RuntimeError('Dataset no validado.')
    cid = call('/api/conversations', {})['id']
    base = None
    runs = []

    def turn(message, selected=None):
        nonlocal base
        response = call(f'/api/conversations/{cid}/turns', dict(message=message, base_turn_id=base,
                        selected_ids=selected or [], request_id=str(uuid4())))
        base = response['id']
        agent = response['response']
        if agent['interpreter'] != 'openai_tools' or not agent.get('model_run', {}).get('requests'):
            raise RuntimeError('El turno no acredita una llamada real al modelo.')
        if agent['status'] == 'clarification':
            raise RuntimeError('El modelo pidió aclaración para un escenario esperado: ' + agent['explanation'])
        runs.append(agent['model_run'])
        print('OK:', message)
        print('Filtros:', json.dumps(agent['result']['applied_query'], ensure_ascii=False))
        return agent

    first = turn('Quiero cinco series de fantasía con un máximo de doce episodios, ordenadas de mayor a menor puntuación.')
    q = first['result']['applied_query']
    if q['filters']['formats'] != ['tv'] or 'Fantasy' not in q['filters']['genres'] or q['filters']['max_episodes'] != 12 or q['limit'] != 5 or q['order_by'] != 'score' or q['direction'] != 'desc':
        raise RuntimeError('La interpretación inicial no coincide con los filtros esperados.')
    second = turn('De esas, dejame solamente las que se estrenaron desde 2020; mantené lo demás.')
    filters = second['result']['applied_query']['filters']
    if filters['year_from'] != 2020 or filters['max_episodes'] != 12 or filters['formats'] != ['tv'] or 'Fantasy' not in filters['genres']:
        raise RuntimeError('El refinamiento perdió filtros o no aplicó el año.')
    ids = second['result']['evidence']['shown_ids'][:2]
    if len(ids) != 2:
        raise RuntimeError('No hay dos filas para verificar la comparación.')
    third = turn('Compará estos dos y mostrame sus diferencias de puntuación y episodios.', ids)
    if third['result']['evidence']['shown_ids'] != ids:
        raise RuntimeError('No se comparó la selección exacta.')
    print('OK: fase 7 por HTTP con modelo real, herramientas locales y contexto.')
    print('Conversation:', cid)
    print('Model:', health['model_name'])
    print('Usage:', json.dumps(dict(requests=sum(r['requests'] for r in runs), input_tokens=sum(r['input_tokens'] for r in runs), output_tokens=sum(r['output_tokens'] for r in runs))))


if __name__ == '__main__':
    try:
        main()
    except (OSError, URLError, RuntimeError, ValueError, KeyError) as error:
        raise SystemExit(f'Prueba real incompleta: {error}')
