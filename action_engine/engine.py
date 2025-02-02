from __future__ import annotations
from typing import Callable, Concatenate, Any

from action_engine.action import Action
from action_engine.param import StatefulParamSet, Param, OutputParam
from action_engine.types import Id, Rm


class Engine[BaseState]:
    _params: StatefulParamSet
    actions: dict[str, Action]
    base_state_type: type[BaseState]
    base_action_selector: Callable[[list[Action]], Action]

    def __init__(
        self,
        base_state_type: type[BaseState],
        base_action_selector: Callable[[list[Action]], Action],
    ):
        self._params = StatefulParamSet([])
        self.actions = {}
        self.base_state_type = base_state_type
        self.base_action_selector = base_action_selector

    def run[**P, O](
        self,
        base_state: BaseState,
        entry_point: Action[Concatenate[BaseState, P], O] | None = None,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self._params.set_state(
            Param(name="base", type_=self.base_state_type), base_state
        )

        if entry_point:
            # Set the initial states for positional arguments
            for p, arg in zip(entry_point.input_params, args):
                self._params.set_state(Param(name=p.name, type_=p.type_), arg)

            # Set the initial states for keyword arguments
            for name, val in kwargs.items():
                param = entry_point.get_input_param(name)
                assert param
                self._params.set_state(Param(name=param.name, type_=param.type_), val)

            # Invoke the entry point
            result = entry_point.invoke(self._params)
            for param2, val in result:
                self._update(param2, val)

        while True:
            possible_actions = self._filter_actions()
            action = self.base_action_selector(possible_actions)
            output_params = action.invoke(self._params)
            for param3, val in output_params:
                self._update(param3, val)
            if action.final:
                break

    def _filter_actions(self) -> list[Action]:
        return [
            action
            for action in self.actions.values()
            if action.can_invoke_with(self._params)
        ]

    def _update(self, param: OutputParam, val: Any) -> None:
        """Update the state with the given parameter and value."""
        if isinstance(val, Id):
            pass
        if isinstance(val, Rm):
            self._params.discard(param.name)
            if param.cascade:
                self._cascade(param.name)
        else:
            self._params.set_state(
                Param(name=param.name, type_=param.type_), val
            )
            if param.cascade:
                self._cascade(param.name)

    def _cascade(self, name: str) -> None:
        """Deletes all parameters that depend on the given parameter name recursively."""
        for action in self.actions.values():
            if deps := action.input_params.get(name):
                for dep in deps.deps:
                    self._params.discard(dep)
                    self._cascade(dep)

    def action[**P, O](
        self, terminal: bool = False, description: str = ""
    ) -> Callable[
        [Callable[Concatenate[BaseState, P], O]], Action[Concatenate[BaseState, P], O]
    ]:
        def wrapper(
            fn: Callable[Concatenate[BaseState, P], O],
        ) -> Action[Concatenate[BaseState, P], O]:
            action = Action(fn=fn, final=terminal, description=description)
            self.actions[action.name] = action
            return action

        return wrapper
