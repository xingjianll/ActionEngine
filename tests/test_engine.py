"""Tests for the Engine class and its action registration/invocation flow."""

from __future__ import annotations
from typing import List, Annotated, cast
import pytest
from pydantic import BaseModel
from action_engine.engine import Engine
from action_engine.action import Action
from action_engine.param import Param, ParamSet, InputParam
from action_engine.param_functions import Tag, Deps


class DummyState(BaseModel):
    """
    A simple base state model used in engine tests.
    """

    counter: int = 0
    finished: bool = False


@pytest.fixture
def dummy_engine() -> Engine[DummyState]:
    """
    Creates an Engine instance with DummyState as the base state.
    The custom action selector chooses the 'finish' action if available;
    otherwise, it selects the first action.
    """

    def action_selector(actions: List[Action]) -> Action:
        for act in actions:
            if act.name == "finish":
                return act
        return actions[0]

    return Engine(DummyState, action_selector)


def test_engine_run(dummy_engine: Engine[DummyState]) -> None:
    """
    Test the engine's run loop by registering two actions:
      - `increment`: increases the state's counter.
      - `finish`: marks the state as finished.
    The action selector is designed to choose the finish action when possible.
    """

    @dummy_engine.action(terminal=False)
    def increment(base: DummyState) -> Annotated[int, Tag("counter", cascade=False)]:
        new_value: int = base.counter + 1
        base.counter = new_value
        return new_value

    @dummy_engine.action(terminal=True)
    def finish(base: DummyState, counter: Annotated[int, Deps([])]) -> None:
        base.finished = True

    state: DummyState = DummyState(counter=0, finished=False)
    dummy_engine.run(state)
    # After run, the finish action should have been executed.
    assert state.finished is True
    # The increment action should have updated the counter.
    assert state.counter == 1


def test_engine_cascade() -> None:
    """
    Test the engine's internal cascade functionality.
    When an output parameter with cascade=True is updated with a removal signal,
    all dependent parameters are removed recursively.
    """
    engine: Engine[DummyState] = Engine(DummyState, lambda acts: acts[0])
    # Manually add a parameter "dependent" to the engine's state.
    engine._params.set_state(Param(name="dependent", type_=int), 100)

    # Create a dummy input parameter "trigger" whose metadata indicates it depends on "dependent".
    dummy_input_param: InputParam = InputParam(
        name="trigger", type_=int, deps=["dependent"]
    )
    dummy_param_set: ParamSet[InputParam] = ParamSet([dummy_input_param])

    # Create a dummy action with these input parameters.
    class DummyAction:
        def __init__(self, inputs: ParamSet[InputParam]) -> None:
            self._input_params = inputs

        @property
        def input_params(self) -> ParamSet[InputParam]:
            return self._input_params

    dummy_action = DummyAction(dummy_param_set)
    # Cast dummy_action to Action since Engine expects actions of type Action.
    engine.actions["dummy"] = cast(Action, dummy_action)

    # Invoke cascade on "trigger" so that parameters dependent on it are removed.
    engine._cascade("trigger")
    # Verify that the "dependent" parameter has been removed.
    assert engine._params.get_state("dependent") is None
