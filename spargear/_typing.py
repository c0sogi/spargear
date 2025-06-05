import argparse
import typing as tp
from typing import IO, List, Literal, Optional, Protocol, Tuple, Type, Union

SUPPRESS_LITERAL_TYPE = Literal["==SUPPRESS=="]
SUPPRESS: SUPPRESS_LITERAL_TYPE = "==SUPPRESS=="
ACTION_TYPES_THAT_DONT_SUPPORT_TYPE_KWARG = (
    "store_const",
    "store_true",
    "store_false",
    "append_const",
    "count",
    "help",
    "version",
)
Action = Optional[
    Literal[
        "store",
        "store_const",
        "store_true",
        "store_false",
        "append",
        "append_const",
        "count",
        "help",
        "version",
        "extend",
    ]
]
ContainerTypes = Tuple[Union[Type[List[object]], Type[Tuple[object, ...]]], ...]


class FileProtocol(Protocol):
    """A protocol that defines the methods expected from file-like objects."""

    def read(self, n: int = -1) -> str: ...
    def write(self, s: str) -> int: ...
    def close(self) -> None: ...


class TypedFileType:
    """A wrapper around argparse. FileType that returns FileProtocol compatible objects."""

    def __init__(
        self, mode: str, bufsize: int = -1, encoding: Optional[str] = None, errors: Optional[str] = None
    ) -> None:
        self.file_type = argparse.FileType(mode, bufsize, encoding, errors)

    def __call__(self, string: str) -> Union[IO[str], IO[bytes]]:
        return self.file_type(string)


def get_origin(obj: object) -> Optional[object]:
    """Get the origin of a type, similar to typing.get_origin.

    e.g. List[int] -> list
         List -> None"""
    return tp.get_origin(obj)


def get_args(obj: object) -> Tuple[object, ...]:
    """Get the arguments of a type, similar to typing.get_args."""
    return tp.get_args(obj)
