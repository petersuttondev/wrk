from collections.abc import Generator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime as DateTime
from enum import Enum, unique
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
    timestamp: Final[DateTime]


@final
@dataclass(frozen=True, slots=True)
class StopEvent:
    type: ClassVar[Final[Literal[EventType.STOP]]] = EventType.STOP
    timestamp: Final[DateTime]


type Event = StartEvent | StopEvent


def sql(text: str) -> str:
    return text


def open_cursor(conn: Connection) -> ContextManager[Cursor]:
    return closing(conn.cursor())


@contextmanager
def transaction(conn: Connection) -> Generator[Cursor]:
    with conn, open_cursor(conn) as cursor:
        yield cursor


_CREATE_EVENTS_TABLE: Final = sql(r"""
    CREATE TABLE IF NOT EXISTS events (
        id        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT
    ,   type      INTEGER NOT NULL CHECK (type BETWEEN 0 AND 1)
    ,   timestamp INTEGER NOT NULL CHECK (timestamp >= 0)
    ) STRICT
""")


@contextmanager
def open_database() -> Generator[Connection]:
    parent_dir = Path.home() / '.local/share/wrk'
    parent_dir.mkdir(parents=True, exist_ok=True)
    database_path = parent_dir / 'database.sqlite3'
    with closing(connect(database_path, autocommit=True)) as conn:
        with open_cursor(conn) as cursor:
            cursor.execute('PRAGMA journal_mode = WAL')
        conn.autocommit = False
        with transaction(conn) as cursor:
            cursor.execute(_CREATE_EVENTS_TABLE)
        yield conn


def insert_event(conn: Connection, event: Event) -> None:
    with transaction(conn) as cursor:
        cursor.execute(
            sql(r"""
                INSERT INTO events (type, timestamp) VALUES (:type, :timestamp)
            """),
            {
                'type': event.type.value,
                'timestamp': round(event.timestamp.timestamp()),
            },
        )
