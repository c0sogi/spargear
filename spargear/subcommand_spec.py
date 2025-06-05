from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, Optional, Type, TypeVar

if TYPE_CHECKING:
    from .base_arguments import BaseArguments

S = TypeVar("S", bound="BaseArguments")


@dataclass
class SubcommandSpec(Generic[S]):
    """Represents a subcommand specification for command-line interfaces."""

    name: str
    """The name of the subcommand."""
    argument_class: Type[S]
    """The BaseArguments subclass that defines the subcommand's arguments."""
    help: str = ""
    """Brief help text for the subcommand."""
    description: Optional[str] = None
    """Detailed description of the subcommand."""
