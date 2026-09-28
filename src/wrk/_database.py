from collections.abc import Generator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime as DateTime
from enum import Enum, unique
import os
from pathlib import Path
from sqlite3 import Connection, Cursor, connect
from typing import ClassVar, ContextManager, Final, Literal, final


@final
@unique
class EventType(Enum):
    START = 0
    STOP = 1


@final
@dataclass(frozen=True, slots=True)
class StartEvent:
    type: ClassVar[Final[Literal[EventType.START]]] = EventType.START
    created_at: Final[DateTime]
    archived_at: Final[DateTime | None] = None


@final
@dataclass(frozen=True, slots=True)
class StopEvent:
    type: ClassVar[Final[Literal[EventType.STOP]]] = EventType.STOP
    created_at: Final[DateTime]
    archived_at: Final[DateTime | None] = None


type Event = StartEvent | StopEvent


def sql(text: str) -> str:
    return text


def open_cursor(conn: Connection) -> ContextManager[Cursor]:
    return closing(conn.cursor())


@contextmanager
def transaction(conn: Connection) -> Generator[Cursor]:
    with conn, open_cursor(conn) as cursor:
        yield cursor


def _get_database_path() -> Path:
    name = 'database.sqlite3'

    if 'WRK_DEV' in os.environ:
        print('Using development database')
        project_dir = Path(__file__).resolve(strict=True).parents[1]
        return project_dir / 'local' / name

    path = os.environ.get('WRK_DATABASE', None)

    if path is not None:
        return Path(path)

    parent_dir = Path.home() / '.local/share/wrk'
    parent_dir.mkdir(parents=True, exist_ok=True)
    return parent_dir / name


_CREATE_EVENTS_TABLE: Final = sql(r"""
    CREATE TABLE IF NOT EXISTS events (
        id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT
    ,   type        INTEGER NOT NULL CHECK (type BETWEEN 0 AND 1)
    ,   created_at  INTEGER NOT NULL CHECK (created_at >= 0)
    ,   archived_at INTEGER CHECK (archived_at >= 0)
    ) STRICT
""")


@contextmanager
def open_database() -> Generator[Connection]:
    with closing(connect(_get_database_path(), autocommit=True)) as conn:
        with open_cursor(conn) as cursor:
            cursor.execute('PRAGMA journal_mode = WAL')
        conn.autocommit = False
        with transaction(conn) as cursor:
            cursor.execute(_CREATE_EVENTS_TABLE)
        yield conn


def fetch_events(
    cursor: Cursor, include_archived: bool | None = None
) -> list[Event]:
    if include_archived is None:
        include_archived = False
    cursor.execute(
        sql("""
            SELECT e.type, e.created_at, e.archived_at
            FROM events AS e ORDER BY e.created_at
        """)
    )
    events: list[Event] = []
    for raw_type, raw_created_at, raw_archived_at in cursor:
        if not include_archived and raw_archived_at is not None:
            continue
        event_type = EventType(raw_type)
        created_at = DateTime.fromtimestamp(raw_created_at)
        if raw_archived_at is None:
            archived_at = None
        else:
            archived_at = DateTime.fromtimestamp(raw_archived_at)
        match event_type:
            case EventType.START:
                event = StartEvent(created_at, archived_at=archived_at)
            case EventType.STOP:
                event = StopEvent(created_at, archived_at=archived_at)
        events.append(event)
    return events


def insert_event(conn: Connection, event: Event) -> None:
    with transaction(conn) as cursor:
        cursor.execute(
            sql(r"""
                INSERT INTO events (type, created_at, archived_at)
                VALUES (:type, :created_at, NULL)
            """),
            {
                'type': event.type.value,
                'created_at': round(event.created_at.timestamp()),
                'archived_at': None
                if event.archived_at is None
                else event.archived_at.timestamp(),
            },
        )
