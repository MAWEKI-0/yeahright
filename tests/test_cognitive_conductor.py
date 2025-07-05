import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add the parent directory to the sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from genes import cognitive_conductor

@patch('engine.run_organism')
@patch('genesis.generate_genome_from_prompt')
def test_cognitive_conductor_success(mock_generate_genome, mock_run_organism):
    """Verify the gene successfully generates and executes a sub-genome."""
    # ARRANGE
    mock_generate_genome.return_value = '{"genes": [{"id": "test_gene", "type": "TestGene"}]}'
    mock_run_organism.return_value = ("log output", "success", {"test_gene": "sub-task complete"})

    config = {"organism_id": 1, "run_id": 1}
    input_data = {
        "task_prompt": "Solve this sub-task.",
        "initial_input_for_sub_task": {"data": "input"}
    }

    # ACT
    result = cognitive_conductor(config, input_data, {})

    # ASSERT
    mock_generate_genome.assert_called_once_with("Solve this sub-task.")
    mock_run_organism.assert_called_once()
    assert result == {"test_gene": "sub-task complete"}

@patch('genesis.generate_genome_from_prompt')
def test_cognitive_conductor_genesis_failure(mock_generate_genome):
    """Verify the gene handles errors during sub-genome generation."""
    # ARRANGE
    mock_generate_genome.side_effect = Exception("Genesis failed")

    config = {"organism_id": 1, "run_id": 1}
    input_data = {"task_prompt": "This will fail."}

    # ACT
    result = cognitive_conductor(config, input_data, {})

    # ASSERT
    assert "error" in result
    assert "CognitiveConductor failed" in result["error"]
    assert "Genesis failed" in result["reason"]

@patch('engine.run_organism')
@patch('genesis.generate_genome_from_prompt')
def test_cognitive_conductor_engine_failure(mock_generate_genome, mock_run_organism):
    """Verify the gene handles errors during sub-genome execution."""
    # ARRANGE
    mock_generate_genome.return_value = '{"genes": []}'
    mock_run_organism.side_effect = Exception("Engine failed")

    config = {"organism_id": 1, "run_id": 1}
    input_data = {"task_prompt": "This will also fail."}

    # ACT
    result = cognitive_conductor(config, input_data, {})

    # ASSERT
    assert "error" in result
    assert "CognitiveConductor failed" in result["error"]
    assert "Engine failed" in result["reason"]
