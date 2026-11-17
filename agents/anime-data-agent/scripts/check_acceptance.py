"""Fixed acceptance examples for the agreed snapshot (not current online rankings)."""
import hashlib
import json
from pathlib import Path

from anime_agent.config import Settings
from anime_agent.models import Query
from anime_agent.queries import Repository


def main():
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / 'docs/acceptance-cases.json').read_text(encoding='utf-8'))
    pointer = Settings.from_environment().dataset_path
    manifest = json.loads(pointer.read_text(encoding='utf-8'))
    source = pointer.parent / manifest['load_id'] / 'source.csv'
    if hashlib.sha256(source.read_bytes()).hexdigest() != cases['source_sha256']:
        raise RuntimeError('These expected results require the documented snapshot; review before updating cases.')
    repo = Repository(pointer)
    for case in cases['cases']:
        result = repo.execute(Query.model_validate(case['query']))
        value = result.model_dump()
        for field, expected in case['expected'].items():
            actual = [row['anime_id'] for row in result.rows] if field == 'ids' else value[field]
            if actual != expected:
                raise AssertionError(f"{case['name']}: {field}: {actual!r} != {expected!r}")
        print('PASS:', case['name'])
    print('Load:', repo.load_id)


if __name__ == '__main__':
    main()
