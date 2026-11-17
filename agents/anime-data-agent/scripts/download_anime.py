"""Download a resumable Jikan snapshot using only Python's standard library."""
import csv
import hashlib
import json
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
START, END = '2020-01-01', '2026-11-16'
OUT = ROOT / 'data' / f'jikan-tv-{START}_{END}'


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def fetch(url):
    for attempt in range(6):
        try:
            request = Request(url, headers={'User-Agent': 'AnimeDataAgentResearch/0.1', 'Accept': 'application/json'})
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 5:
                raise
            time.sleep(min(60, 2 ** (attempt + 1)))
        except (URLError, TimeoutError) as error:
            reason = getattr(error, 'reason', error)
            if isinstance(reason, socket.gaierror):
                raise RuntimeError('No se pudo resolver api.jikan.moe (DNS). Comprueba el acceso desde el navegador.') from error
            # One retry for transient connection failures; never loop for minutes.
            if attempt >= 1:
                raise RuntimeError('Jikan no responde desde esta conexion. Abre https://api.jikan.moe/v4/anime/1 en el navegador para comprobar el acceso. No se publicaron datos finales en este intento.') from error
            print('Conexion interrumpida; reintentando una vez...', flush=True)
            time.sleep(2)


def main():
    raw = OUT / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    records, page, urls = {}, 1, []
    while True:
        query = urlencode(dict(type='tv', start_date=START, end_date=END,
                               order_by='mal_id', sort='asc', limit=25, page=page))
        url = 'https://api.jikan.moe/v4/anime?' + query
        path = raw / f'page-{page:04d}.json'
        if path.exists():
            envelope = json.loads(path.read_text(encoding='utf-8'))
            if envelope['url'] != url:
                raise ValueError('Cached page belongs to a different query')
        else:
            print(f'Descargando pagina {page} desde api.jikan.moe...', flush=True)
            payload = fetch(url)
            if not isinstance(payload.get('data'), list) or 'pagination' not in payload:
                raise ValueError('Unexpected Jikan response')
            envelope = dict(url=url, collected_at=datetime.now(timezone.utc).isoformat(), payload=payload)
            save_json(path, envelope)
            time.sleep(1.2)
        payload = envelope['payload']
        for item in payload['data']:
            premiered = (item.get('aired') or {}).get('from')
            # Date queries may overlap ongoing shows: enforce premiere coverage locally.
            if item.get('type') != 'TV' or not premiered or not START <= premiered[:10] <= END:
                continue
            record = dict(item)
            record['_collected_at'] = envelope['collected_at']
            record['_source_url'] = url
            records[item['mal_id']] = record
        urls.append(url)
        print(f'Page {page}: {len(records)} unique TV anime in scope', flush=True)
        if not payload['pagination'].get('has_next_page'):
            break
        page += 1
    items = [records[key] for key in sorted(records)]
    if not items:
        raise ValueError('No records: final dataset was not published')
    save_json(OUT / 'anime.json', items)
    fields = ['mal_id', 'title', 'title_english', 'title_japanese', 'type', 'episodes',
              'status', 'year', 'season', 'aired_from', 'score', 'scored_by', 'rank',
              'popularity', 'members', 'favorites', 'genres', 'studios', 'synopsis',
              'url', 'collected_at']
    target = OUT / 'anime.csv'
    temporary = target.with_suffix('.csv.tmp')
    with temporary.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in items:
            row = {key: item.get(key) for key in fields}
            row.update(aired_from=(item.get('aired') or {}).get('from'),
                       genres=json.dumps([x['name'] for x in item.get('genres', [])], ensure_ascii=False),
                       studios=json.dumps([x['name'] for x in item.get('studios', [])], ensure_ascii=False),
                       collected_at=item['_collected_at'])
            writer.writerow(row)
    temporary.replace(target)
    checksums = {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
                 for name in ('anime.csv', 'anime.json')}
    save_json(OUT / 'manifest.json', dict(source='Jikan v4 / MyAnimeList (unofficial)',
              start_date=START, end_date=END, date_semantics='premiere date inclusive',
              completed_at=datetime.now(timezone.utc).isoformat(), records=len(items),
              pages=page, query_urls=urls, sha256=checksums,
              note='Snapshot; pagination may change during collection. Not a historical ratings series.'))
    print(f'Download complete: {len(items)} anime. Files: {OUT}')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        raise SystemExit(f'Download incomplete: {error}. Run again to resume cached pages.')
