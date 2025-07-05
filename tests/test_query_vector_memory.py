import pytest
from unittest.mock import patch
import sys
import os

# Add the parent directory to the sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from genes import query_vector_memory

@patch('genes.query_memory')
def test_query_memory_success(mock_db_query):
    """Verify the gene correctly calls the database query function."""
    mock_db_query.return_value = ["memory1", "memory2"]
    
    config = {"organism_id": 1, "num_results": 2}
    input_data = {"query": "What happened yesterday?"}
    
    result = query_vector_memory(config, input_data, {})
    
    mock_db_query.assert_called_once_with(1, "What happened yesterday?", n_results=2)
    assert result == {"memories": ["memory1", "memory2"]}
