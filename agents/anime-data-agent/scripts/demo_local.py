"""Demonstrate phases 4/5 directly, without network sockets or a model."""
import json
import tempfile
from pathlib import Path

from anime_agent.config import Settings
from anime_agent.conversation import build_agent
from anime_agent.history import History
from anime_agent.models import ActivateRequest, TurnRequest
from anime_agent.queries import Repository


def run():
    repo = Repository(Settings.from_environment().dataset_path)
    graph = build_agent(repo)
    transcript = []
    with tempfile.TemporaryDirectory(prefix='anime-demo-') as folder:
        history = History(Path(folder) / 'conversation.sqlite3')
        cid = history.create()['id']
        base = None

        def turn(message, selected=None):
            nonlocal base
            saved = history.append(cid, TurnRequest(message=message, base_turn_id=base, selected_ids=selected or []), graph)
            base = saved['id']
            response = saved['response']
            result = response['result']
            transcript.append(dict(message=message, status=response['status'], filters=response['state']['query'],
                explanation=response['explanation'], total=result['total'] if result else None,
                rows=[{key: row[key] for key in ('anime_id', 'title', 'score', 'scored_by', 'episodes')} for row in result['rows']] if result else [],
                groups=result['groups'] if result else []))
            return saved

        first = turn('Muéstrame los 10 animes de fantasía mejor puntuados')
        second = turn('Solo series de televisión de máximo 26 episodios')
        ids = [r['anime_id'] for r in second['response']['result']['rows'][:2]]
        turn('Compara estos dos', ids)
        turn('Solo TV y con doblaje costarricense')
        history.activate(cid, ActivateRequest(turn_id=first['id'], expected_active_turn_id=base))
        base = first['id']
        turn('Solo TV')
        turn('¿Cuántas series se estrenaron por año desde 2020?')
    return dict(mode='Direct service demonstration, no HTTP and no model', load_id=repo.load_id,
                manifest_sha256=repo.manifest_hash, transcript=transcript)


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
