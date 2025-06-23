from abc import ABC, abstractmethod
from typing import Generic, Protocol, TypeVar, runtime_checkable

from .base import BaseArguments

T = TypeVar("T", covariant=True)
S = TypeVar("S", bound=BaseArguments)


@runtime_checkable
class Runnable(Protocol, Generic[T]):
    def run(self) -> T: ...


class RunnableArguments(BaseArguments, ABC, Runnable[T]):
    @abstractmethod
    def run(self) -> T: ...


class SubcommandArguments(BaseArguments):
    def execute(self) -> None:
        if isinstance(last_subcommand := self.last_subcommand, Runnable):
            last_subcommand.run()
        else:
            # If there's a last_subcommand but it's not runnable, show its help
            # Otherwise, show this class's help
            if last_subcommand is not None:
                last_subcommand.get_parser().print_help()
            else:
                self.get_parser().print_help()
