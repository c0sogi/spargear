import argparse
import inspect
import json
import pickle
import typing as tp
import warnings
from copy import deepcopy
from dataclasses import field, make_dataclass
from pathlib import Path
from traceback import print_exc
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from ._typing import Action
from .argument_spec import ArgumentSpec
from .argument_spec_type import ArgumentSpecType
from .subcommand_spec import SubcommandSpec
from .type_helper import extract_attr_docstrings, is_optional, sanitize_name


class BaseArguments:
    """Base class for defining arguments declaratively using ArgumentSpec."""

    __arguments__: Dict[str, Tuple[ArgumentSpec[object], ArgumentSpecType]]
    __subcommands__: Dict[str, SubcommandSpec["BaseArguments"]]
    __subcommand: Optional["BaseArguments"] = None

    @property
    def last_subcommand(self) -> Optional["BaseArguments"]:
        return self.__subcommand

    def __init__(self, args: Optional[Sequence[str]] = None, _internal_init: bool = False) -> None:
        """
        Initializes the BaseArguments instance and loads arguments from the command line or a given list of arguments.
        If no arguments are provided, it uses sys.argv[1:] by default.
        """
        # Initialize instance-specific argument values and specs
        self.__instance_values__: Dict[str, object] = {}
        self.__instance_specs__: Dict[str, ArgumentSpec[object]] = {}

        # only load at root (내부 생성이 아닌 경우)
        if not _internal_init:
            cls = self.__class__
            parser = cls.get_parser()
            try:
                parsed_args = parser.parse_args(args)
            except SystemExit:
                raise

            # load this class's own specs
            self.__load_from_namespace(parsed_args)

            # now walk down through any subcommands
            current_cls = cls
            current_inst: Optional["BaseArguments"] = None
            depth = 0
            while current_cls._has_subcommands():
                # 각 레벨에 맞는 dest 이름 사용
                if depth == 0:
                    dest_name = "subcommand"
                else:
                    dest_name = f"subcommand_depth_{depth}"

                subname = getattr(parsed_args, dest_name, None)
                if not subname:
                    break

                subc = current_cls.__subcommands__.get(subname)
                if not subc:
                    break

                try:
                    argument_class = subc.get_argument_class()
                except Exception:
                    break

                # Create subcommand instance with internal flag
                inst = argument_class(args=None, _internal_init=True)
                # Load values from parsed args
                inst.__load_from_namespace(parsed_args)
                current_inst = inst
                current_cls = argument_class
                depth += 1
            self.__subcommand = current_inst

    def __getitem__(self, key: str) -> Optional[object]:
        return self.__instance_values__.get(key, self.__class__.__arguments__[key][0].value)

    def __getattribute__(self, name: str) -> object:
        """Override attribute access to return instance-specific ArgumentSpec objects or values."""
        # For special attributes, use normal access
        if name.startswith("_") or name in ("last_subcommand", "get", "keys", "values", "items"):
            return super().__getattribute__(name)

        # Check if this is an ArgumentSpec attribute
        try:
            cls = super().__getattribute__("__class__")
            if hasattr(cls, "__arguments__") and name in cls.__arguments__:
                spec, spec_type = cls.__arguments__[name]

                # For specless types, return the actual value
                if spec_type.is_specless_type:
                    instance_values = super().__getattribute__("__instance_values__")
                    if name in instance_values:
                        return instance_values[name]
                    else:
                        # Return the default value or None
                        return spec.default

                # For ArgumentSpec types, return the instance-specific spec
                instance_specs = super().__getattribute__("__instance_specs__")
                if name in instance_specs:
                    return instance_specs[name]
                else:
                    # Create instance copy if not exists
                    import copy

                    instance_spec = copy.deepcopy(spec)
                    instance_specs[name] = instance_spec
                    return instance_spec
        except AttributeError:
            pass

        # Use normal attribute access for everything else
        return super().__getattribute__(name)

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

            # ArgumentSpecs
            docstrings = extract_attr_docstrings(current_cls)
            for attr_name, attr_hint in _get_type_hints(current_cls):
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

                            # Check if attr_value is a callable (potential default factory)
                    default_factory: Optional[Callable[[], object]] = None
                    default_value: Optional[object] = attr_value

                    # If attr_value is callable and not a type, treat it as default_factory
                    if callable(attr_value) and not inspect.isclass(attr_value) and attr_value is not type:
                        default_factory = attr_value
                        default_value = None

                    spec: ArgumentSpec[object] = ArgumentSpec(
                        name_or_flags=[sanitize_name(attr_name)],
                        default=default_value,
                        default_factory=default_factory,
                        required=default_value is None and default_factory is None and not is_optional(attr_hint),
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

    def get(self, key: str) -> Optional[object]:
        return self.__instance_values__.get(key, self.__class__.__arguments__[key][0].value)

    def keys(self) -> Iterable[str]:
        yield from (k for k, _v in self.items())

    def values(self) -> Iterable[object]:
        yield from (v for _k, v in self.items())

    def items(self) -> Iterable[Tuple[str, object]]:
        for key, spec, _ in self.__class__.__iter_arguments():
            value = self.__instance_values__.get(key, spec.value)
            if value is not None:
                yield key, value

    def to_dataclass(self, class_name: Optional[str] = None) -> Any:
        """Convert the BaseArguments instance to a dataclass instance.

        Args:
            class_name: Name for the generated dataclass. Defaults to {ClassName}Config.

        Returns:
            A dataclass instance with all the argument values.
        """
        if class_name is None:
            class_name = f"{self.__class__.__name__}Config"

        # Collect all argument values
        field_definitions: List[Tuple[str, type, Any]] = []
        field_values: Dict[str, Any] = {}

        for key, spec, spec_type in self.__class__.__iter_arguments():
            # Get the value from instance
            if hasattr(self, "__instance_values__") and key in self.__instance_values__:
                value = self.__instance_values__[key]
            else:
                value = spec.default

            # Determine the field type
            field_type = spec_type.type_no_optional_or_spec if spec_type.type_no_optional_or_spec is not object else Any
            if not isinstance(field_type, type):
                field_type = Any

            # Create field definition - handle mutable defaults
            if isinstance(value, (list, dict, set)):
                # Use default_factory for mutable types
                def make_factory(val: Any) -> Callable[[], Any]:
                    if hasattr(val, "copy"):
                        return lambda: val.copy()
                    else:
                        return lambda: list(val)

                field_definitions.append((key, cast(type, field_type), field(default_factory=make_factory(value))))
            else:
                field_definitions.append((key, cast(type, field_type), field(default=value)))
            field_values[key] = value

        # Create the dataclass
        DataclassType = make_dataclass(class_name, field_definitions)

        # Create instance with current values
        return DataclassType(**field_values)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the BaseArguments instance to a dictionary.

        Returns:
            A dictionary with all argument names and their values.
        """
        result: Dict[str, Any] = {}
        for key, spec, _ in self.__class__.__iter_arguments():
            if hasattr(self, "__instance_values__") and key in self.__instance_values__:
                value = self.__instance_values__[key]
            else:
                value = spec.default

            # Only include non-None values
            if value is not None:
                result[key] = value

        return result

    def to_json(self, file_path: Optional[Union[str, Path]] = None, **kwargs: Any) -> str:
        """Serialize the BaseArguments instance to JSON.

        Args:
            file_path: Optional file path to save the JSON. If provided, saves to file.
            **kwargs: Additional arguments passed to json.dumps().

        Returns:
            JSON string representation.
        """
        data = self.to_dict()

        # Convert non-serializable types
        def json_serializer(obj: Any) -> Any:
            if isinstance(obj, Path):
                return str(obj)
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            else:
                return str(obj)

        json_str = json.dumps(data, default=json_serializer, indent=2, **kwargs)

        if file_path:
            Path(file_path).write_text(json_str, encoding="utf-8")

        return json_str

    def to_pickle(self, file_path: Union[str, Path]) -> None:
        """Serialize the BaseArguments instance to a pickle file.

        Args:
            file_path: File path to save the pickle data.
        """
        data = self.to_dict()
        with open(file_path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], args: Optional[Sequence[str]] = None):
        """Create a BaseArguments instance from a dictionary.

        Args:
            data: Dictionary with argument names and values.
            args: Optional command line arguments to parse first.

        Returns:
            A new BaseArguments instance with values from the dictionary.
        """
        # Create instance with command line args first (if provided)
        instance = cls(args or [])

        # Apply dictionary values only for keys not set by command line
        if hasattr(instance, "__instance_values__"):
            for key, value in data.items():
                if key in cls.__arguments__:
                    # Only set if not already set by command line args or if it's still the default
                    spec, _ = cls.__arguments__[key]

                    # Set from dict if: not in instance values, is None, or is still the default value
                    if key not in instance.__instance_values__ or instance.__instance_values__[key] is None or instance.__instance_values__[key] == spec.default:
                        instance.__instance_values__[key] = value
                        # Also update instance specs if they exist
                        if hasattr(instance, "__instance_specs__") and key in instance.__instance_specs__:
                            instance.__instance_specs__[key].value = value

        return instance

    @classmethod
    def from_json(cls, json_data: Union[str, Path], args: Optional[Sequence[str]] = None):
        """Create a BaseArguments instance from JSON data.

        Args:
            json_data: JSON string or path to JSON file.
            args: Optional command line arguments to parse first.

        Returns:
            A new BaseArguments instance with values from the JSON.
        """
        if Path(str(json_data)).exists():
            # It's a file path
            data = json.loads(Path(json_data).read_text(encoding="utf-8"))
        else:
            # It's a JSON string
            data = json.loads(str(json_data))

        return cls.from_dict(data, args)

    @classmethod
    def from_pickle(cls, file_path: Union[str, Path], args: Optional[Sequence[str]] = None):
        """Create a BaseArguments instance from a pickle file.

        Args:
            file_path: Path to the pickle file.
            args: Optional command line arguments to parse first.

        Returns:
            A new BaseArguments instance with values from the pickle file.
        """
        with open(file_path, "rb") as f:
            data = pickle.load(f)

        return cls.from_dict(data, args)

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update the current instance with values from a dictionary.

        Args:
            data: Dictionary with argument names and values to update.
        """
        if hasattr(self, "__instance_values__"):
            for key, value in data.items():
                if key in self.__class__.__arguments__:
                    self.__instance_values__[key] = value
                    # Also update instance specs if they exist
                    if hasattr(self, "__instance_specs__") and key in self.__instance_specs__:
                        self.__instance_specs__[key].value = value

    def save_config(self, file_path: Union[str, Path], format: Literal["json", "pickle"] = "json") -> None:
        """Save the current configuration to a file.

        Args:
            file_path: Path to save the configuration.
            format: File format, either "json" or "pickle".
        """
        if format == "json":
            self.to_json(file_path)
        elif format == "pickle":
            self.to_pickle(file_path)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'pickle'.")

    @classmethod
    def load_config(
        cls,
        file_path: Union[str, Path],
        format: Optional[Literal["json", "pickle"]] = None,
        args: Optional[Sequence[str]] = None,
    ):
        """Load configuration from a file.

        Args:
            file_path: Path to the configuration file.
            format: File format. If None, inferred from file extension.
            args: Optional command line arguments to parse first.

        Returns:
            A new BaseArguments instance with values from the file.
        """
        path = Path(file_path)

        if format is None:
            # Infer format from extension
            if path.suffix.lower() == ".json":
                format = "json"
            elif path.suffix.lower() in (".pkl", ".pickle"):
                format = "pickle"
            else:
                raise ValueError(f"Cannot infer format from extension: {path.suffix}")

        if format == "json":
            return cls.from_json(path, args)
        elif format == "pickle":
            return cls.from_pickle(path, args)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @classmethod
    def get_parser(cls) -> argparse.ArgumentParser:
        arg_parser = argparse.ArgumentParser(
            description=cls.__doc__,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            add_help=False,
        )
        arg_parser.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help="Show this help message and exit.")
        cls.__configure_parser(arg_parser)
        return arg_parser

    @classmethod
    def __iter_arguments(cls) -> Iterable[Tuple[str, ArgumentSpec[object], ArgumentSpecType]]:
        yield from ((key, spec, spec_type) for key, (spec, spec_type) in cls.__arguments__.items())

    @classmethod
    def __iter_subcommands(cls) -> Iterable[Tuple[str, SubcommandSpec["BaseArguments"]]]:
        yield from cls.__subcommands__.items()

    @classmethod
    def _has_subcommands(cls) -> bool:
        return bool(cls.__subcommands__)

    @classmethod
    def __add_argument_to_parser(cls, parser: argparse.ArgumentParser, name_or_flags: List[str], **kwargs: object) -> None:
        parser.add_argument(*name_or_flags, **kwargs)  # type: ignore

    @classmethod
    def __configure_parser(cls, parser: argparse.ArgumentParser, _depth: int = 0) -> None:
        # 1) add this class's own arguments
        for key, spec, _ in cls.__iter_arguments():
            kwargs = spec.get_add_argument_kwargs()
            is_positional = not any(name.startswith("-") for name in spec.name_or_flags)
            if is_positional:
                kwargs.pop("required", None)
                cls.__add_argument_to_parser(parser, spec.name_or_flags, **kwargs)
            else:
                kwargs.setdefault("dest", key)
                cls.__add_argument_to_parser(parser, spec.name_or_flags, **kwargs)

        # 2) if there are subcommands, add them at this level
        if cls._has_subcommands():
            # 각 레벨에 고유한 dest 이름 사용
            if _depth == 0:
                dest_name = "subcommand"
            else:
                dest_name = f"subcommand_depth_{_depth}"

            subparsers = parser.add_subparsers(
                title="subcommands",
                dest=dest_name,
                help="Available subcommands",
                required=not cls.__arguments__ and bool(cls.__subcommands__),
            )
            for name, subc in cls.__iter_subcommands():
                subparser = subparsers.add_parser(
                    name,
                    help=subc.help,
                    description=subc.description or subc.help,
                )
                try:
                    argument_class = subc.get_argument_class()
                    argument_class.__configure_parser(subparser, _depth + 1)
                except Exception:
                    # If getting the argument class fails, skip this subcommand configuration
                    pass

    def __load_from_namespace(self, args: argparse.Namespace) -> None:
        # First, create instance-specific copies of all ArgumentSpecs
        for key, spec, spec_type in self.__class__.__iter_arguments():
            # Create a copy of the spec for this instance

            instance_spec = deepcopy(spec)
            self.__instance_specs__[key] = instance_spec

        for key, spec, spec_type in self.__class__.__iter_arguments():
            instance_spec = self.__instance_specs__[key]
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

            # Store value in instance-specific storage
            self.__instance_values__[key] = val
            # Update the instance-specific spec
            instance_spec.value = val
            if spec_type.is_specless_type:
                setattr(self, key, val)

        # Apply default factories after all values are loaded
        for key, spec, spec_type in self.__class__.__iter_arguments():
            instance_spec = self.__instance_specs__[key]
            # Only apply default factory if no value was set from command line
            if key not in self.__instance_values__ or self.__instance_values__[key] is None:
                if instance_spec.default_factory is not None:
                    factory_value = instance_spec.default_factory()
                    self.__instance_values__[key] = factory_value
                    # Update the instance-specific spec
                    instance_spec.value = factory_value
                    if spec_type.is_specless_type:
                        setattr(self, key, factory_value)


ignored_annotations = tuple(tp.get_type_hints(BaseArguments).keys())


def _get_type_hints(obj: type) -> Iterator[Tuple[str, object]]:
    """Get type hints for an object, excluding those in BaseArguments."""
    for k, v in tp.get_type_hints(obj).items():
        if k not in ignored_annotations:
            yield k, v
