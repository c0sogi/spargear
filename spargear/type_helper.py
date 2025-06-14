import ast
import inspect
import logging
import sys
import textwrap
import types
import typing as tp
from typing import Dict, Literal, Optional, Tuple, Type, Union, cast

from ._typing import ContainerTypes

logger = logging.getLogger(__name__)


def get_union_args(t: object) -> Tuple[object, ...]:
    origin = get_origin(t)
    if origin is Union:
        return get_args(t)
    if sys.version_info >= (3, 10) and origin is types.UnionType:
        return get_args(t)
    return ()


def is_optional(t: object) -> bool:
    """Check if a type is Optional."""
    return type(None) in get_union_args(t)


def get_origin(obj: object) -> Optional[object]:
    """Get the origin of a type, similar to typing.get_origin.

    e.g. List[int] -> list
         List -> None"""
    return tp.get_origin(obj)


def get_args(obj: object) -> Tuple[object, ...]:
    """Get the arguments of a type, similar to typing.get_args."""
    return tp.get_args(obj)


def sanitize_name(name: str) -> str:
    """Sanitize a name for use as a command-line argument."""
    sanitized: str = name.replace("_", "-").lower().lstrip("-")
    if name.isupper():
        return sanitized  # if the name is all uppercase, assume it's positional
    else:
        return f"--{sanitized}"  # if the name is not all uppercase, assume it's a flag


def ensure_no_optional(t: object) -> object:
    """Ensure that the type is not Optional."""
    non_none_args = tuple(arg for arg in get_union_args(t) if arg is not type(None))
    if not non_none_args:
        return t
    if len(non_none_args) == 1:
        return non_none_args[0]
    return Union[non_none_args]  # pyright: ignore[reportInvalidTypeArguments]


def get_arguments_of_container_types(type_no_optional_or_spec: object, container_types: ContainerTypes) -> Optional[Tuple[object, ...]]:
    if isinstance(type_no_optional_or_spec, type) and issubclass(type_no_optional_or_spec, container_types):
        return ()

    type_no_optional_or_spec = cast(object, type_no_optional_or_spec)
    type_no_optional_or_spec_origin: Optional[object] = get_origin(type_no_optional_or_spec)
    if isinstance(type_no_optional_or_spec_origin, type) and issubclass(type_no_optional_or_spec_origin, container_types):
        return get_args(type_no_optional_or_spec)
    return None


def get_type_of_element_of_container_types(type_no_optional_or_spec: object, container_types: ContainerTypes) -> Optional[type]:
    iterable_arguments = get_arguments_of_container_types(type_no_optional_or_spec=type_no_optional_or_spec, container_types=container_types)
    if iterable_arguments is None:
        return None
    else:
        return next((it for it in iterable_arguments if isinstance(it, type)), None)


def get_literals(type_no_optional_or_spec: object, container_types: ContainerTypes) -> Optional[Tuple[object, ...]]:
    """Get the literals of the list element type."""
    if get_origin(type_no_optional_or_spec) is Literal:
        # Extract literals from Literal type
        return get_args(type_no_optional_or_spec)

    elif (arguments_of_container_types := get_arguments_of_container_types(type_no_optional_or_spec=type_no_optional_or_spec, container_types=container_types)) and get_origin(
        first_argument_of_container_types := arguments_of_container_types[0]
    ) is Literal:
        # Extract literals from List[Literal] or Tuple[Literal, ...]
        return get_args(first_argument_of_container_types)
    return None


def extract_attr_docstrings(cls: Type[object]) -> Dict[str, str]:
    """
    Extracts docstrings from class attributes.
    This function inspects the class definition and retrieves the docstrings
    associated with each attribute.
    """
    try:
        source = inspect.getsource(cls)
        source_ast = ast.parse(textwrap.dedent(source))

        docstrings: Dict[str, str] = {}
        last_attr: Optional[str] = None

        class_def = next((node for node in source_ast.body if isinstance(node, ast.ClassDef)), None)
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
        logger.warning(f"Failed to extract docstrings from {cls.__name__}: {e}")
        return {}
