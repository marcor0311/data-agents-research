"""Transactional SQLite history: immutable turns and optimistic active pointer."""
import hashlib
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from anime_agent.models import AgentResponse


class NotFound(ValueError):
    pass


class Conflict(ValueError):
    pass


class History:
    def __init__(self, path: Path):
        self.path = path
        self._locks = {}
        self._locks_guard = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL, active_turn_id TEXT);
              CREATE TABLE IF NOT EXISTS turns (
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
                parent_turn_id TEXT, created_at TEXT NOT NULL, message TEXT NOT NULL,
                request_id TEXT, request_hash TEXT NOT NULL, response TEXT NOT NULL,
                UNIQUE(conversation_id, request_id));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def conversation(db, cid):
        value = db.execute('SELECT * FROM conversations WHERE id=?', (cid,)).fetchone()
        if value is None:
            raise NotFound('Conversación no encontrada.')
        return value

    @staticmethod
    def turn_value(row):
        return dict(id=row['id'], parent_turn_id=row['parent_turn_id'], created_at=row['created_at'],
                    message=row['message'], response=AgentResponse.model_validate_json(row['response']).model_dump(mode='json'))

    def create(self):
        cid = str(uuid4())
        with self.connect() as db:
            db.execute('INSERT INTO conversations VALUES (?,?,NULL)', (cid, datetime.now(timezone.utc).isoformat()))
        return self.get(cid)

    def get(self, cid):
        with self.connect() as db:
            db.execute('BEGIN')
            conversation = dict(self.conversation(db, cid))
            turns = db.execute('SELECT * FROM turns WHERE conversation_id=? ORDER BY rowid', (cid,)).fetchall()
            return {**conversation, 'turns': [self.turn_value(row) for row in turns]}

    def append(self, cid, request, agent):
        with self._locks_guard:
            lock = self._locks.setdefault(cid, threading.Lock())
        with lock:
            return self._append(cid, request, agent)

    def _append(self, cid, request, agent):
        fingerprint = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            conversation = self.conversation(db, cid)
            if request.request_id:
                prior = db.execute('SELECT * FROM turns WHERE conversation_id=? AND request_id=?', (cid, request.request_id)).fetchone()
                if prior:
                    if prior['request_hash'] != fingerprint:
                        raise Conflict('request_id reutilizado con otro contenido.')
                    return self.turn_value(prior)
            if conversation['active_turn_id'] != request.base_turn_id:
                raise Conflict('El turno base está desactualizado; recuperá la conversación antes de reintentar.')
            previous = None
            if request.base_turn_id:
                row = db.execute('SELECT response FROM turns WHERE id=? AND conversation_id=?', (request.base_turn_id, cid)).fetchone()
                if row is None:
                    raise NotFound('Turno ajeno o inexistente.')
                previous = AgentResponse.model_validate_json(row['response'])
        # Do not hold a database write lock while waiting on a remote model.
        response = agent.invoke({'previous': previous, 'request': request})['response']
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            conversation = self.conversation(db, cid)
            if request.request_id:
                prior = db.execute('SELECT * FROM turns WHERE conversation_id=? AND request_id=?', (cid, request.request_id)).fetchone()
                if prior:
                    if prior['request_hash'] != fingerprint:
                        raise Conflict('request_id reutilizado con otro contenido.')
                    return self.turn_value(prior)
            if conversation['active_turn_id'] != request.base_turn_id:
                raise Conflict('El contexto cambió durante la consulta. Recuperá el historial; no se guardó un turno sobre una base antigua.')
            tid = str(uuid4())
            db.execute('INSERT INTO turns VALUES (?,?,?,?,?,?,?,?)',
                       (tid, cid, request.base_turn_id, datetime.now(timezone.utc).isoformat(), request.message,
                        request.request_id, fingerprint, response.model_dump_json()))
            db.execute('UPDATE conversations SET active_turn_id=? WHERE id=?', (tid, cid))
            return self.turn_value(db.execute('SELECT * FROM turns WHERE id=?', (tid,)).fetchone())

    def activate(self, cid, request):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            conversation = self.conversation(db, cid)
            row = db.execute('SELECT id FROM turns WHERE id=? AND conversation_id=?', (request.turn_id, cid)).fetchone()
            if row is None:
                raise NotFound('Turno ajeno o inexistente.')
            if conversation['active_turn_id'] != request.expected_active_turn_id:
                raise Conflict('La conversación cambió antes de recuperar el turno.')
            db.execute('UPDATE conversations SET active_turn_id=? WHERE id=?', (request.turn_id, cid))
        return self.get(cid)
