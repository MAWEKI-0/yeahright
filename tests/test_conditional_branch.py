import pytest
import sys
import os

# Add the parent directory to the sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from genes import conditional_branch

@pytest.mark.parametrize("truthy_value", [
    "hello",
    123,
    True,
    [1, 2],
    {"key": "value"}
])
def test_conditional_branch_truthy_inputs(truthy_value):
    """Tests that various 'truthy' inputs pass through correctly."""
    input_data = truthy_value
    result = conditional_branch({}, input_data, {})
    assert result == {"condition_met": True, "data": truthy_value}

@pytest.mark.parametrize("falsy_value", [
    "",
    0,
    False,
    [],
    {},
    None
])
def test_conditional_branch_falsy_inputs(falsy_value):
    """Tests that various 'falsy' inputs return the correct structure."""
    input_data = falsy_value
    result = conditional_branch({}, input_data, {})
    assert result == {"condition_met": False}

def test_conditional_branch_missing_input():
    """Tests graceful handling when the input key is missing."""
    input_data = None
    result = conditional_branch({}, input_data, {})
    assert result == {"condition_met": False}
