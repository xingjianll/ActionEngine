"""Tests for the parameter (param) module."""

from __future__ import annotations
import pytest
from action_engine.param import Param, StatefulParamSet, ParamSet


def test_stateful_param_set_set_and_get() -> None:
    """
    Verify that setting a parameter using StatefulParamSet stores
    the value and that get_state returns the expected value.
    """
    state_set: StatefulParamSet = StatefulParamSet([])
    param_int: Param = Param(name="test_param", type_=int)
    state_set.set_state(param_int, 42)
    assert state_set.get_state("test_param") == 42


def test_stateful_param_set_discard() -> None:
    """
    Verify that discarding a parameter removes it from the internal state.
    """
    state_set: StatefulParamSet = StatefulParamSet([])
    param_str: Param = Param(name="string_param", type_=str)
    state_set.set_state(param_str, "hello")
    assert state_set.get_state("string_param") == "hello"
    state_set.discard("string_param")
    assert state_set.get_state("string_param") is None


def test_stateful_param_set_wrong_type() -> None:
    """
    Verify that setting a value of the wrong type raises an assertion error.
    """
    state_set: StatefulParamSet = StatefulParamSet([])
    param_float: Param = Param(name="float_param", type_=float)
    with pytest.raises(AssertionError):
        # 10 is an int, not a float.
        state_set.set_state(param_float, 10)


def test_param_set_subset() -> None:
    """
    Verify that a ParamSet with fewer parameters is a subset of a larger ParamSet,
    when the types are compatible.
    """
    param_a: Param = Param(name="a", type_=int)
    param_b: Param = Param(name="b", type_=str)
    set1: ParamSet = ParamSet([param_a])
    set2: ParamSet = ParamSet([param_a, param_b])
    assert set1 <= set2
    assert not (set2 <= set1)
