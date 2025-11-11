from dataclasses import dataclass, field
from inspect import getdoc
from typing import TYPE_CHECKING, Callable, Generic, Optional, Type, TypeVar, Union, cast

from ._typing import sanitize_name, unwrap_callable

if TYPE_CHECKING:
    from .base import BaseArguments

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


def subcommand(
    name: Optional[str] = None,
    help: str = "",
    description: Optional[str] = None,
    argument_class: Optional[Type[S]] = None,
) -> Callable[[Union[Callable[..., Type[S]], Type[S]]], SubcommandSpec[S]]:
    """
    Decorator to automatically create SubcommandSpec from a method.

    This is the recommended way to define subcommands in spargear. The decorator
    automatically handles method-to-factory conversion and extracts metadata
    from the method name and docstring.

    Args:
        name: The name of the subcommand. If not provided, uses the method name.
        help: Brief help text for the subcommand. If not provided, uses the first
              line of the method's docstring.
        description: Detailed description of the subcommand. If not provided,
                    uses the remaining lines of the method's docstring.
        argument_class: The BaseArguments subclass. If provided, the method won't
                       be called and this class will be used directly.

    Returns:
        A SubcommandSpec instance that can be used as a class attribute.

    Examples:
        Basic usage:

        ```python
        class MyApp(BaseArguments):
            @subcommand(help="Initialize a new project")
            def init():
                return InitArguments
        ```

        With custom name and docstring help:

        ```python
        class MyApp(BaseArguments):
            @subcommand(name="db-migrate")
            def database_migrate():
                '''Run database migrations.

                This command applies all pending database migrations
                to bring the database schema up to date.
                '''
                return MigrateArguments
        ```

        With direct argument class (method won't be called):

        ```python
        class MyApp(BaseArguments):
            @subcommand(argument_class=ServeArguments, help="Start server")
            def serve():
                pass  # This method body is ignored
        ```

    Note:
        - No need for @staticmethod - the decorator handles method calling automatically
        - The method should return a BaseArguments subclass
        - Method docstrings are automatically used for help and description
        - Method names are automatically converted to subcommand names
    """

    def decorator(func_or_class: Union[Callable[..., Type[S]], Type[S]]) -> SubcommandSpec[S]:
        if isinstance(func_or_class, type):
            # Handle class objects
            if argument_class is not None:
                t = argument_class
                if isinstance(func_or_class, t):
                    func_or_class = cast(Type[S], func_or_class)
                    return subcommandclass(name=name, help=help, description=description)(func_or_class)
                else:
                    raise ValueError(f"Expected {t.__name__}, but got {func_or_class.__name__}")
            else:
                func_or_class = cast(
                    Type[S], func_or_class
                )  # There's no way to get the type of the class, so we cast to the generic type
                return subcommandclass(name=name, help=help, description=description)(func_or_class)
        else:
            # Handle staticmethod objects
            unwrapped_func = unwrap_callable(func_or_class)

            # Extract name from function name if not provided
            subcommand_name: str = name or sanitize_name(unwrapped_func.__name__)

            # Extract help from docstring if not provided
            func_help: str = help
            func_description: Optional[str] = description
            if not func_help and (doc := getdoc(unwrapped_func)):
                # Use first line of docstring as help
                lines = doc.strip().split("\n")
                func_help = lines[0].strip()
                # Use rest of docstring as description if available and description not provided
                if not func_description and len(lines) > 1:
                    func_description = "\n".join(line.strip() for line in lines[1:]).strip()
                    if not func_description:
                        func_description = None

            # Determine argument_class or argument_class_factory
            if argument_class is not None:
                # Use provided argument_class directly
                return SubcommandSpec(
                    name=subcommand_name,
                    argument_class=argument_class,
                    help=func_help,
                    description=func_description,
                )
            else:
                # Always use the function as a factory
                def argument_class_factory() -> Type[S]:
                    # At class definition time, methods are unbound functions
                    # So we can call them directly without self
                    try:
                        result = unwrapped_func()
                        return result  # pyright: ignore[reportReturnType]
                    except TypeError:
                        # If there's still a TypeError, the function probably has other required parameters
                        raise ValueError(
                            f"Method '{unwrapped_func.__name__}' cannot be used as a factory. Make sure it has no required parameters (including 'self')."
                        )

                return SubcommandSpec(
                    name=subcommand_name,
                    argument_class_factory=argument_class_factory,
                    help=func_help,
                    description=func_description,
                )

    return decorator


def subcommandclass(
    name: Optional[str] = None,
    help: str = "",
    description: Optional[str] = None,
) -> Callable[[Type[S]], SubcommandSpec[S]]:
    """
        Decorator to automatically create SubcommandSpec from a class.

        This decorator allows you to directly decorate an argument class without
        needing a factory method. The class is used directly as the argument_class.

        Args:
            name: The name of the subcommand. If not provided, uses the class name.
            help: Brief help text for the subcommand. If not provided, uses the first
                  line of the class's docstring.
            description: Detailed description of the subcommand. If not provided,
                        uses the remaining lines of the class's docstring.

        Returns:
            A SubcommandSpec instance that can be used as a class attribute.

        Examples:
            Basic usage:
    ```python
            class MyApp(BaseArguments):
                @subcommandclass(help="Initialize a new project")
                class init(BaseArguments):
                    path: str
                    verbose: bool = False
    ```

            With custom name and docstring help:
    ```python
            class MyApp(BaseArguments):
                @subcommandclass(name="db-migrate")
                class database_migrate(BaseArguments):
                    '''Run database migrations.

                    This command applies all pending database migrations
                    to bring the database schema up to date.
                    '''
                    target: Optional[str] = None
    ```

            Accessing the original class:
    ```python
            class MyApp(BaseArguments):
                @subcommandclass()
                class serve(BaseArguments):
                    port: int = 8000

            # The SubcommandSpec preserves the original class
            serve_class = MyApp.serve.argument_class
    ```

        Note:
            - The decorated class should be a BaseArguments subclass
            - Class docstrings are automatically used for help and description
            - Class names are automatically converted to subcommand names
            - The original class is preserved and can be accessed via the SubcommandSpec
    """

    def decorator(cls: Type[S]) -> SubcommandSpec[S]:
        # Extract name from class name if not provided
        subcommand_name: str = name or sanitize_name(cls.__name__)

        # Extract help from docstring if not provided
        cls_help: str = help
        cls_description: Optional[str] = description
        if not cls_help and (doc := getdoc(cls)):
            # Use first line of docstring as help
            lines = doc.strip().split("\n")
            cls_help = lines[0].strip()
            # Use rest of docstring as description if available and description not provided
            if not cls_description and len(lines) > 1:
                cls_description = "\n".join(line.strip() for line in lines[1:]).strip()
                if not cls_description:
                    cls_description = None

        # Create SubcommandSpec with the class directly
        return SubcommandSpec(
            name=subcommand_name,
            argument_class=cls,
            help=cls_help,
            description=cls_description,
        )

    return decorator
