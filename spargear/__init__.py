from ._typing import SUPPRESS, Action, Annotated, FileProtocol, TypedFileType
from .argspec import ArgumentSpec, ArgumentSpecType
from .arguments import RunnableArguments, SubcommandArguments
from .base import BaseArguments
from .subcommand import SubcommandSpec, subcommand

__all__ = [
    # Core classes
    "BaseArguments",
    "ArgumentSpec",
    # Subcommand support (recommended)
    "subcommand",
    "SubcommandSpec",
    # Advanced features
    "RunnableArguments",
    "SubcommandArguments",
    "ArgumentSpecType",
    # Utilities
    "SUPPRESS",
    "Action",
    "FileProtocol",
    "TypedFileType",
    "Annotated",
]
