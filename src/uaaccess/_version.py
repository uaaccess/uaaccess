"""
_version.py

Obtains the version of the application from a nearby pyproject.toml, or the package directly (if installed).
We do this to prevent the need to hardcode version numbers in more than one place.

Credit for the idea taken from a Stackoverflow thread: https://stackoverflow.com/questions/67085041/how-to-specify-version-in-only-one-place-when-using-pyproject-toml
"""


import importlib.metadata
from contextlib import suppress
from pathlib import Path


def extract_version() -> str:
    """Returns either the version of installed package or the one
    found in nearby pyproject.toml"""
    with suppress(FileNotFoundError, StopIteration):
        with open((Path(__file__).parent.parent.parent)/"pyproject.toml", encoding="utf-8") as pyproject_toml:
            version = (
                next(line for line in pyproject_toml if line.startswith("version"))
                .split("=")[1]
                .strip("'\"\n ")
            )
            return f"{version}"
    return importlib.metadata.version(__package__
                                      or __name__.split(".", maxsplit=1)[0])


__version__ = extract_version()
