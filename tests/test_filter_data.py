import pytest
from genes import filter_data

@pytest.fixture
def sample_data():
    """Provides a sample list of dictionaries for filtering tests."""
    return [
        {"id": 1, "name": "apple", "value": 10},
        {"id": 2, "name": "banana", "value": 20},
        {"id": 3, "name": "orange", "value": 30},
        {"id": 4, "name": "grape", "value": 10},
    ]

# === A. Test the Happy Path ===
def test_filter_data_greater_than(sample_data):
    config = {"field": "value", "condition": "greater_than", "value": 15}
    result = filter_data(config=config, input_data=sample_data, data_context={})
    assert len(result) == 2
    assert result[0]["name"] == "banana"
    assert result[1]["name"] == "orange"

def test_filter_data_less_than(sample_data):
    config = {"field": "value", "condition": "less_than", "value": 15}
    result = filter_data(config=config, input_data=sample_data, data_context={})
    assert len(result) == 2
    assert result[0]["name"] == "apple"
    assert result[1]["name"] == "grape"

def test_filter_data_contains(sample_data):
    config = {"field": "name", "condition": "contains", "value": "an"}
    result = filter_data(config=config, input_data=sample_data, data_context={})
    assert len(result) == 2
    assert result[0]["name"] == "banana"
    assert result[1]["name"] == "orange"

def test_filter_data_not_in(sample_data):
    config = {"field": "name", "condition": "not_in", "value": ["apple", "orange"]}
    result = filter_data(config=config, input_data=sample_data, data_context={})
    assert len(result) == 2
    assert result[0]["name"] == "banana"
    assert result[1]["name"] == "grape"

def test_filter_data_not_in_from_context(sample_data):
    config = {"field": "id", "condition": "not_in", "value_from_context": "seen_ids"}
    context = {"seen_ids": [1, 3, 5]}
    result = filter_data(config=config, input_data=sample_data, data_context=context)
    assert len(result) == 2
    assert result[0]["name"] == "banana"
    assert result[1]["name"] == "grape"

# === C. Test for Statelessness ===
def test_filter_data_is_stateless(sample_data):
    config = {"field": "value", "condition": "greater_than", "value": 15}
    result1 = filter_data(config=config, input_data=sample_data, data_context={})
    result2 = filter_data(config=config, input_data=sample_data, data_context={})
    assert result1 == result2

# === D. Test Edge Cases & Graceful Failure ===
def test_filter_data_empty_input(sample_data):
    assert filter_data(config={"field": "value", "condition": "greater_than", "value": 0}, input_data=[], data_context={}) == []

def test_filter_data_none_input(sample_data):
    assert filter_data(config={"field": "value", "condition": "greater_than", "value": 0}, input_data=None, data_context={}) == []

def test_filter_data_no_matching_items(sample_data):
    config = {"field": "value", "condition": "greater_than", "value": 100}
    assert filter_data(config=config, input_data=sample_data, data_context={}) == []

def test_filter_data_field_missing_in_some_items(sample_data):
    data_with_missing = sample_data + [{"id": 5, "name": "kiwi"}] # 'value' is missing
    config = {"field": "value", "condition": "greater_than", "value": 15}
    result = filter_data(config=config, input_data=data_with_missing, data_context={})
    assert len(result) == 2 # Should gracefully skip the item with the missing field

def test_filter_data_unsupported_condition(sample_data):
    config = {"field": "value", "condition": "equals", "value": 10}
    with pytest.raises(ValueError, match="Condition 'equals' is not supported."):
        filter_data(config=config, input_data=sample_data, data_context={})

def test_filter_data_no_value_in_config(sample_data):
    config = {"field": "value", "condition": "greater_than"} # Missing 'value' and 'value_from_context'
    with pytest.raises(ValueError, match="FilterData config must contain 'value' or 'value_from_context'"):
        filter_data(config=config, input_data=sample_data, data_context={})
