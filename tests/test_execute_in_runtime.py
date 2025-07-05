import pytest
from unittest.mock import patch, MagicMock
from genes import execute_in_runtime
import subprocess
import sys
import os

# Add the parent directory to the sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_execute_runtime_success():
    """Verify the gene successfully runs a simple, safe command."""
    input_data = {"command": "echo 'hello world'"}
    
    result = execute_in_runtime(config={}, input_data=input_data, data_context={})
    
    assert result["return_code"] == 0
    assert result["stdout"] == "hello world"
    assert result["stderr"] == ""
    assert result["command"] == "echo 'hello world'"

def test_execute_runtime_command_failure():
    """Verify the gene captures stderr and a non-zero exit code from a failing command."""
    # This command is designed to fail predictably on both linux and windows
    input_data = {"command": "ls non_existent_directory_12345"}
    
    result = execute_in_runtime(config={}, input_data=input_data, data_context={})
    
    assert result["return_code"] != 0
    assert result["stdout"] == ""
    assert "non_existent_directory_12345" in result["stderr"]

def test_execute_runtime_handles_missing_command_input():
    """Verify graceful failure when the 'command' key is missing."""
    input_data = {"wrong_key": "some_value"}
    
    result = execute_in_runtime(config={}, input_data=input_data, data_context={})
    
    assert result["return_code"] == -1
    assert "Error: 'command' key not provided" in result["stderr"]

@patch('genes.subprocess.run')
def test_execute_runtime_handles_timeout(mock_run):
    """Verify the gene handles a TimeoutExpired exception gracefully."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 10", timeout=5)
    
    input_data = {"command": "sleep 10"}
    
    result = execute_in_runtime(config={"timeout": 5}, input_data=input_data, data_context={})
    
    assert result["return_code"] == -1
    assert "timed out" in result["stderr"]

@patch('genes.subprocess.run')
def test_execute_runtime_handles_file_not_found(mock_run):
    """Verify the gene handles a FileNotFoundError for a non-existent command."""
    mock_run.side_effect = FileNotFoundError()

    input_data = {"command": "nonexistentcommand"}

    result = execute_in_runtime(config={}, input_data=input_data, data_context={})

    assert result["return_code"] == -1
    assert "not found" in result["stderr"]

def test_execute_runtime_with_variable_substitution():
    """Verify the gene correctly substitutes a variable from the data_context."""
    # This command uses a variable {{some_step.output_filename}}
    input_data = {"command": "echo 'test content' > {{some_step.output_filename}}"}
    
    # The data_context contains the value for that variable
    data_context = {
        "some_step": {
            "output_filename": "test_file.txt"
        }
    }
    
    # We use a real subprocess call here to ensure shlex.quote works
    result = execute_in_runtime(config={}, input_data=input_data, data_context=data_context)

    assert result["return_code"] == 0
    # The command in the result should show the SUBSTITUTED value
    assert result["command"] == "echo 'test content' > test_file.txt"
    # Cleanup the created file
    if os.path.exists("test_file.txt"):
        os.remove("test_file.txt")
