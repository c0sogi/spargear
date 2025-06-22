from ._typing import SUPPRESS, Action, FileProtocol, TypedFileType
from .argument_spec import ArgumentSpec
from .argument_spec_type import ArgumentSpecType
from .arguments import RunnableArguments, SubcommandArguments
from .base_arguments import BaseArguments
from .subcommand_spec import SubcommandSpec, subcommand

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
]
