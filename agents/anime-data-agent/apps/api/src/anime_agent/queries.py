"""Read-only, hash-verified snapshot queries; no model-generated calculations."""
import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path

from anime_agent.models import Query, Result


class DatasetUnavailable(RuntimeError):
    pass


class InvalidQuery(ValueError):
    pass


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.casefold()) if unicodedata.category(c) != 'Mn')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def child(root, name):
    if not isinstance(name, str):
        raise ValueError('Invalid manifest path')
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError('Manifest path escapes snapshot')
    return path


DEFINITIONS = {
    'score': 'Puntuación publicada por MyAnimeList, sobre 10; no se recalcula.',
    'scored_by': 'Cantidad de usuarios que puntuaron; sin mínimo obligatorio.',
    'popularity': 'Posición de popularidad en MyAnimeList: menor es más popular; no es seguidores.',
    'rank': 'Posición reportada por MyAnimeList; distinta del orden calculado por esta consulta.',
    'duration_seconds': 'Duración media reportada por episodio en segundos.',
    'year': 'Año de la fecha de inicio; registros del dataset, no total mundial.',
    'groups': 'Géneros/estudios múltiples contribuyen a cada grupo; sus sumas pueden exceder el total. Sin dato se agrupa como Desconocido.',
    'missing': 'Valores desconocidos permanecen nulos; se omiten solo cuando la métrica o filtro los requiere.',
}


class Repository:
    def __init__(self, pointer: Path):
        try:
            pointer = pointer.resolve()
            pointer_bytes = pointer.read_bytes()
            selection = json.loads(pointer_bytes)
            manifest_path = child(pointer.parent, selection['manifest'])
            if digest(manifest_path) != selection['manifest_sha256']:
                raise ValueError('Manifest hash mismatch')
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            if manifest['schema_version'] != 1 or manifest['load_id'] != selection['load_id']:
                raise ValueError('Unsupported snapshot contract')
            required = {'anime.json', 'source.csv', 'quality.json'}
            if not required <= manifest['files'].keys():
                raise ValueError('Incomplete snapshot')
            for name, checksum in manifest['files'].items():
                if digest(child(manifest_path.parent, name)) != checksum:
                    raise ValueError('Snapshot checksum mismatch')
            self.records = json.loads((manifest_path.parent / 'anime.json').read_text(encoding='utf-8'))
            if digest(manifest_path.parent / 'anime.json') != manifest['files']['anime.json'] or digest(manifest_path) != selection['manifest_sha256']:
                raise ValueError('Snapshot changed during read')
            if pointer.read_bytes() != pointer_bytes:
                raise ValueError('Snapshot pointer changed during read; retry')
            self.by_id = {r['anime_id']: r for r in self.records}
            if len(self.records) != manifest['records'] or len(self.by_id) != len(self.records):
                raise ValueError('Invalid record inventory')
            self.manifest = manifest
            self.manifest_hash = selection['manifest_sha256']
            self.formats = sorted({r['type'] for r in self.records})
            self.statuses = sorted({r['status'] for r in self.records})
            self.genres = sorted({g for r in self.records for g in r['genres']})
            self.studios = sorted({s for r in self.records for s in r['studios']})
            self.query_hash = digest(Path(__file__))
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise DatasetUnavailable('No se pudo verificar la carga de anime; revisá la preparación y sus hashes.') from error

    @property
    def load_id(self):
        return self.manifest['load_id']

    def metadata(self):
        return dict(load_id=self.load_id, records=len(self.records), formats=self.formats,
                    genres=self.genres, studios=self.studios, statuses=self.statuses,
                    disabled_metrics=self.manifest['disabled_metrics'], definitions=DEFINITIONS,
                    source_file_date=self.manifest['source_file_date'], reference_date=self.manifest['reference_date'],
                    source_date_note=self.manifest['source_file_date_semantics'],
                    date_coverage=[min(r['start_year'] for r in self.records), max(r['start_year'] for r in self.records)])

    def canonical_query(self, query):
        query = query.model_copy(deep=True)
        f = query.filters
        for field, vocabulary in [('formats', self.formats), ('genres', self.genres), ('statuses', self.statuses)]:
            mapping = {norm(v): v for v in vocabulary}
            values = getattr(f, field)
            if any(norm(v) not in mapping for v in values):
                raise InvalidQuery(f'Filtro {field} contiene valores desconocidos; consultá /api/dataset.')
            setattr(f, field, list(dict.fromkeys(mapping[norm(v)] for v in values)))
        if f.studio:
            candidates = [s for s in self.studios if norm(s) == norm(f.studio)]
            if len(candidates) != 1:
                raise InvalidQuery('Estudio desconocido o ambiguo; usá el nombre del catálogo.')
            f.studio = candidates[0]
        if query.direction is None:
            query.direction = 'asc' if query.order_by in ('popularity', 'rank', 'title') else 'desc'
        return query

    def matches(self, record, f):
        if f.title and not any(norm(f.title) in norm(record.get(key) or '') for key in ('title', 'english_title', 'japanese_title')):
            return False
        if f.formats and record['type'] not in f.formats:
            return False
        if f.statuses and record['status'] not in f.statuses:
            return False
        if f.genres:
            hits = [g in record['genres'] for g in f.genres]
            if not (any(hits) if f.genre_mode == 'any' else all(hits)):
                return False
        if f.studio and f.studio not in record['studios']:
            return False
        for field, minimum, maximum in [('start_year', f.year_from, f.year_to),
                                         ('score', f.min_score, None), ('scored_by', f.min_votes, None),
                                         ('episodes', None, f.max_episodes)]:
            value = record[field]
            if minimum is not None and (value is None or value < minimum):
                return False
            if maximum is not None and (value is None or value > maximum):
                return False
        return True

    @staticmethod
    def public(record, detail=False):
        keys = ['anime_id', 'title', 'english_title', 'japanese_title', 'type', 'episodes',
                'duration_seconds', 'status', 'studios', 'genres', 'score', 'scored_by',
                'rank', 'popularity', 'start_date', 'start_date_precision', 'start_year',
                'future_start', 'source_url', 'quality_flags']
        if detail:
            keys += ['synopsis', 'source', 'end_date', 'end_date_precision', 'rating']
        return {key: record[key] for key in keys}

    def execute(self, query: Query) -> Result:
        q = self.canonical_query(query)
        if q.kind in ('detail', 'compare'):
            if any(i not in self.by_id for i in q.ids):
                raise InvalidQuery('Uno de los IDs no existe en esta carga.')
            selected = [self.by_id[i] for i in q.ids]
            if any(not self.matches(r, q.filters) for r in selected):
                raise InvalidQuery('Los IDs seleccionados no satisfacen los filtros activos.')
        else:
            selected = [r for r in self.records if self.matches(r, q.filters)]
        matched = len(selected)
        groups, omitted = [], 0
        if q.kind == 'aggregate':
            counts = Counter()
            for r in selected:
                values = [r['start_year']] if q.group_by == 'year' else r['genres' if q.group_by == 'genre' else 'studios']
                for value in values or [None]:
                    counts['Desconocido' if value is None else str(value)] += 1
            groups = [dict(key=k, count=counts[k]) for k in sorted(counts)]
            shown = []
        elif q.kind in ('detail', 'compare'):
            shown = selected
        else:
            eligible = [r for r in selected if r.get(q.order_by) is not None]
            omitted = len(selected) - len(eligible)
            # Stable ties always preserve ascending ID, even for descending metrics.
            eligible.sort(key=lambda r: r['anime_id'])
            eligible.sort(key=lambda r: norm(r['title']) if q.order_by == 'title' else r[q.order_by], reverse=q.direction == 'desc')
            selected = eligible
            shown = eligible[:q.limit]
        evidence = dict(load_id=self.load_id, manifest_sha256=self.manifest_hash,
                        source_commit=self.manifest['source_commit'], source_sha256=self.manifest['source_sha256'],
                        source_repository=self.manifest['source_repository'], source_file_date=self.manifest['source_file_date'],
                        reference_date=self.manifest['reference_date'], query_sha256=self.query_hash,
                        selected_ids=[r['anime_id'] for r in selected], shown_ids=[r['anime_id'] for r in shown])
        return Result(status='result' if selected else 'empty', kind=q.kind, applied_query=q,
                      total=len(selected), matched_total=matched, omitted_missing_metric=omitted,
                      rows=[self.public(r, q.kind in ('detail', 'compare')) for r in shown],
                      groups=groups, evidence=evidence, definitions=DEFINITIONS)
