from argparse import ArgumentParser

from wrk._database import open_database, transaction
from wrk._report import print_report
from wrk._ui import run_ui


def _do_archive() -> None:
    with open_database() as conn, transaction(conn) as cursor:
        cursor.execute(r"""
            UPDATE events SET archived_at = unixepoch()
            WHERE archived_at IS NULL
        """)


def _do_extend() -> None:
    with open_database() as conn, transaction(conn) as cursor:
        cursor.execute("""
            UPDATE events SET timestamp = unixepoch()
            FROM (
                SELECT id FROM events
                WHERE type = 1
                ORDER BY timestamp DESC
                LIMIT 1
            ) AS latest
            WHERE events.id = latest.id;
        """)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        'command',
        nargs='?',
        choices=('extend', 'report', 'archive'),
    )
    args = parser.parse_args()
    match args.command:
        case 'archive':
            _do_archive()
        case 'extend':
            _do_extend()
        case 'report':
            print_report()
        case _:
            run_ui()


if __name__ == '__main__':
    main()
