from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .base_arguments import BaseArguments

T = TypeVar("T", covariant=True)
S = TypeVar("S", bound=BaseArguments)


class RunnableArguments(BaseArguments, ABC, Generic[T]):
    @abstractmethod
    def run(self) -> T: ...
