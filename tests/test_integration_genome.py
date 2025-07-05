# tests/test_integration_genome.py
import pytest
import json
from unittest.mock import patch, MagicMock
from engine import run_organism

# Define the path to our test genome
TEST_GENOME_PATH = "tests/test_genomes/genome_fetch_summarize_store.json"

def load_test_genome():
    """Helper function to load the test genome from its file."""
    with open(TEST_GENOME_PATH, 'r') as f:
        return json.load(f)

@pytest.fixture
def mock_gene_map():
    """A pytest fixture to mock the entire GENE_MAP for this test."""
    mock_fetch = MagicMock(name="FetchArticle")
    mock_summarize = MagicMock(name="SummarizeText")
    mock_store = MagicMock(name="StoreResult")

    # Define the return value for each mock to simulate the data flow
    mock_fetch.return_value = {"content": "This is the full article content."}
    mock_summarize.return_value = {"summary": "This is the summary."}
    mock_store.return_value = {"status": "success"}

    with patch('engine.GENE_MAP', {
        "FetchArticle": mock_fetch,
        "SummarizeText": mock_summarize,
        "StoreResult": mock_store
    }) as patched_map:
        yield {
            "fetch": mock_fetch,
            "summarize": mock_summarize,
            "store": mock_store
        }

def test_genome_chain_executes_correctly(mock_gene_map):
    """
    Integration test to verify a full genome chain.
    Asserts that data flows correctly from one gene to the next.
    """
    # 1. ARRANGE
    genome = load_test_genome()
    initial_input = {"url": "http://example.com/article"}
    
    # We must construct the exact dictionaries the engine will pass.
    # The engine adds organism_id and run_id to config, and initial_input to context.
    # For this test, let's assume dummy IDs.
    expected_config_for_fetch = {'organism_id': 1, 'run_id': 1}
    expected_data_context_for_fetch = {'initial_input': initial_input}
    expected_input_for_fetch = initial_input

    expected_config_for_summarize = {'organism_id': 1, 'run_id': 1}
    expected_input_for_summarize = {'content': 'This is the full article content.'}
    expected_data_context_for_summarize = {'initial_input': initial_input, 'fetch_step': {'content': 'This is the full article content.'}}

    expected_config_for_store = {'organism_id': 1, 'run_id': 1}
    expected_input_for_store = {'summary': 'This is the summary.'}
    expected_data_context_for_store = {'initial_input': initial_input, 'fetch_step': {'content': 'This is the full article content.'}, 'summarize_step': {'summary': 'This is the summary.'}}


    # 2. ACT
    log_output, final_status, data_context = run_organism(json.dumps(genome), run_id=1, organism_id=1, initial_input=initial_input)

    # 3. ASSERT
    mock_fetch = mock_gene_map["fetch"]
    mock_summarize = mock_gene_map["summarize"]
    mock_store = mock_gene_map["store"]

    # // CORRECTION: Assert using positional arguments to match the engine's actual call.
    # The engine passes (config, input_data, data_context).
    mock_fetch.assert_called_once_with(expected_config_for_fetch, expected_input_for_fetch, expected_data_context_for_fetch)

    # // CORRECTION: The input for the next gene is the output of the previous. Config and context are passed along.
    mock_summarize.assert_called_once_with(expected_config_for_summarize, expected_input_for_summarize, expected_data_context_for_summarize)
    
    # // CORRECTION: Same logic for the final gene in the chain.
    mock_store.assert_called_once_with(expected_config_for_store, expected_input_for_store, expected_data_context_for_store)

    assert final_status == "success"
