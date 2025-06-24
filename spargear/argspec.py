import argparse
from dataclasses import dataclass, field, fields
from typing import (
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from ._typing import (
    ACTION_TYPES_THAT_DONT_SUPPORT_TYPE_KWARG,
    SUPPRESS_LITERAL_TYPE,
    Action,
    TypedFileType,
    ensure_no_optional,
    get_args,
    get_arguments_of_container_types,
    get_literals,
    get_origin,
    get_type_of_element_of_container_types,
)

T = TypeVar("T")


@dataclass
class ArgumentSpec(Generic[T]):
    """Represents the specification for a command-line argument."""

    name_or_flags: List[str]
    action: Action = None
    nargs: Optional[Union[int, Literal["*", "+", "?"]]] = None
    const: Optional[T] = None
    default: Optional[Union[T, SUPPRESS_LITERAL_TYPE]] = None
    default_factory: Optional[Callable[[], T]] = None
    choices: Optional[Sequence[T]] = None
    required: bool = False
    help: str = ""
    metavar: Optional[str] = None
    version: Optional[str] = None
    type: Optional[
        Union[Callable[[str], T], Type[argparse.FileType], TypedFileType]
    ] = None
    dest: Optional[str] = None
    value: Optional[T] = field(init=False, default=None)  # Parsed value stored here

    def __post_init__(self) -> None:
        """Validate that default and default_factory are not both set."""
        if self.default is not None and self.default_factory is not None:
            raise ValueError("Cannot specify both 'default' and 'default_factory'")

    def unwrap(self) -> T:
        """Returns the value, raising an error if it's None."""
        if self.value is None:
            raise ValueError(f"Value for {self.name_or_flags} is None.")
        return self.value

    def get_add_argument_kwargs(self) -> Dict[str, object]:
        """Prepares keyword arguments for argparse.ArgumentParser.add_argument."""
        kwargs: Dict[str, object] = {}
        argparse_fields: Set[str] = {
            f.name
            for f in fields(self)
            if f.name not in ("name_or_flags", "value", "default_factory")
        }
        for field_name in argparse_fields:
            attr_value: object = getattr(self, field_name)
            if field_name == "default":
                if attr_value is None:
                    # If we have a default_factory, don't set default in argparse
                    if self.default_factory is not None:
                        kwargs[field_name] = argparse.SUPPRESS
                    else:
                        pass  # Keep default=None if explicitly set or inferred
                elif attr_value in get_args(SUPPRESS_LITERAL_TYPE):
                    kwargs[field_name] = argparse.SUPPRESS
                else:
                    kwargs[field_name] = attr_value
            elif attr_value is not None:
                if (
                    field_name == "type"
                    and self.action in ACTION_TYPES_THAT_DONT_SUPPORT_TYPE_KWARG
                ):
                    continue
                kwargs[field_name] = attr_value
        return kwargs

    def apply_default_factory(self) -> None:
        """Apply the default factory if value is None and default_factory is set."""
        if self.value is None and self.default_factory is not None:
            self.value = self.default_factory()


class ArgumentSpecType(NamedTuple):
    """Represents the type information extracted from ArgumentSpec type hints."""

    type_no_optional_or_spec: object  # The T in ArgumentSpec[T]
    is_specless_type: bool = False

    @classmethod
    def from_type_hint(cls, type_hint: object):
        """Extract type information from a type hint."""
        type_no_spec: object = ensure_no_argspec(type_hint)  # pyright: ignore[reportPrivateUsage]
        return cls(
            type_no_optional_or_spec=ensure_no_optional(type_no_spec),
            is_specless_type=type_hint is type_no_spec,
        )

    @property
    def choices(self) -> Optional[Tuple[object, ...]]:
        """Extract choices from Literal types."""
        return get_literals(
            type_no_optional_or_spec=self.type_no_optional_or_spec,
            container_types=(list, tuple),
        )

    @property
    def type(self) -> Optional[Type[object]]:
        """Determine the appropriate type for the argument."""
        t = get_type_of_element_of_container_types(
            type_no_optional_or_spec=self.type_no_optional_or_spec,
            container_types=(list, tuple),
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
                type_no_optional_or_spec=self.type_no_optional_or_spec,
                container_types=(list,),
            )
            is not None
        )

    @property
    def should_return_as_tuple(self) -> bool:
        """Determines if the argument should be returned as a tuple."""
        return (
            get_arguments_of_container_types(
                type_no_optional_or_spec=self.type_no_optional_or_spec,
                container_types=(tuple,),
            )
            is not None
        )

    @property
    def tuple_nargs(self) -> Optional[Union[int, Literal["+"]]]:
        """Determine the number of arguments for a tuple type."""
        if self.should_return_as_tuple and (
            args := get_args(self.type_no_optional_or_spec)
        ):
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


def ensure_no_argspec(t: object) -> object:
    """Unwraps the ArgumentSpec type to get the actual type."""
    if (
        (origin := get_origin(t)) is not None
        and isinstance(origin, type)
        and issubclass(origin, ArgumentSpec)
        and (args := get_args(t))
    ):
        # Extract T from ArgumentSpec[T]
        return args[0]
    return t
