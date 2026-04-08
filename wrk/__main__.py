from argparse import ArgumentParser

from wrk._report import print_report
from wrk._ui import run_ui
from wrk._database import open_database, transaction


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument('command', nargs='?', choices=('extend', 'report','clear'))
    args = parser.parse_args()
    if args.command == 'extend':
        with open_database() as conn, transaction(conn) as cursor:
            cursor.execute('''
                UPDATE events SET timestamp = unixepoch()
                FROM (
                    SELECT id FROM events
                    WHERE type = 1
                    ORDER BY timestamp DESC
                    LIMIT 1
                ) AS latest
                WHERE events.id = latest.id;
            ''')
    elif args.command == 'report':
        print_report()
    elif args.command == 'clear':
        with open_database() as conn, transaction(conn) as cursor:
            cursor.execute('DELETE FROM events')
    else:
        run_ui()


if __name__ == '__main__':
    main()
