import pytest
from unittest.mock import MagicMock, patch, ANY
import json
import textwrap
import genes

@pytest.fixture
def mock_openai_client(mocker):
    """Mock the OpenAI client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"genes": []}'))]
    mock_client.chat.completions.create.return_value = mock_response
    mocker.patch('genesis.OpenAI', return_value=mock_client)
    return mock_client

@pytest.fixture
def mock_gene_docstrings_with_manifest(mocker):
    """Mocks the __doc__ attribute of gene functions."""
    mock_filter_data_doc = textwrap.dedent("""
        description: Filters a list based on a field.
        manifest:
          inputs:
            - name: input_data
              type: list_of_dicts
            - name: config.field
              type: string
          outputs:
            - type: list_of_dicts
    """)
    mock_write_to_memory_doc = textwrap.dedent("""
        description: Writes a value to the organism's persistent memory.
        manifest:
          inputs:
            - name: input_data
              type: any
            - name: config.key
              type: string
          outputs:
            - type: dict
    """)
    mocker.patch.object(genes.filter_data, '__doc__', mock_filter_data_doc)
    mocker.patch.object(genes.write_to_memory, '__doc__', mock_write_to_memory_doc)

    # Add the mock docstring for ExtractFieldList
    mock_extract_field_list_doc = textwrap.dedent("""
        description: Extracts values of a specified field from a list of dictionaries, returning a flat list of these values.
        manifest:
          inputs:
            - name: input_data
              type: list_of_dicts
            - name: config.field
              type: string
          outputs:
            - type: list
        """)
    mocker.patch.object(genes.extract_field_list, '__doc__', mock_extract_field_list_doc)

    mock_summarize_articles_doc = textwrap.dedent("""
        description: Summarizes a list of articles using an external LLM. Each item in the input list should have 'title' and 'text' fields. A 'summary' field will be added to each item.
        manifest:
          inputs:
            - name: input_data
              type: list_of_dicts
          outputs:
            - type: list_of_dicts
        """)
    mocker.patch.object(genes.summarize_articles, '__doc__', mock_summarize_articles_doc)

    mock_fetch_news_api_doc = textwrap.dedent("""
        description: Fetches news headlines and articles from a general news API (NewsAPI.org). Requires a 'query' (e.g., 'technology', 'economic') and an 'apiKey_env' (environment variable name for the API key). Adds 'id', 'title', 'text', 'url' fields to each article.
        manifest:
          inputs:
            # No direct input_data is used, only config for parameters
          outputs:
            - type: list_of_dicts
        """)
    mocker.patch.object(genes.fetch_news_api, '__doc__', mock_fetch_news_api_doc)

def test_parse_gene_docstring_valid_manifest():
    """Test parsing a docstring with a valid manifest."""
    docstring_content = textwrap.dedent("""
        description: This is an example gene.
        manifest:
          inputs:
            - name: input_data
              type: list
            - name: config.param
              type: string
          outputs:
            - type: boolean
    """)
    mock_func = MagicMock()
    mock_func.__doc__ = docstring_content
    from genesis import _parse_gene_docstring
    description, manifest = _parse_gene_docstring(mock_func)
    assert description == "This is an example gene."
    assert manifest['inputs'][0]['name'] == 'input_data'
    assert manifest['outputs'][0]['type'] == 'boolean'

def test_parse_gene_docstring_no_manifest():
    """Test parsing a docstring without a manifest."""
    docstring_content = "description: A gene with no manifest."
    mock_func = MagicMock()
    mock_func.__doc__ = docstring_content
    from genesis import _parse_gene_docstring
    description, manifest = _parse_gene_docstring(mock_func)
    assert description == "A gene with no manifest."
    assert manifest is None

def test_parse_gene_docstring_malformed_manifest():
    """Test parsing a docstring with a malformed manifest."""
    docstring_content = textwrap.dedent("""
        description: This gene has a bad manifest.
        manifest:
          - name: input_data
          type: list
        - not_a_valid_yaml_line:
    """)
    mock_func = MagicMock()
    mock_func.__doc__ = docstring_content
    mock_func.__name__ = "MalformedGene"
    from genesis import _parse_gene_docstring
    with patch('builtins.print') as mock_print:
        description, manifest = _parse_gene_docstring(mock_func)
        assert mock_print.called
        # Check that the print call contains the expected warning text
        call_args, _ = mock_print.call_args
        assert "Warning: Could not parse manifest for gene MalformedGene" in call_args[0]
    assert description == "This gene has a bad manifest."
    assert manifest is None

def test_generate_genome_from_prompt_includes_manifest(mock_openai_client, mock_gene_docstrings_with_manifest):
    """Test that the system prompt includes manifest details."""
    user_prompt = "Generate something complex."
    from genesis import generate_genome_from_prompt
    generate_genome_from_prompt(user_prompt)
    mock_openai_client.chat.completions.create.assert_called_once()
    messages = mock_openai_client.chat.completions.create.call_args.kwargs['messages']
    system_prompt_content = messages[0]['content']
    assert "FilterData" in system_prompt_content
    assert "config.field" in system_prompt_content
    assert "WriteToMemory" in system_prompt_content
    assert "config.key" in system_prompt_content

    # Add assertions for ExtractFieldList's manifest
    assert "ExtractFieldList" in system_prompt_content
    assert "- name: input_data" in system_prompt_content
    assert "type: list_of_dicts" in system_prompt_content
    assert "- name: config.field" in system_prompt_content
    assert "type: list" in system_prompt_content # For outputs

    # Add assertions for SummarizeArticles's manifest
    assert "SummarizeArticles" in system_prompt_content
    assert "- name: input_data" in system_prompt_content
    assert "type: list_of_dicts" in system_prompt_content # For inputs
    assert "outputs:" in system_prompt_content
    assert "type: list_of_dicts" in system_prompt_content # For outputs

    # Add assertions for FetchNewsAPI's manifest
    assert "FetchNewsAPI" in system_prompt_content
    assert "outputs:" in system_prompt_content
    assert "type: list_of_dicts" in system_prompt_content # For outputs
