import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add the parent directory to the sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine import run_organism

@pytest.fixture
def self_correcting_genome():
    with open("tests/test_genomes/genome_self_correcting.json", 'r') as f:
        return json.dumps(json.load(f))

# This test requires mocking multiple components.
@patch('genes.save_memory')
@patch('genes.query_memory')
@patch('genes.subprocess.run')
def test_organism_can_self_correct(mock_run, mock_query, mock_save, self_correcting_genome):
    # ARRANGE
    # 1. First call to ExecuteInRuntime (attempt_read) fails
    mock_run_fail = MagicMock()
    mock_run_fail.returncode = 1
    mock_run_fail.stdout = ""
    mock_run_fail.stderr = "No such file or directory"
    
    # 2. Second call to ExecuteInRuntime (create_missing_file) succeeds
    mock_run_create = MagicMock()
    mock_run_create.returncode = 0
    mock_run_create.stdout = ""
    mock_run_create.stderr = ""
    
    # 3. Third call to ExecuteInRuntime (retry_read) succeeds
    mock_run_success = MagicMock()
    mock_run_success.returncode = 0
    mock_run_success.stdout = "content"
    mock_run_success.stderr = ""
    
    # Set the side_effect to return these mocks in order
    mock_run.side_effect = [mock_run_fail, mock_run_create, mock_run_success]
    
    initial_input = {"command": "cat /tmp/missing_file.txt"}
    
    # ACT
    log_output, final_status, data_context = run_organism(self_correcting_genome, 1, 1, initial_input)

    # ASSERT
    # Assert that the error was saved to memory
    mock_save.assert_called_once_with(1, "No such file or directory")
    
    # Assert the final output is the content of the file from the successful retry
    assert final_status == "success"
    assert data_context['retry_read']['stdout'] == 'content'
    
    # Assert subprocess.run was called three times with the correct commands
    assert mock_run.call_count == 3
    assert mock_run.call_args_list[0].args[0] == ['cat', '/tmp/missing_file.txt']
    assert mock_run.call_args_list[1].args[0] == ['echo', 'content', '>', '/tmp/missing_file.txt']
    assert mock_run.call_args_list[2].args[0] == ['cat', '/tmp/missing_file.txt']
