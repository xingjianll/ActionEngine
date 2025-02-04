from __future__ import annotations

from collections.abc import Iterator
from types import UnionType
from typing import Any, override, get_args

from pydantic import BaseModel, ConfigDict


class Param(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    type_: type | UnionType

    def __str__(self) -> str:
        if isinstance(self.type_, type):
            return f"{self.name}: {self.type_.__name__}"
        else:
            return (
                f"{self.name}: {"｜".join([x.__name__ for x in get_args(self.type_)])}"
            )


class InputParam(Param):
    deps: list[str]
    ...


class OutputParam(Param):
    cascade: bool


class ParamSet[T: Param]:
    _params: dict[str, T]

    @property
    def params(self):
        return self._params

    def __init__(self, params: list[T]) -> None:
        self._params = {}
        for i, param in enumerate(params):
            self._params[param.name] = param

    def __contains__(self, name: str) -> bool:
        """v is in N if for all f such that f(v), f(N)"""
        return name in self._params

    def __le__(self, other: ParamSet) -> bool:
        """N <= E if for all function f that take Param set N as input, f also takes E as input."""
        if not self._params.keys() <= other.params.keys():
            return False
        return all(
            issubclass(other.params[name].type_, self.params[name].type_)
            for name in self._params
        )

    def __iter__(self) -> Iterator[T]:
        """Iterate over the set elements."""
        return iter([p for name, p in self._params.items()])

    def __len__(self) -> int:
        """Return the size of the set."""
        return len(self._params)

    def __getitem__(self, index: int) -> T:
        """
        Retrieve the Param at the given index, using the insertion order.
        """
        items = list(self._params.items())
        name, p = items[index]
        return p

    def get(self, name: str) -> T | None:
        """Return the Param object with the given name."""
        return self._params.get(name)

    def add(self, param: T) -> None:
        """Add a parameter to the set."""
        self._params[param.name] = param

    def discard(self, name: str) -> None:
        """Remove an item from the set, if it exists."""
        if name in self:
            del self._params[name]

    def __repr__(self) -> str:
        """Return a string representation of the set."""
        return f"CustomSet({list(self._params)})"


class StatefulParamSet(ParamSet):
    _state: dict[str, Any]

    def __init__(self, params: list[Param]) -> None:
        super().__init__(params)
        self._state = {}

    def set_state(self, param: Param, value: Any) -> None:
        if value is None:
            self.discard(param.name)
            return
        assert isinstance(value, param.type_)
        self.add(param)
        self._state[param.name] = value

    def get_state(self, param: str) -> Any:
        return self._state.get(param)

    @override
    def discard(self, name: str) -> None:
        if name in self:
            super().discard(name)
            del self._state[name]
