import argparse
import ast
import inspect
import logging
import textwrap
import typing as tp
import warnings
from dataclasses import dataclass, field, fields
from traceback import print_exc
from typing import (
    IO,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Literal,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

# --- Type Definitions ---
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

T = TypeVar("T")
S = TypeVar("S", bound="BaseArguments")

logger = logging.getLogger(__name__)


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


@dataclass
class ArgumentSpec(Generic[T]):
    """Represents the specification for a command-line argument."""

    name_or_flags: List[str]
    action: Action = None
    nargs: Optional[Union[int, Literal["*", "+", "?"]]] = None
    const: Optional[T] = None
    default: Optional[Union[T, SUPPRESS_LITERAL_TYPE]] = None
    choices: Optional[Sequence[T]] = None
    required: bool = False
    help: str = ""
    metavar: Optional[str] = None
    version: Optional[str] = None
    type: Optional[Union[Callable[[str], T], Type[argparse.FileType], TypedFileType]] = None
    dest: Optional[str] = None
    value: Optional[T] = field(init=False, default=None)  # Parsed value stored here

    def unwrap(self) -> T:
        """Returns the value, raising an error if it's None."""
        if self.value is None:
            raise ValueError(f"Value for {self.name_or_flags} is None.")
        return self.value

    def get_add_argument_kwargs(self) -> Dict[str, object]:
        """Prepares keyword arguments for argparse.ArgumentParser.add_argument."""
        kwargs: Dict[str, object] = {}
        argparse_fields: set[str] = {f.name for f in fields(self) if f.name not in ("name_or_flags", "value")}
        for field_name in argparse_fields:
            attr_value: object = getattr(self, field_name)
            if field_name == "default":
                if attr_value is None:
                    pass  # Keep default=None if explicitly set or inferred
                elif attr_value in _get_args(SUPPRESS_LITERAL_TYPE):
                    kwargs[field_name] = argparse.SUPPRESS
                else:
                    kwargs[field_name] = attr_value
            elif attr_value is not None:
                if field_name == "type" and self.action in ACTION_TYPES_THAT_DONT_SUPPORT_TYPE_KWARG:
                    continue
                kwargs[field_name] = attr_value
        return kwargs


class ArgumentSpecType(NamedTuple):
    """Represents the type information extracted from ArgumentSpec type hints."""

    T: object  # The T in ArgumentSpec[T]
    type_of_list_element: Optional[type]  # The E in ArgumentSpec[List[E]] or ArgumentSpec[Tuple[E, ...]]
    is_specless_type: bool = False

    @classmethod
    def from_type_hint(cls, type_hint: object):
        """Extract type information from a type hint."""
        t = _unwrap_argument_spec(type_hint)
        return cls(
            T=t,
            type_of_list_element=_get_type_of_element_of_container_types(t, container_types=(list, tuple)),
            is_specless_type=type_hint is t,
        )

    @property
    def choices(self) -> Optional[Tuple[object, ...]]:
        """Extract choices from Literal types."""
        return _get_literals(self.T, container_types=(list, tuple))

    @property
    def type(self) -> Optional[Type[object]]:
        """Determine the appropriate type for the argument."""
        if self.type_of_list_element is not None:
            return self.type_of_list_element
        if isinstance(self.T, type):
            return self.T
        return None

    @property
    def should_return_as_list(self) -> bool:
        """Determines if the argument should be returned as a list."""
        return _get_arguments_of_container_types(self.T, container_types=(list,)) is not None

    @property
    def should_return_as_tuple(self) -> bool:
        """Determines if the argument should be returned as a tuple."""
        return _get_arguments_of_container_types(self.T, container_types=(tuple,)) is not None

    @property
    def tuple_nargs(self) -> Optional[Union[int, Literal["+"]]]:
        """Determine the number of arguments for a tuple type."""
        if self.should_return_as_tuple and (args := _get_args(self.T)):
            if Ellipsis not in args:
                return len(args)
            else:
                return "+"
        return None

    @property
    def basic_info(self) -> Dict[str, object]:
        """Returns a dictionary with basic information about the argument."""
        return {
            "T": self.T,
            "element_type": self.type_of_list_element,
            "is_specless_type": self.is_specless_type,
            "choices": self.choices,
            "type": self.type,
            "should_return_as_list": self.should_return_as_list,
            "should_return_as_tuple": self.should_return_as_tuple,
            "tuple_nargs": self.tuple_nargs,
        }


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


class BaseArguments:
    """Base class for defining arguments declaratively using ArgumentSpec."""

    __arguments__: Dict[str, Tuple[ArgumentSpec[object], ArgumentSpecType]]
    __subcommands__: Dict[str, SubcommandSpec["BaseArguments"]]
    __parent__: Optional[Type["BaseArguments"]] = None
    last_subcommand: Optional["BaseArguments"] = None

    def __init__(self, args: Optional[Sequence[str]] = None) -> None:
        """
        Initializes the BaseArguments instance and loads arguments from the command line or a given list of arguments.
        If no arguments are provided, it uses sys.argv[1:] by default.
        """
        # only load at root
        if self.__class__.__parent__ is None:
            cls = self.__class__
            parser = cls.get_parser()
            try:
                parsed_args = parser.parse_args(args)
            except SystemExit:
                raise

            # load this class's own specs
            cls.load_from_namespace(parsed_args)

            # now walk down through any subcommands
            current_cls = cls
            current_inst: Optional["BaseArguments"] = None
            while current_cls._has_subcommands():
                # top‐level uses 'subcommand', deeper levels use '<classname>_subcommand'
                if current_cls.__parent__ is None:
                    dest_name = "subcommand"
                else:
                    dest_name = f"{current_cls.__name__.lower()}_subcommand"

                subname = getattr(parsed_args, dest_name, None)
                if not subname:
                    break

                subc = current_cls.__subcommands__.get(subname)
                if not subc or not subc.argument_class:
                    break

                inst = subc.argument_class()
                subc.argument_class.load_from_namespace(parsed_args)
                current_inst = inst
                current_cls = subc.argument_class
            self.last_subcommand = current_inst

    @classmethod
    def __getitem__(cls, key: str) -> Optional[object]:
        return cls.__arguments__[key][0].value

    @classmethod
    def get(cls, key: str) -> Optional[object]:
        return cls.__arguments__[key][0].value

    @classmethod
    def keys(cls) -> Iterable[str]:
        yield from (k for k, _v in cls.items())

    @classmethod
    def values(cls) -> Iterable[object]:
        yield from (v for _k, v in cls.items())

    @classmethod
    def items(cls) -> Iterable[Tuple[str, object]]:
        yield from ((key, spec.value) for key, spec, _ in cls._iter_arguments() if spec.value is not None)

    @classmethod
    def get_parser(cls) -> argparse.ArgumentParser:
        arg_parser = argparse.ArgumentParser(
            description=cls.__doc__,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            add_help=False,
        )
        arg_parser.add_argument(
            "-h", "--help", action="help", default=argparse.SUPPRESS, help="Show this help message and exit."
        )
        cls._configure_parser(arg_parser)
        return arg_parser

    @classmethod
    def load_from_namespace(cls, args: argparse.Namespace) -> None:
        for key, spec, spec_type in cls._iter_arguments():
            is_positional = not any(n.startswith("-") for n in spec.name_or_flags)
            attr = spec.name_or_flags[0] if is_positional else (spec.dest or key)
            if not hasattr(args, attr):
                continue
            val = getattr(args, attr)
            if val is argparse.SUPPRESS:
                continue
            if spec_type.should_return_as_list:
                if isinstance(val, list):
                    val = cast(List[object], val)
                elif val is not None:
                    val = [val]
            elif spec_type.should_return_as_tuple:
                if isinstance(val, tuple):
                    val = cast(Tuple[object, ...], val)
                elif val is not None:
                    if isinstance(val, list):
                        val = tuple(cast(List[object], val))
                    else:
                        val = (val,)
            spec.value = val
            if spec_type.is_specless_type:
                setattr(cls, key, val)

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls.__arguments__ = {}
        cls.__subcommands__ = {}

        for current_cls in reversed(cls.__mro__):
            if current_cls in (object, BaseArguments):
                continue

            # Subcommands
            for attr_value in vars(current_cls).values():
                if isinstance(attr_value, SubcommandSpec):
                    attr_value = cast(SubcommandSpec["BaseArguments"], attr_value)
                    cls.__subcommands__[attr_value.name] = attr_value
                    if attr_value.argument_class:
                        attr_value.argument_class.__parent__ = cls

            # ArgumentSpecs
            docstrings = _extract_attr_docstrings(current_cls)
            for attr_name, attr_hint in _get_type_hints_without_base_arguments(current_cls):
                attr_value: Optional[object] = getattr(current_cls, attr_name, None)
                if isinstance(attr_value, ArgumentSpec):
                    spec = cast(ArgumentSpec[object], attr_value)
                else:
                    action: Optional[Action] = None
                    type: Optional[Callable[[str], object]] = None
                    if attr_hint is bool:
                        if attr_value is False:
                            # If the default is False, we want to set action to store_true
                            action = "store_true"
                        elif attr_value is True:
                            # If the default is True, we want to set action to store_false
                            action = "store_false"
                        else:
                            # If the default is None, we want to get explicit boolean value
                            def get_boolean(x: str) -> bool:
                                if x.lower() in ("true", "1", "yes"):
                                    return True
                                elif x.lower() in ("false", "0", "no"):
                                    return False
                                raise argparse.ArgumentTypeError(f"Invalid boolean value: {x}")

                            type = get_boolean

                    spec: ArgumentSpec[object] = ArgumentSpec(
                        name_or_flags=[_sanitize_name(attr_name)],
                        default=attr_value,
                        required=attr_value is None and not _is_optional(attr_hint),
                        help=docstrings.get(attr_name, ""),
                        action=action,
                        type=type,
                    )

                if attr_name in cls.__arguments__:
                    warnings.warn(f"Duplicate argument name '{attr_name}' in {current_cls.__name__}.", UserWarning)

                try:
                    spec_type: ArgumentSpecType = ArgumentSpecType.from_type_hint(attr_hint)
                    if literals := spec_type.choices:
                        spec.choices = literals
                    if spec.type is None and (th := spec_type.type):
                        spec.type = th
                    if tn := spec_type.tuple_nargs:
                        spec.nargs = tn
                    elif spec.nargs is None and spec_type.should_return_as_list or spec_type.should_return_as_tuple:
                        spec.nargs = "*"
                    cls.__arguments__[attr_name] = (spec, spec_type)
                except Exception as e:
                    print_exc()
                    warnings.warn(f"Error processing {attr_name} in {current_cls.__name__}: {e}", UserWarning)
                    continue

    @classmethod
    def _iter_arguments(cls) -> Iterable[Tuple[str, ArgumentSpec[object], ArgumentSpecType]]:
        yield from ((key, spec, spec_type) for key, (spec, spec_type) in cls.__arguments__.items())

    @classmethod
    def _iter_subcommands(cls) -> Iterable[Tuple[str, SubcommandSpec["BaseArguments"]]]:
        yield from cls.__subcommands__.items()

    @classmethod
    def _has_subcommands(cls) -> bool:
        return bool(cls.__subcommands__)

    @classmethod
    def _add_argument_to_parser(
        cls, parser: argparse.ArgumentParser, name_or_flags: List[str], **kwargs: object
    ) -> None:
        parser.add_argument(*name_or_flags, **kwargs)  # type: ignore

    @classmethod
    def _configure_parser(cls, parser: argparse.ArgumentParser) -> None:
        # 1) add this class's own arguments
        for key, spec, _ in cls._iter_arguments():
            kwargs = spec.get_add_argument_kwargs()
            is_positional = not any(name.startswith("-") for name in spec.name_or_flags)
            if is_positional:
                kwargs.pop("required", None)
                cls._add_argument_to_parser(parser, spec.name_or_flags, **kwargs)
            else:
                kwargs.setdefault("dest", key)
                cls._add_argument_to_parser(parser, spec.name_or_flags, **kwargs)

        # 2) if there are subcommands, add them at this level
        if cls._has_subcommands():
            if cls.__parent__ is None:
                dest_name = "subcommand"
            else:
                dest_name = f"{cls.__name__.lower()}_subcommand"

            subparsers = parser.add_subparsers(
                title="subcommands",
                dest=dest_name,
                help="Available subcommands",
                required=not cls.__arguments__ and bool(cls.__subcommands__),
            )
            for name, subc in cls._iter_subcommands():
                subparser = subparsers.add_parser(
                    name,
                    help=subc.help,
                    description=subc.description or subc.help,
                )
                if subc.argument_class:
                    subc.argument_class._configure_parser(subparser)


# --- Helper Functions ---


def _get_origin(obj: object) -> Optional[object]:
    """Get the origin of a type, similar to typing.get_origin.

    e.g. List[int] -> list
         List -> None"""
    return tp.get_origin(obj)


def _get_args(obj: object) -> Tuple[object, ...]:
    """Get the arguments of a type, similar to typing.get_args."""
    return tp.get_args(obj)


def _get_type_hints_without_base_arguments(obj: object) -> Iterator[Tuple[str, object]]:
    """Get type hints for an object, excluding those in BaseArguments."""
    base_arguments_attrs: List[str] = [key for key in tp.get_type_hints(BaseArguments).keys()]
    for k, v in tp.get_type_hints(obj).items():
        if k in base_arguments_attrs:
            continue
        yield k, v


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use as a command-line argument."""
    return "--" + name.replace("_", "-").lower().lstrip("-")


def _is_optional(t: object) -> bool:
    """Check if a type is Optional."""
    return _get_origin(t) is Union and len(args := _get_args(t)) == 2 and type(None) in args


def _ensure_no_optional(t: object) -> object:
    """Ensure that the type is not Optional."""
    if _get_origin(t) is Union and len(t_args := _get_args(t)) == 2 and type(None) in t_args:
        return next(arg for arg in t_args if arg is not type(None))
    else:
        return t


def _unwrap_argument_spec(t: object) -> object:
    """Unwraps the ArgumentSpec type to get the actual type."""
    if (
        (origin := _get_origin(t)) is not None
        and isinstance(origin, type)
        and issubclass(origin, ArgumentSpec)
        and (args := _get_args(t))
    ):
        # Extract T from ArgumentSpec[T]
        return args[0]
    return t


def _get_arguments_of_container_types(t: object, container_types: ContainerTypes) -> Optional[Tuple[object, ...]]:
    t_no_optional: object = _ensure_no_optional(t)
    if isinstance(t_no_optional, type) and issubclass(t_no_optional, container_types):
        return ()

    t_no_optional = cast(object, t_no_optional)
    t_no_optional_origin: Optional[object] = _get_origin(t_no_optional)
    if isinstance(t_no_optional_origin, type) and issubclass(t_no_optional_origin, container_types):
        return _get_args(t_no_optional)
    return None


def _get_type_of_element_of_container_types(t: object, container_types: ContainerTypes) -> Optional[type]:
    if (iterable_arguments := _get_arguments_of_container_types(t, container_types=container_types)) and isinstance(
        first_iterable_argument := iterable_arguments[0], type
    ):
        return first_iterable_argument  # Extract E from List[E] or Tuple[E, ...]
    return None


def _get_literals(t: object, container_types: ContainerTypes) -> Optional[Tuple[object, ...]]:
    """Get the literals of the list element type."""
    t_no_optional: object = _ensure_no_optional(t)
    if _get_origin(t_no_optional) is Literal:
        # Extract literals from Literal type
        return _get_args(t_no_optional)
    elif (
        arguments_of_container_types := _get_arguments_of_container_types(t, container_types=container_types)
    ) and _get_origin(first_argument_of_container_types := arguments_of_container_types[0]) is Literal:
        # Extract literals from List[Literal] or Tuple[Literal, ...]
        return _get_args(first_argument_of_container_types)
    return None


def _extract_attr_docstrings(cls: Type[object]) -> Dict[str, str]:
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
