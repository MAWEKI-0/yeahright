import pytest
from genes import extract_field_list

# === A. Test the Happy Path ===
def test_extract_field_list_happy_path():
    """Verify the gene correctly extracts a list of values from a list of dicts."""
    # --- Assemble ---
    input_data = [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"},
        {"id": 3, "name": "Charlie", "role": "user"},
    ]
    
    # --- Act ---
    # Test extracting 'name'
    name_result = extract_field_list(config={"field": "name"}, input_data=input_data, data_context={})
    # Test extracting 'role'
    role_result = extract_field_list(config={"field": "role"}, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert name_result == ["Alice", "Bob", "Charlie"]
    assert role_result == ["admin", "user", "user"]

# === C. Test for Statelessness ===
def test_extract_field_list_is_stateless():
    """Verify calling the gene twice with the same input yields the same result."""
    # --- Assemble ---
    input_data = [{"id": 1, "value": "A"}, {"id": 2, "value": "B"}]
    config = {"field": "value"}
    
    # --- Act ---
    result1 = extract_field_list(config=config, input_data=input_data, data_context={})
    result2 = extract_field_list(config=config, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert result1 == result2
    assert result1 == ["A", "B"]

# === D. Test Edge Cases & Graceful Failure ===
def test_extract_field_list_empty_input():
    """Verify the gene handles an empty list."""
    assert extract_field_list(config={"field": "any"}, input_data=[], data_context={}) == []

def test_extract_field_list_none_input():
    """Verify the gene handles None as input."""
    assert extract_field_list(config={"field": "any"}, input_data=None, data_context={}) == []

def test_extract_field_list_missing_field():
    """Verify the gene handles dicts where the specified field is missing."""
    # --- Assemble ---
    input_data = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "role": "user"}, # 'name' field is missing
        {"id": 3, "name": "Charlie"},
    ]
    config = {"field": "name"}
    
    # --- Act ---
    result = extract_field_list(config=config, input_data=input_data, data_context={})
    
    # --- Assert ---
    # It should gracefully skip the entry without the field
    assert result == ["Alice", "Charlie"]

def test_extract_field_list_no_field_in_config():
    """Verify the gene raises an error if 'field' is not in the config."""
    with pytest.raises(ValueError, match="ExtractFieldList requires 'field' in config."):
        extract_field_list(config={}, input_data=[{"id": 1}], data_context={})

def test_extract_field_list_non_list_input():
    """Verify the gene handles input that is not a list."""
    assert extract_field_list(config={"field": "any"}, input_data={"not": "a list"}, data_context={}) == []
