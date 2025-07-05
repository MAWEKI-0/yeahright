import pytest
from genes import merge_data

@pytest.fixture
def sample_context():
    """Provides a sample data context for merging tests."""
    return {
        "source1": [
            {"id": 1, "name": "apple"},
            {"id": 2, "name": "banana"},
        ],
        "source2": [
            {"id": 3, "name": "orange"},
            {"id": 1, "name": "apple"}, # Duplicate
        ],
        "source3": [
            {"id": 4, "name": "grape"},
        ],
        "empty_source": [],
    }

# === A. Test the Happy Path ===
def test_merge_data_happy_path(sample_context):
    """Verify the gene correctly merges and deduplicates lists from context."""
    config = {"source_keys": ["source1", "source2", "source3"], "deduplicate_by_field": "id"}
    result = merge_data(config=config, input_data=None, data_context=sample_context)
    
    assert len(result) == 4
    result_ids = {item["id"] for item in result}
    assert result_ids == {1, 2, 3, 4}

# === C. Test for Statelessness ===
def test_merge_data_is_stateless(sample_context):
    config = {"source_keys": ["source1", "source2"], "deduplicate_by_field": "id"}
    result1 = merge_data(config=config, input_data=None, data_context=sample_context)
    result2 = merge_data(config=config, input_data=None, data_context=sample_context)
    assert result1 == result2

# === D. Test Edge Cases & Graceful Failure ===
def test_merge_data_empty_sources(sample_context):
    config = {"source_keys": ["empty_source"], "deduplicate_by_field": "id"}
    assert merge_data(config=config, input_data=None, data_context=sample_context) == []

def test_merge_data_no_sources_in_config():
    assert merge_data(config={"deduplicate_by_field": "id"}, input_data=None, data_context={}) == []

def test_merge_data_key_not_in_context(sample_context):
    config = {"source_keys": ["source1", "non_existent_key"], "deduplicate_by_field": "id"}
    result = merge_data(config=config, input_data=None, data_context=sample_context)
    assert len(result) == 2 # Should gracefully ignore the missing key

def test_merge_data_no_dedup_field_in_config(sample_context):
    config = {"source_keys": ["source1"]}
    with pytest.raises(ValueError, match="MergeData config requires 'deduplicate_by_field'."):
        merge_data(config=config, input_data=None, data_context=sample_context)

def test_merge_data_mixed_content(sample_context):
    """Verify it handles sources that are not lists or items that are not dicts."""
    bad_context = {
        "source1": [{"id": 1}],
        "source2": "not_a_list",
        "source3": [1, 2, 3], # Items are not dicts
    }
    config = {"source_keys": ["source1", "source2", "source3"], "deduplicate_by_field": "id"}
    result = merge_data(config=config, input_data=None, data_context=bad_context)
    assert len(result) == 1
    assert result[0]["id"] == 1
