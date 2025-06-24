import argparse
import ast
import inspect
import logging
import sys
import textwrap
import types
from functools import partial

if sys.version_info < (3, 9):
    import typing_extensions as typing

else:
    import typing

Annotated = typing.Annotated
get_type_hints = typing.get_type_hints

SUPPRESS_LITERAL_TYPE = typing.Literal["==SUPPRESS=="]
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
Action = typing.Optional[
    typing.Literal[
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
ContainerTypes = typing.Tuple[
    typing.Union[
        typing.Type[typing.List[object]], typing.Type[typing.Tuple[object, ...]]
    ],
    ...,
]

logger = logging.getLogger(__name__)


class FileProtocol(typing.Protocol):
    """A protocol that defines the methods expected from file-like objects."""

    def read(self, n: int = -1) -> str: ...
    def write(self, s: str) -> int: ...
    def close(self) -> None: ...


class TypedFileType:
    """A wrapper around argparse. FileType that returns FileProtocol compatible objects."""

    def __init__(
        self,
        mode: str,
        bufsize: int = -1,
        encoding: typing.Optional[str] = None,
        errors: typing.Optional[str] = None,
    ) -> None:
        self.file_type = argparse.FileType(mode, bufsize, encoding, errors)

    def __call__(self, string: str) -> typing.Union[typing.IO[str], typing.IO[bytes]]:
        return self.file_type(string)


def get_origin(obj: object) -> typing.Optional[object]:
    """Get the origin of a type, similar to typing.get_origin.

    e.g. typing.List[int] -> list
         typing.List -> None"""
    return typing.get_origin(obj)


def get_args(obj: object) -> typing.Tuple[object, ...]:
    """Get the arguments of a type, similar to typing.get_args."""
    return typing.get_args(obj)


def get_union_args(t: object) -> typing.Tuple[object, ...]:
    origin = get_origin(t)
    if origin is typing.Union:
        return get_args(t)
    if sys.version_info >= (3, 10) and origin is types.UnionType:
        return get_args(t)
    return ()


def is_optional(t: object) -> bool:
    """Check if a type is Optional."""
    return type(None) in get_union_args(t)


def sanitize_name(name: str) -> str:
    """Sanitize a name for use as a command-line argument."""
    return name.replace("_", "-").lower().lstrip("-")


def sanitize_flag(name: str) -> str:
    """Sanitize a name for use as a command-line argument."""
    if name.isupper():
        # if the name is all uppercase, assume it's positional
        return sanitize_name(name)
    else:
        return f"--{sanitize_name(name)}"  # if the name is not all uppercase, assume it's a flag


def ensure_no_optional(t: object) -> object:
    """Ensure that the type is not Optional."""
    non_none_args = tuple(arg for arg in get_union_args(t) if arg is not type(None))
    if not non_none_args:
        return t
    if len(non_none_args) == 1:
        return non_none_args[0]
    return typing.Union[non_none_args]  # pyright: ignore[reportInvalidTypeArguments]


def get_arguments_of_container_types(
    type_no_optional_or_spec: object, container_types: ContainerTypes
) -> typing.Optional[typing.Tuple[object, ...]]:
    if isinstance(type_no_optional_or_spec, type) and issubclass(
        type_no_optional_or_spec, container_types
    ):
        return ()

    type_no_optional_or_spec = typing.cast(object, type_no_optional_or_spec)
    type_no_optional_or_spec_origin: typing.Optional[object] = get_origin(
        type_no_optional_or_spec
    )
    if isinstance(type_no_optional_or_spec_origin, type) and issubclass(
        type_no_optional_or_spec_origin, container_types
    ):
        return get_args(type_no_optional_or_spec)
    return None


def get_type_of_element_of_container_types(
    type_no_optional_or_spec: object, container_types: ContainerTypes
) -> typing.Optional[type]:
    iterable_arguments = get_arguments_of_container_types(
        type_no_optional_or_spec=type_no_optional_or_spec,
        container_types=container_types,
    )
    if iterable_arguments is None:
        return None
    else:
        return next((it for it in iterable_arguments if isinstance(it, type)), None)


def get_literals(
    type_no_optional_or_spec: object, container_types: ContainerTypes
) -> typing.Optional[typing.Tuple[object, ...]]:
    """Get the literals of the list element type."""
    if get_origin(type_no_optional_or_spec) is typing.Literal:
        # Extract literals from Literal type
        return get_args(type_no_optional_or_spec)

    elif (
        arguments_of_container_types := get_arguments_of_container_types(
            type_no_optional_or_spec=type_no_optional_or_spec,
            container_types=container_types,
        )
    ) and get_origin(
        first_argument_of_container_types := arguments_of_container_types[0]
    ) is typing.Literal:
        # Extract literals from List[Literal] or Tuple[Literal, ...]
        return get_args(first_argument_of_container_types)
    return None


def extract_attr_docstrings(cls: typing.Type[object]) -> typing.Dict[str, str]:
    """
    Extracts docstrings from class attributes.
    This function inspects the class definition and retrieves the docstrings
    associated with each attribute.
    """
    try:
        source = inspect.getsource(cls)
        source_ast = ast.parse(textwrap.dedent(source))

        docstrings: typing.Dict[str, str] = {}
        last_attr: typing.Optional[str] = None

        class_def = next(
            (node for node in source_ast.body if isinstance(node, ast.ClassDef)), None
        )
        if class_def is None:
            return {}

        for node in class_def.body:
            # Annotated assignment (e.g., `a: int`)
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                last_attr = node.target.id

            # """docstring"""
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str) and last_attr:
                    docstrings[last_attr] = node.value.value.strip()
                    last_attr = None
            else:
                last_attr = None  # cut off if we see something else

        return docstrings
    except Exception as e:
        logger.debug(f"Failed to extract docstrings from {cls.__name__}: {e}")
        return {}


def unwrap_callable(func: typing.Callable[..., object]) -> typing.Callable[..., object]:
    """
    Get the name of a callable.
    This function is used to get the name of a callable, even if it is wrapped by a decorator.
    It is used to get the name of a subcommand.
    """
    # 1) staticmethod / classmethod → unwrap __func__
    if isinstance(func, (staticmethod, classmethod)):
        func = func.__func__  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    # 2) bound method(A().method) → unwrap __func__
    func = getattr(func, "__func__", func)

    # 3) functools.partial → unwrap func
    if isinstance(func, partial):
        func = func.func

    # 4) unwrap decorator chain (functools.wraps based)
    func = inspect.unwrap(func)
    return func


def assert_type(val: object, type_: type) -> None:
    """Assert that the value is of the given type."""
    
    if not isinstance(val, type_):
        raise TypeError(f"Value `{val}` is not of type `{type_}`")
