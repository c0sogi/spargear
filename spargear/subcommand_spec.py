from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Generic, Optional, Type, TypeVar

if TYPE_CHECKING:
    from .base_arguments import BaseArguments

S = TypeVar("S", bound="BaseArguments")


@dataclass
class SubcommandSpec(Generic[S]):
    """Represents a subcommand specification for command-line interfaces."""

    name: str
    """The name of the subcommand."""
    argument_class: Optional[Type[S]] = None
    """The BaseArguments subclass that defines the subcommand's arguments."""
    argument_class_factory: Optional[Callable[[], Type[S]]] = None
    """A factory function that returns the BaseArguments subclass."""
    help: str = ""
    """Brief help text for the subcommand."""
    description: Optional[str] = None
    """Detailed description of the subcommand."""

    # Private field to cache the result of factory function
    _cached_argument_class: Optional[Type[S]] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate that either argument_class or argument_class_factory is provided."""
        if self.argument_class is None and self.argument_class_factory is None:
            raise ValueError("Either argument_class or argument_class_factory must be provided")
        if self.argument_class is not None and self.argument_class_factory is not None:
            raise ValueError("Only one of argument_class or argument_class_factory should be provided")

    def get_argument_class(self) -> Type[S]:
        """Get the argument class, either directly or from the factory."""
        if self.argument_class is not None:
            return self.argument_class
        elif self.argument_class_factory is not None:
            # Use cached result if available
            if self._cached_argument_class is not None:
                return self._cached_argument_class
            # Call factory and cache the result
            self._cached_argument_class = self.argument_class_factory()
            return self._cached_argument_class
        else:
            raise ValueError("No argument class or factory available")
