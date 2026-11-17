"""Build an optional URL-only media index. No AniList API calls or image downloads."""
import csv
import hashlib
import json
import subprocess
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'Anime-dataset/data/raw/anilist_seasonal_20261115.csv'
HOSTS = {'s4.anilist.co', 's.anilist.co', 'cdn.anilist.co'}


def safe_image(value):
    parsed = urlparse(value or '')
    return value if parsed.scheme == 'https' and parsed.netloc in HOSTS else None


def main():
    pointer = json.loads((ROOT / 'data/processed/current.json').read_text(encoding='utf-8'))
    folder = ROOT / 'data/processed' / pointer['load_id']
    catalog = json.loads((folder / 'anime.json').read_text(encoding='utf-8'))
    ids = {r['anime_id'] for r in catalog}
    images = {}
    with SOURCE.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            value = row.get('mal_id')
            if not value:
                continue
            identifier = Decimal(value)
            if not identifier.is_finite() or identifier != identifier.to_integral_value() or int(identifier) not in ids:
                continue
            cover, banner = safe_image(row['cover_image_large']), safe_image(row['banner_image'])
            if not (cover or banner):
                continue
            key = str(int(identifier))
            candidate = dict(cover=cover, banner=banner, source_url=row['site_url'],
                             collected_at=row['collected_at'], anilist_id=row['anime_id'])
            if key not in images or candidate['collected_at'] > images[key]['collected_at']:
                images[key] = candidate
    result = dict(load_id=pointer['load_id'], source_repository='https://github.com/LeoRigasaki/Anime-dataset',
                  source_commit=subprocess.check_output(['git', '-C', str(ROOT.parent / 'Anime-dataset'), 'rev-parse', 'HEAD'], text=True).strip(),
                  source_file=SOURCE.name, source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  note='URLs only, optional presentation metadata joined by MAL ID. No ratings from AniList. Not a license grant for artwork.',
                  images=images)
    target = ROOT / 'apps/web/public/media-index.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')
    print(f'Media: {len(images)} linked IDs, {sum(bool(r["banner"]) for r in images.values())} banners. {target}')


if __name__ == '__main__':
    main()
