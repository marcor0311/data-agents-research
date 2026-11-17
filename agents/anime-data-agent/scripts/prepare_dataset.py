"""Validate and publish an immutable local snapshot. Standard library only."""
import argparse
import calendar
import csv
import hashlib
import io
import json
import math
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['anime_id', 'title', 'english_title', 'japanese_title', 'type', 'episodes',
          'duration', 'status', 'source', 'season', 'studios', 'genres', 'rating',
          'score', 'scored_by', 'rank', 'popularity', 'members', 'favorites',
          'watching', 'completed', 'on_hold', 'dropped', 'plan_to_watch',
          'start_date', 'end_date', 'broadcast_day', 'broadcast_time', 'synopsis']
UNAVAILABLE = ['members', 'favorites', 'watching', 'completed', 'on_hold', 'dropped', 'plan_to_watch']
FORMATS = {'tv', 'movie', 'music', 'special', 'unknown', 'tv_special', 'ova', 'pv', 'cm', 'ona'}
STATUSES = {'finished_airing', 'currently_airing', 'not_yet_aired'}
SOURCE_URL = 'https://github.com/LeoRigasaki/Anime-dataset'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def number(value, field, positive=False, integer=True):
    if value.strip() == '':
        return None
    n = float(value)
    if not math.isfinite(n) or n < 0 or (integer and not n.is_integer()):
        raise ValueError(f'{field}: invalid nonnegative number')
    if positive and n == 0:
        return None
    return int(n) if integer else n


def parse_date(value):
    if not value:
        return None, None, None, None
    if re.fullmatch(r'\d{4}', value):
        year = int(value)
        return value, 'year', date(year, 1, 1), date(year, 12, 31)
    if re.fullmatch(r'\d{4}-\d{2}', value):
        year, month = map(int, value.split('-'))
        return value, 'month', date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    day = date.fromisoformat(value)
    if len(value) != 10:
        raise ValueError('date must use YYYY, YYYY-MM or YYYY-MM-DD')
    return value, 'day', day, day


def normalize(row, reference):
    notes = []
    identifier = number(row['anime_id'], 'anime_id', positive=True)
    if identifier is None or not row['title'].strip():
        raise ValueError('missing identifier or title')
    if row['type'] not in FORMATS or row['status'] not in STATUSES:
        raise ValueError('unknown format or status')
    result = {key: (value.strip() or None) for key, value in row.items()}
    result['anime_id'] = identifier
    for field in ['episodes', 'duration', 'rank', 'popularity']:
        result[field] = number(row[field], field, positive=True)
        if result[field] is None:
            notes.append(field + '_unknown')
    result['duration_seconds'] = result.pop('duration')
    result['scored_by'] = number(row['scored_by'], 'scored_by')
    result['score'] = number(row['score'], 'score', positive=True, integer=False)
    if result['score'] is not None and (result['score'] > 10 or not result['scored_by']):
        raise ValueError('score outside scale or score without votes')
    if result['score'] is None:
        notes.append('score_unavailable_not_zero_rating')
    for field in UNAVAILABLE:
        number(row[field], field)
        if float(row[field]) != 0:
            raise ValueError(f'{field}: source changed; review disabled field policy')
        result[field] = None
    notes.append('source_statistics_unavailable')
    for field in ['genres', 'studios']:
        result[field] = list(dict.fromkeys(x.strip() for x in row[field].split(';') if x.strip()))
        if not result[field]:
            notes.append(field + '_missing')
    for field in ['start_date', 'end_date']:
        value, precision, earliest, latest = parse_date(row[field])
        result[field] = value
        result[field + '_precision'] = precision
        if precision != 'day':
            notes.append(field + ('_missing' if precision is None else '_partial'))
        if field == 'start_date':
            result['start_year'] = earliest.year if earliest else None
            result['future_start'] = (True if earliest > reference else False if latest <= reference else None) if earliest else None
    season = re.fullmatch(r'(winter|spring|summer|fall) (\d{4})', row['season'])
    if not season:
        raise ValueError('invalid season')
    result['season_name'] = season[1]
    result['season_year'] = int(season[2])
    if not result['synopsis']:
        notes.append('synopsis_missing')
    result['source_url'] = f'https://myanimelist.net/anime/{identifier}'
    result['quality_flags'] = notes
    # Retain source values alongside explicit normalization reasons.
    result['source_values'] = dict(row)
    return result


def build(source, output, source_repo, reference):
    content = source.read_bytes()
    source_hash = sha(content)
    transform_hash = sha(Path(__file__).read_bytes())
    load_id = f'anime-v1-{reference.isoformat()}-{source_hash[:16]}-{transform_hash[:16]}'
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig'), newline=''))
    if reader.fieldnames != FIELDS:
        raise ValueError('CSV schema changed; review before publishing')
    originals, records, errors, ids = [], [], [], set()
    for line, row in enumerate(reader, start=2):
        originals.append(row)
        try:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('malformed CSV row')
            result = normalize(row, reference)
            if result['anime_id'] in ids:
                raise ValueError('duplicate anime_id')
            ids.add(result['anime_id'])
            records.append(result)
        except (ValueError, TypeError) as error:
            errors.append({'csv_line': line, 'error': str(error)})
    if errors or not records:
        raise ValueError(f'Validation failed: {len(errors)} rejected rows; examples={errors[:5]}. Current snapshot unchanged.')
    records.sort(key=lambda item: item['anime_id'])
    commit = subprocess.check_output(['git', '-C', str(source_repo), 'rev-parse', 'HEAD'], text=True).strip()
    relative = source.resolve().relative_to(source_repo.resolve()).as_posix()
    tracked = subprocess.check_output(['git', '-C', str(source_repo), 'show', f'{commit}:{relative}'])
    # Accept CRLF conversion by Git but record both byte hashes, never equate them.
    if tracked.replace(b'\r\n', b'\n') != content.replace(b'\r\n', b'\n'):
        raise ValueError('Source CSV differs from pinned Git commit')
    declared = re.search(r'(\d{8})\.csv$', source.name)
    report = {
        'load_id': load_id, 'reference_date': reference.isoformat(),
        'input_rows': len(originals), 'accepted_rows': len(records), 'rejected_rows': 0,
        'excluded_by_scope': 0, 'unique_ids': len(ids),
        'rows_with_warnings': sum(bool(r['quality_flags']) for r in records),
        'warnings': dict(sorted(Counter(flag for r in records for flag in r['quality_flags']).items())),
        'formats': dict(sorted(Counter(r['type'] for r in records).items())),
        'start_years': dict(sorted(Counter(str(r['start_year']) for r in records).items())),
        'start_date_precision': dict(Counter(r['start_date_precision'] for r in records)),
        'future_starts': sum(r['future_start'] is True for r in records),
        'future_start_uncertain': sum(r['future_start'] is None for r in records),
        'missing_normalized': {key: sum(r.get(key) is None or r.get(key) == [] for r in records)
                               for key in ['score', 'episodes', 'duration_seconds', 'rank', 'popularity',
                                           'studios', 'genres', 'synopsis', *UNAVAILABLE]},
        'disabled_metrics': UNAVAILABLE,
        'license': 'No explicit root license file found in inspected repository. Public redistribution not cleared.',
        'coverage_note': 'Observed snapshot; seasonal collector does not certify exhaustive coverage.',
    }
    # Stage a complete directory before atomically publishing the current pointer.
    output.mkdir(parents=True, exist_ok=True)
    destination = output / load_id
    if destination.exists():
        existing = json.loads((destination / 'manifest.json').read_text(encoding='utf-8'))
        for name, checksum in existing['files'].items():
            if sha((destination / name).read_bytes()) != checksum:
                raise ValueError('Existing snapshot corrupt; current pointer unchanged')
        if (destination / 'anime.json').read_bytes() != encode(records):
            raise ValueError('Non-reproducible records; refusing to overwrite snapshot')
    else:
        stage = Path(tempfile.mkdtemp(prefix='.prepare-', dir=output))
        try:
            files = {'anime.json': encode(records), 'quality.json': encode(report)}
            (stage / 'source.csv').write_bytes(content)
            files['source.csv'] = content
            for name, value in files.items():
                (stage / name).write_bytes(value)
            manifest = {
                'schema_version': 1, 'load_id': load_id,
                'source_repository': SOURCE_URL, 'source_commit': commit,
                'source_path': relative, 'source_sha256': source_hash,
                'git_blob_sha256': sha(tracked), 'source_bytes': len(content),
                'source_file_date': datetime.strptime(declared[1], '%Y%m%d').date().isoformat() if declared else None,
                'source_file_date_semantics': 'Filename date only; exact collection timestamp unknown.',
                'incorporated_at': datetime.now(timezone.utc).isoformat(),
                'reference_date': reference.isoformat(), 'transform_sha256': transform_hash,
                'records': len(records), 'files': {name: sha(value) for name, value in files.items()},
                'disabled_metrics': UNAVAILABLE, 'ranking_min_votes_default': None,
            }
            (stage / 'manifest.json').write_bytes(encode(manifest))
            stage.rename(destination)
        finally:
            if stage.exists():
                if stage.resolve().parent != output.resolve() or not stage.name.startswith('.prepare-'):
                    raise ValueError('Unsafe staging cleanup path')
                shutil.rmtree(stage)
    pointer = {'load_id': load_id, 'manifest': f'{load_id}/manifest.json',
               'manifest_sha256': sha((destination / 'manifest.json').read_bytes())}
    temporary = output / 'current.json.tmp'
    temporary.write_bytes(encode(pointer))
    temporary.replace(output / 'current.json')
    return destination, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT.parent / 'Anime-dataset/data/raw/anime_seasonal_20261116.csv')
    parser.add_argument('--source-repo', type=Path, default=ROOT.parent / 'Anime-dataset')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/processed')
    parser.add_argument('--reference-date', type=date.fromisoformat, default=date(2026, 11, 16))
    args = parser.parse_args()
    destination, report = build(args.source, args.output, args.source_repo, args.reference_date)
    print(json.dumps({'snapshot': str(destination), 'quality': report}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
