import pytest
from unittest.mock import patch
import sys
import os

# Add the parent directory to the sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from genes import save_to_vector_memory

@patch('genes.save_memory')
def test_save_memory_success(mock_db_save):
    """Verify the gene correctly calls the database function."""
    mock_db_save.return_value = "org1_12345"
    
    config = {"organism_id": 1}
    input_data = {"text": "This is a test memory."}
    
    result = save_to_vector_memory(config, input_data, {})
    
    mock_db_save.assert_called_once_with(1, "This is a test memory.")
    assert result == {"status": "success", "memory_id": "org1_12345"}
