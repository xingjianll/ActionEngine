import asyncio
from collections.abc import Generator
from inspect import iscoroutinefunction
from types import NoneType
from typing import Callable, Any, get_type_hints, get_origin, get_args

from action_engine.param import (
    ParamSet,
    StatefulParamSet,
    OutputParam,
    InputParam,
)
from action_engine.param_functions import TagMetaData, DepsMetaData
from action_engine.types import Displayable


class Action[**I, O](Displayable):
    _fn: Callable
    _name: str
    _final: bool
    _description: str
    _input_params: ParamSet[InputParam]
    _output_params: ParamSet[OutputParam]

    def __init__(self, fn: Callable[I, O], final: bool, description: str) -> None:
        self._fn = fn
        self._name = fn.__name__
        self._final = final
        self._description = description

        self._input_params = ParamSet([])
        self._output_params = ParamSet([])

        # Extract return type
        for param1 in self._extract_input_params(fn):
            self._input_params.add(param1)

        for param2 in self._extract_output_params(fn):
            self._output_params.add(param2)

    @property
    def name(self) -> str:
        return self._name

    @property
    def final(self) -> bool:
        return self._final

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_params(self) -> ParamSet[InputParam]:
        return self._input_params

    @property
    def output_params(self) -> ParamSet[OutputParam]:
        return self._output_params

    @staticmethod
    def _extract_input_params(fn: Callable[I, O]) -> Generator[InputParam, None, None]:
        type_hints = get_type_hints(fn, include_extras=True)
        for param_name, param_type in type_hints.items():
            if param_name != "return":
                if hasattr(param_type, "__metadata__"):
                    base_type = param_type.__origin__
                    metadata = param_type.__metadata__[0]
                    assert isinstance(metadata, DepsMetaData)
                    yield InputParam(
                        name=param_name, type_=base_type, deps=metadata.deps
                    )
                else:
                    yield InputParam(name=param_name, type_=param_type, deps=[])

    @staticmethod
    def _extract_output_params(
        fn: Callable[I, O],
    ) -> Generator[OutputParam, None, None]:
        type_hints = get_type_hints(fn, include_extras=True)
        return_type = type_hints.get("return", Any)

        if hasattr(return_type, "__metadata__"):  # Handle one
            base_type = return_type.__origin__
            metadata = return_type.__metadata__
            metadata = metadata[0]
            assert isinstance(metadata, TagMetaData)
            yield OutputParam(
                name=metadata.name, type_=base_type, cascade=metadata.cascade
            )
        elif return_type is NoneType:  # Handle void
            pass
        else:  # Handle multiple
            origin = get_origin(return_type)
            if origin is tuple:
                for sub_return_type in get_args(return_type):
                    if hasattr(sub_return_type, "__metadata__"):
                        base_type = sub_return_type.__origin__
                        metadata = return_type.__metadata__
                        assert isinstance(metadata, TagMetaData)
                        yield OutputParam(
                            name=metadata.name,
                            type_=base_type,
                            cascade=metadata.cascade,
                        )
                    else:
                        raise TypeError(
                            f"Expected an Annotated[...] type but got {sub_return_type}"
                        )
            else:
                raise TypeError(
                    f"Expected an Annotated[...] or tuple[...] but got {return_type}"
                )

    def can_invoke_with(self, params: ParamSet) -> bool:
        """
        Returns True if this Action can be invoked with the given ParamSet,
        False otherwise.
        """
        return self._input_params <= params

    def get_input_param(self, name: str) -> InputParam | None:
        return self._input_params.get(name)

    def __call__(self, *args: I.args, **kwargs: I.kwargs) -> O:
        return self._fn(*args, **kwargs)

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return self._name

    def get_name(self) -> str:
        return self._name

    def get_info(self) -> list[str]:
        ret1 = []
        if not self.input_params:
            ret1.append("None\n")

        for p in self.input_params:
            ret1.append(str(p) + "\n")

        ret2 = []
        if not self._output_params:
            ret2.append("None\n")
        for p2 in self.output_params:
            ret2.append(str(p2) + "\n")
        return ["".join(ret1), "".join(ret2)]

    def invoke(self, state: StatefulParamSet) -> list[tuple[OutputParam, Any]]:
        try:
            params_dict = {p.name: state.get_state(p.name) for p in self._input_params}
        except KeyError as e:
            raise ValueError("Missing required parameter: " + str(e))
        if iscoroutinefunction(self._fn):
            result = asyncio.run(self._fn(**params_dict))
        else:
            result = self._fn(**params_dict)

        rt: list[tuple[OutputParam, Any]] = []
        if not self._output_params:
            return rt

        if isinstance(result, tuple):
            for p, val in zip(self._output_params, result):
                rt.append(
                    (
                        OutputParam(**p.model_dump(exclude={"type_"}), type_=type(val)),
                        val,
                    )
                )
        else:
            p = self._output_params[0]
            rt.append(
                (
                    OutputParam(**p.model_dump(exclude={"type_"}), type_=type(result)),
                    result,
                )
            )

        return rt
