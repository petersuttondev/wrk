from argparse import ArgumentParser

from wrk._report import print_report
from wrk._ui import run_ui


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument('command', nargs='?', choices=('report',))
    args = parser.parse_args()
    if args.command == 'report':
        print_report()
    else:
        run_ui()


if __name__ == '__main__':
    main()
