import pytest
from unittest.mock import patch, MagicMock
import json
from genes import write_to_memory

# === A. Test the Happy Path ===
@patch('genes.database.get_db_connection')
def test_write_to_memory_success(mock_get_conn):
    """Verify the gene successfully executes a database REPLACE command."""
    # --- Assemble ---
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    
    config = {"key": "test_key", "organism_id": 1}
    input_data = {"some_data": "some_value"}
    
    # --- Act ---
    result = write_to_memory(config=config, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert result == {"status": "success", "key": "test_key"}
    mock_conn.execute.assert_called_once_with(
        'REPLACE INTO organism_state (organism_id, key, value) VALUES (?, ?, ?)',
        (1, 'test_key', json.dumps(input_data))
    )
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()

# === C. Test for Statelessness ===
@patch('genes.database.get_db_connection')
def test_write_to_memory_is_stateless(mock_get_conn):
    """Verify calling the gene twice with the same input yields the same result."""
    # --- Assemble ---
    mock_conn = MagicMock()
    mock_get_conn.return_value = mock_conn
    
    config = {"key": "stateless_key", "organism_id": 2}
    input_data = {"stateless": True}
    
    # --- Act ---
    result1 = write_to_memory(config=config, input_data=input_data, data_context={})
    result2 = write_to_memory(config=config, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert result1 == result2
    assert mock_conn.execute.call_count == 2
