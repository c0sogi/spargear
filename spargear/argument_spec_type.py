from typing import Dict, Literal, NamedTuple, Optional, Tuple, Type, Union, get_args

from .argument_spec import ArgumentSpec
from .type_helper import (
    ensure_no_optional,
    get_arguments_of_container_types,
    get_literals,
    get_type_of_element_of_container_types,
)


class ArgumentSpecType(NamedTuple):
    """Represents the type information extracted from ArgumentSpec type hints."""

    type_no_optional_or_spec: object  # The T in ArgumentSpec[T]
    is_specless_type: bool = False

    @classmethod
    def from_type_hint(cls, type_hint: object):
        """Extract type information from a type hint."""
        type_no_spec: object = ArgumentSpec._unwrap_argument_spec(type_hint)  # pyright: ignore[reportPrivateUsage]
        return cls(
            type_no_optional_or_spec=ensure_no_optional(type_no_spec),
            is_specless_type=type_hint is type_no_spec,
        )

    @property
    def choices(self) -> Optional[Tuple[object, ...]]:
        """Extract choices from Literal types."""
        return get_literals(type_no_optional_or_spec=self.type_no_optional_or_spec, container_types=(list, tuple))

    @property
    def type(self) -> Optional[Type[object]]:
        """Determine the appropriate type for the argument."""
        t = get_type_of_element_of_container_types(
            type_no_optional_or_spec=self.type_no_optional_or_spec, container_types=(list, tuple)
        )
        if t is not None:
            return t
        if isinstance(self.type_no_optional_or_spec, type):
            return self.type_no_optional_or_spec
        return None

    @property
    def should_return_as_list(self) -> bool:
        """Determines if the argument should be returned as a list."""
        return (
            get_arguments_of_container_types(
                type_no_optional_or_spec=self.type_no_optional_or_spec, container_types=(list,)
            )
            is not None
        )

    @property
    def should_return_as_tuple(self) -> bool:
        """Determines if the argument should be returned as a tuple."""
        return (
            get_arguments_of_container_types(
                type_no_optional_or_spec=self.type_no_optional_or_spec, container_types=(tuple,)
            )
            is not None
        )

    @property
    def tuple_nargs(self) -> Optional[Union[int, Literal["+"]]]:
        """Determine the number of arguments for a tuple type."""
        if self.should_return_as_tuple and (args := get_args(self.type_no_optional_or_spec)):
            if Ellipsis not in args:
                return len(args)
            else:
                return "+"
        return None

    @property
    def basic_info(self) -> Dict[str, object]:
        """Returns a dictionary with basic information about the argument."""
        return {
            "type_no_optional_or_spec": self.type_no_optional_or_spec,
            "is_specless_type": self.is_specless_type,
            "choices": self.choices,
            "type": self.type,
            "should_return_as_list": self.should_return_as_list,
            "should_return_as_tuple": self.should_return_as_tuple,
            "tuple_nargs": self.tuple_nargs,
        }
