import pytest
from unittest.mock import patch, MagicMock
import json
from genes import read_from_memory

# === A. Test the Happy Path ===
@patch('genes.database.get_db_connection')
def test_read_from_memory_success(mock_get_conn):
    """Verify the gene successfully reads and decodes a value from the mock database."""
    # --- Assemble ---
    mock_conn = MagicMock()
    # Simulate a successful fetch where a row is found
    mock_conn.execute.return_value.fetchone.return_value = (json.dumps({"key": "value"}),)
    mock_get_conn.return_value = mock_conn
    
    config = {"key": "test_key", "organism_id": 1}
    
    # --- Act ---
    result = read_from_memory(config=config, input_data=None, data_context={})
    
    # --- Assert ---
    assert result == {"key": "value"}
    mock_conn.execute.assert_called_once_with(
        'SELECT value FROM organism_state WHERE organism_id = ? AND key = ?',
        (1, 'test_key')
    )

# === C. Test for Statelessness ===
@patch('genes.database.get_db_connection')
def test_read_from_memory_is_stateless(mock_get_conn):
    """Verify calling the gene twice with the same input yields the same result."""
    # --- Assemble ---
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = (json.dumps({"stateless": True}),)
    mock_get_conn.return_value = mock_conn
    
    config = {"key": "stateless_key", "organism_id": 1}
    
    # --- Act ---
    result1 = read_from_memory(config=config, input_data=None, data_context={})
    result2 = read_from_memory(config=config, input_data=None, data_context={})
    
    # --- Assert ---
    assert result1 == result2
    assert mock_conn.execute.call_count == 2

# === D. Test Edge Cases & Graceful Failure ===
@patch('genes.database.get_db_connection')
def test_read_from_memory_key_not_found(mock_get_conn):
    """Verify the gene returns None when the key is not found in the database."""
    # --- Assemble ---
    mock_conn = MagicMock()
    # Simulate a fetch where no row is found
    mock_conn.execute.return_value.fetchone.return_value = None
    mock_get_conn.return_value = mock_conn
    
    config = {"key": "not_found_key", "organism_id": 1}
    
    # --- Act ---
    result = read_from_memory(config=config, input_data=None, data_context={})
    
    # --- Assert ---
    assert result is None
