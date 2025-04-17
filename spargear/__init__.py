import argparse
import logging
import warnings
from dataclasses import dataclass, field, fields
from typing import (
    IO,
    Callable,
    Dict,
    Generic,
    Iterable,
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
from typing import get_args as typing_get_args
from typing import get_origin as typing_get_origin
from typing import get_type_hints as typing_get_type_hints

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
                elif attr_value in get_args(SUPPRESS_LITERAL_TYPE):
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
    element_type: Optional[Type[object]]  # The E in ArgumentSpec[List[E]] or ArgumentSpec[Tuple[E, ...]]

    @classmethod
    def from_hint(cls, hints: Dict[str, object], attr_name: str) -> Optional["ArgumentSpecType"]:
        """Extract type information from type hints."""
        if attr_name not in hints:
            return None

        hint = hints[attr_name]
        hint_origin = get_origin(hint)
        hint_args = get_args(hint)

        if (
            hint_origin is not None
            and isinstance(hint_origin, type)
            and issubclass(hint_origin, ArgumentSpec)
            and hint_args
        ):
            T: object = hint_args[0]  # Extract T
            element_type: Optional[Type[object]]

            outer_origin = get_origin(T)
            if isinstance(outer_origin, type):
                if issubclass(outer_origin, list) and (args := get_args(T)) and (isinstance(arg := args[0], type)):
                    element_type = arg  # Extract E from List[E]
                elif issubclass(outer_origin, tuple) and (args := get_args(T)):
                    # For Tuple[E, ...] or Tuple[E1, E2, ...]
                    first_type: Optional[Type[object]] = next((arg for arg in args if isinstance(arg, type)), None)
                    if first_type is not None:
                        element_type = first_type
                    else:
                        element_type = None
                else:
                    element_type = None
            else:
                element_type = None

            return cls(T=T, element_type=element_type)
        return None

    @property
    def choices(self) -> Optional[Tuple[object, ...]]:
        """Extract choices from Literal types."""
        T_origin = get_origin(self.T)

        # Handle ArgumentSpec[List[Literal["A", "B"]]]
        if (
            isinstance(T_origin, type)
            and issubclass(T_origin, (list, tuple))
            and (args := get_args(self.T))
            and get_origin(arg := args[0]) is Literal
            and (literals := get_args(arg))
        ):
            return literals

        # Handle ArgumentSpec[Literal["A", "B"]]
        elif T_origin is Literal and (args := get_args(self.T)):
            return args

        return None

    @property
    def type(self) -> Optional[Type[object]]:
        """Determine the appropriate type for the argument."""
        if self.element_type is not None:
            return self.element_type
        if isinstance(self.T, type):
            return self.T
        return None

    @property
    def should_return_as_list(self) -> bool:
        """Determines if the argument should be returned as a list."""
        T_origin = get_origin(self.T)
        return isinstance(T_origin, type) and issubclass(T_origin, list)

    @property
    def should_return_as_tuple(self) -> bool:
        """Determines if the argument should be returned as a tuple."""
        T_origin = get_origin(self.T)
        return isinstance(T_origin, type) and issubclass(T_origin, tuple)

    @property
    def tuple_nargs(self) -> Optional[Union[int, Literal["+"]]]:
        """Determine the number of arguments for a tuple type."""
        if self.should_return_as_tuple and (args := get_args(self.T)):
            if Ellipsis not in args:
                return len(args)
            else:
                return "+"
        return None


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

    __argspec__: Dict[str, ArgumentSpec[object]]
    __argspectype__: Dict[str, ArgumentSpecType]
    __subcommands__: Dict[str, SubcommandSpec["BaseArguments"]]
    __parent__: Optional[Type["BaseArguments"]] = None

    def __init__(self, args: Optional[Sequence[str]] = None) -> None:
        """
        Initializes the BaseArguments instance and loads arguments from the command line or a given list of arguments.
        If no arguments are provided, it uses sys.argv[1:] by default.
        """
        # only load at root
        if self.__class__.__parent__ is None:
            self.load(args)

    @classmethod
    def load(cls, args: Optional[Sequence[str]] = None) -> Optional["BaseArguments"]:
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

        return current_inst

    @classmethod
    def __getitem__(cls, key: str) -> Optional[object]:
        return cls.__argspec__[key].value

    @classmethod
    def get(cls, key: str) -> Optional[object]:
        return cls.__argspec__[key].value

    @classmethod
    def keys(cls) -> Iterable[str]:
        yield from (k for k, _v in cls.items())

    @classmethod
    def values(cls) -> Iterable[object]:
        yield from (v for _k, v in cls.items())

    @classmethod
    def items(cls) -> Iterable[Tuple[str, object]]:
        yield from ((key, spec.value) for key, spec in cls._iter_specs() if spec.value is not None)

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
        for key, spec in cls._iter_specs():
            is_positional = not any(n.startswith("-") for n in spec.name_or_flags)
            attr = spec.name_or_flags[0] if is_positional else (spec.dest or key)
            if not hasattr(args, attr):
                continue
            val = getattr(args, attr)
            if val is argparse.SUPPRESS:
                continue
            if st := cls.__argspectype__.get(key):
                if st.should_return_as_list:
                    if isinstance(val, list):
                        val = cast(List[object], val)
                    elif val is not None:
                        val = [val]
                elif st.should_return_as_tuple:
                    if isinstance(val, tuple):
                        val = cast(Tuple[object, ...], val)
                    elif val is not None:
                        if isinstance(val, list):
                            val = tuple(cast(List[object], val))
                        else:
                            val = (val,)
            spec.value = val

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls.__argspec__ = {}
        cls.__argspectype__ = {}
        cls.__subcommands__ = {}

        for current_cls in reversed(cls.__mro__):
            if current_cls in (object, BaseArguments):
                continue

            vars_ = vars(current_cls)

            # Subcommands
            for attr_name, attr_value in vars_.items():
                if isinstance(attr_value, SubcommandSpec):
                    attr_value = cast(SubcommandSpec["BaseArguments"], attr_value)
                    cls.__subcommands__[attr_value.name] = attr_value
                    if attr_value.argument_class:
                        attr_value.argument_class.__parent__ = cls

            # ArgumentSpecs
            try:
                hints: Dict[str, object] = get_type_hints(current_cls)
                for attr_name, attr_value in vars_.items():
                    if isinstance(attr_value, ArgumentSpec):
                        spec: ArgumentSpec[object] = cast(ArgumentSpec[object], attr_value)
                        if spec_type := ArgumentSpecType.from_hint(hints, attr_name):
                            cls.__argspectype__[attr_name] = spec_type
                            if literals := spec_type.choices:
                                spec.choices = literals
                            if spec.type is None and (th := spec_type.type):
                                spec.type = th
                            if tn := spec_type.tuple_nargs:
                                spec.nargs = tn
                        cls.__argspec__[attr_name] = spec
            except Exception as e:
                warnings.warn(
                    f"Could not fully analyze type hints for {current_cls.__name__}: {e}",
                    stacklevel=2,
                )
                for attr_name, attr_value in vars_.items():
                    if isinstance(attr_value, ArgumentSpec) and attr_name not in cls.__argspec__:
                        cls.__argspec__[attr_name] = attr_value

    @classmethod
    def _iter_specs(cls) -> Iterable[Tuple[str, ArgumentSpec[object]]]:
        yield from cls.__argspec__.items()

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
        for key, spec in cls._iter_specs():
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
                required=not cls.__argspec__ and bool(cls.__subcommands__),
            )
            for name, subc in cls._iter_subcommands():
                subparser = subparsers.add_parser(
                    name,
                    help=subc.help,
                    description=subc.description or subc.help,
                )
                if subc.argument_class:
                    subc.argument_class._configure_parser(subparser)


def get_origin(obj: object) -> Optional[object]:
    """Get the origin of a type, similar to typing.get_origin."""
    return typing_get_origin(obj)


def get_args(obj: object) -> Tuple[object, ...]:
    """Get the arguments of a type, similar to typing.get_args."""
    return typing_get_args(obj)


def get_type_hints(obj: object) -> Dict[str, object]:
    """Get the type hints of a class or function, similar to typing.get_type_hints."""
    return typing_get_type_hints(obj)
