from collections.abc import Iterator
from functools import cache
from typing import TYPE_CHECKING

from cleek import task

if TYPE_CHECKING:
    from pathlib import Path


def _iter_args(
    *args: tuple[Path | str, ...] | Path | str,
) -> Iterator[Path | str]:
    from pathlib import Path

    for arg in args:
        match arg:
            case Path() | str():
                yield arg
            case _:
                yield from _iter_args(*arg)


def _args(*args: tuple[Path | str, ...] | Path | str) -> list[Path | str]:
    return list(_iter_args(*args))


@cache
def _get_project_dir() -> Path:
    from pathlib import Path

    return Path(__file__).resolve(strict=True).parent


@task
def install() -> None:
    import subprocess

    subprocess.run(
        _args(
            'pip',
            'install',
            ('--editable', _get_project_dir()),
            ('--config-settings', 'editable_mode=strict'),
        ),
        check=True,
    )


@task
def uninstall() -> None:
    import subprocess
    import tomllib

    with open(_get_project_dir() / 'pyproject.toml', 'rb') as file:
        pyproject = tomllib.load(file)

    name = pyproject['project']['name']
    subprocess.run(('pip', 'uninstall', '--yes', name), check=True)
