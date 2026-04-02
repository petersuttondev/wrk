import csv
from io import StringIO
from itertools import batched
from datetime import datetime as DateTime
import subprocess
from sqlite3 import Cursor

from wrk._database import (
    StartEvent,
    StopEvent,
    fetch_events,
    open_cursor,
    open_database,
)


def _format_date(datetime: DateTime) -> str:
    return f'{datetime:%d/%m/%Y}'


def _format_time(datetime: DateTime) -> str:
    return f'{datetime:%H:%M:%S}'


def _with_database_print_report(cursor: Cursor) -> None:
    events = fetch_events(cursor)
    string = StringIO()
    writer = csv.writer(string)

    for start, stop in batched(events, 2, strict=True):
        if not isinstance(start, StartEvent):
            raise ValueError()
        if not isinstance(stop, StopEvent):
            raise ValueError()
        writer.writerow(
            (
                _format_date(start.timestamp),
                _format_time(start.timestamp),
                _format_time(stop.timestamp),
            ),
        )

    csv_text = string.getvalue()
    print(csv_text, end='')
    subprocess.run(
        ('xsel', '--clipboard'), input=csv_text, check=True, text=True
    )


def print_report() -> None:
    with open_database() as conn, open_cursor(conn) as cursor:
        _with_database_print_report(cursor)
