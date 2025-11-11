from ._typing import Annotated
from .argspec import ArgumentSpec, ArgumentSpecType
from .arguments import RunnableArguments, SubcommandArguments
from .base import BaseArguments
from .subcommand import SubcommandSpec, subcommand, subcommandclass

__all__ = [
    # Core classes
    "BaseArguments",
    "ArgumentSpec",
    # Subcommand support (recommended)
    "subcommand",
    "subcommandclass",
    "SubcommandSpec",
    # Advanced features
    "RunnableArguments",
    "SubcommandArguments",
    "ArgumentSpecType",
    # Utilities
    "Annotated",
]
