import pytest
import json
from unittest.mock import MagicMock, patch
from engine import run_organism

@pytest.fixture
def mock_stdout(mocker):
    """Fixture to mock stdout."""
    return mocker.patch('sys.stdout')

@pytest.fixture
def mock_genes_map(mocker):
    """Fixture to mock the GENE_MAP within the engine."""
    mock_map = {
        "TestGene": MagicMock(return_value={"status": "ok"}),
        "InputGene": MagicMock(return_value={"processed_data": "processed"}),
        "OutputGene": MagicMock(),
        "FailingGene": MagicMock(side_effect=Exception("Gene failed!")),
        "SuccessGene": MagicMock(),
        "ExtractFieldList": MagicMock(return_value=["id1", "id2"]),
        "FetchNewsAPI": MagicMock(return_value=[{"id": "n1", "title": "News1", "text": "Content1", "url": "http://news1.com"}]),
    }
    mocker.patch('engine.GENE_MAP', mock_map)
    return mock_map

def test_simple_successful_run(mock_genes_map):
    """Tests a basic successful run with a single gene."""
    genome_json = '''
    {
        "genes": [
            {
                "id": "gene1",
                "type": "TestGene"
            }
        ]
    }
    '''
    log, status, data_context = run_organism(genome_json, run_id=1, organism_id=1, initial_input=None)
    assert status == "success"
    assert "[Executing Gene] ID: gene1, Type: TestGene" in log
    assert "Organism Run Finished with status: success" in log
    mock_genes_map["TestGene"].assert_called_once()

def test_data_flow_between_genes(mock_genes_map):
    """Tests that data correctly flows from one gene to another via data_context."""
    mock_genes_map['InputGene'].reset_mock()
    mock_genes_map['OutputGene'].reset_mock()
    genome_json = '''
    {
        "genes": [
            {
                "id": "input_producer",
                "type": "InputGene"
            },
            {
                "id": "output_consumer",
                "type": "OutputGene",
                "input_from": "input_producer"
            }
        ]
    }
    '''
    log, status, data_context = run_organism(genome_json, run_id=2, organism_id=1, initial_input=None)
    assert status == "success"
    args, kwargs = mock_genes_map['OutputGene'].call_args
    config, input_data, data_context_arg = args
    assert input_data == {"processed_data": "processed"}

def test_run_fails_on_unknown_gene(mock_genes_map):
    """Tests that the run fails gracefully if a gene type is not in GENE_MAP."""
    genome_json = '{"genes": [{"id": "gene1", "type": "UnknownGene"}]}'
    log, status, data_context = run_organism(genome_json, run_id=3, organism_id=1, initial_input=None)
    assert status == "failed"
    assert "Gene type 'UnknownGene' not found" in log

def test_run_fails_on_gene_exception(mock_genes_map):
    """Tests that the run fails gracefully when a gene raises an exception."""
    mock_genes_map['FailingGene'].reset_mock()
    genome_json = '{"genes": [{"id": "gene1", "type": "FailingGene"}]}'
    log, status, data_context = run_organism(genome_json, run_id=4, organism_id=1, initial_input=None)
    assert status == "failed"
    assert "**ERROR** during execution of gene 'gene1': Gene failed!" in log
    mock_genes_map['FailingGene'].assert_called_once()

def test_output_as_functionality(mock_genes_map):
    """Tests that the 'output_as' key correctly renames the output in data_context."""
    mock_genes_map['InputGene'].reset_mock()
    mock_genes_map['OutputGene'].reset_mock()
    genome_json = '''
    {
        "genes": [
            {
                "id": "producer",
                "type": "InputGene",
                "output_as": "custom_output_name"
            },
            {
                "id": "consumer",
                "type": "OutputGene",
                "input_from": "custom_output_name"
            }
        ]
    }
    '''
    log, status, data_context = run_organism(genome_json, run_id=5, organism_id=1, initial_input=None)
    assert status == "success"
    assert "Storing result in 'custom_output_name' in data_context" in log
    args, kwargs = mock_genes_map['OutputGene'].call_args
    config, input_data, data_context_arg = args
    assert input_data == {"processed_data": "processed"}
    assert "custom_output_name" in data_context

def test_run_organism_with_extract_field_list_gene(mock_genes_map, mock_stdout):
    """Test a genome involving the new ExtractFieldList gene."""
    genome_json = json.dumps({
        "id": "test_org_extract",
        "genes": [
            {
                "id": "mock_fetch",
                "type": "SuccessGene",
                "output_as": "fetched_data"
            },
            {
                "id": "extract_ids",
                "type": "ExtractFieldList",
                "input_from": "fetched_data",
                "config": {"field": "id"},
                "output_as": "extracted_ids"
            }
        ]
    })
    
    mock_genes_map["SuccessGene"].return_value = [{"id": "item1", "name": "A"}, {"id": "item2", "name": "B"}]
    
    log_output, status, data_context = run_organism(genome_json, 1, 108, initial_input=None)
    
    assert status == "success"
    
    # Get the call arguments and inspect them manually to avoid mutable dictionary issues
    args, kwargs = mock_genes_map["ExtractFieldList"].call_args
    config, input_data, data_context_arg = args
    
    assert config == {'field': 'id', 'organism_id': 108, 'run_id': 1}
    assert input_data == [{"id": "item1", "name": "A"}, {"id": "item2", "name": "B"}]
    assert "<- Output: Storing result in 'extracted_ids' in data_context." in log_output
