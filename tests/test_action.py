"""Tests for the Action class."""

from __future__ import annotations
from typing import Annotated, Any, List
from action_engine.action import Action
from action_engine.param import Param, StatefulParamSet
from action_engine.param_functions import Tag, Deps


def dummy_action_function(
    base: int, increment: Annotated[int, Deps([])]
) -> Annotated[int, Tag("result", cascade=False)]:
    """
    A dummy action function that returns the sum of its inputs.
    The Annotated types allow metadata extraction via Tag and Deps.
    """
    return base + increment


def test_action_extraction_and_invocation() -> None:
    """
    Test that:
      - The Action class correctly extracts input and output parameters
      - The can_invoke_with method works as expected
      - Invoking the action returns the correct output
    """
    action: Action = Action(
        dummy_action_function, final=False, description="dummy action"
    )

    # Check that both 'base' and 'increment' are extracted as input parameters.
    input_params: List[Any] = list(action.input_params)
    input_param_names = {p.name for p in input_params}
    assert "base" in input_param_names
    assert "increment" in input_param_names

    # Check that the output parameter was extracted correctly.
    output_params: List[Any] = list(
        action._output_params
    )  # Access protected member for testing.
    assert len(output_params) == 1
    output_param = output_params[0]
    assert output_param.name == "result"

    # Prepare a StatefulParamSet with required parameters.
    param_set: StatefulParamSet = StatefulParamSet([])
    param_base: Param = Param(name="base", type_=int)
    param_increment: Param = Param(name="increment", type_=int)
    param_set.set_state(param_base, 10)
    param_set.set_state(param_increment, 5)
    assert action.can_invoke_with(param_set)

    # Invoke the action and verify the output.
    output = action.invoke(param_set)
    # We expect a single output tuple ("result", 15).
    assert len(output) == 1
    out_param, value = output[0]
    assert out_param.name == "result"
    assert value == 15
