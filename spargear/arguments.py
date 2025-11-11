from abc import ABC, abstractmethod
from typing import Generic, Protocol, TypeVar, runtime_checkable

from .base import BaseArguments

T = TypeVar("T", covariant=True)


@runtime_checkable
class Runnable(Protocol, Generic[T]):
    def run(self) -> T: ...


class RunnableArguments(BaseArguments, ABC, Runnable[T]):
    @abstractmethod
    def run(self) -> T: ...


class SubcommandArguments(BaseArguments):
    def execute(self) -> None:
        if (subcommand := self.ok(RunnableArguments[object])) is not None:
            subcommand.run()
        else:
            self.get_parser().print_help()
