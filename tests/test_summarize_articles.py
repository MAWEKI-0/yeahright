import pytest
from unittest.mock import patch, MagicMock
from genes import summarize_articles

# === A. Test the Happy Path ===
@patch('genes.OpenAI')
def test_summarize_articles_success(mock_openai):
    """Verify the gene successfully calls the OpenAI API and adds a summary."""
    # --- Assemble ---
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="This is a mock summary."))]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    input_data = [{"title": "Test Article", "text": "Some content."}]
    
    # --- Act ---
    result = summarize_articles(config={}, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert len(result) == 1
    assert result[0]["summary"] == "This is a mock summary."
    mock_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_client.chat.completions.create.call_args
    assert "Test Article" in kwargs['messages'][1]['content']

# === C. Test for Statelessness ===
@patch('genes.OpenAI')
def test_summarize_articles_is_stateless(mock_openai):
    """Verify calling the gene twice with the same input yields the same result."""
    # --- Assemble ---
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="A stateless summary."))]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    input_data = [{"title": "Stateless Test", "text": "Content."}]
    
    # --- Act ---
    result1 = summarize_articles(config={}, input_data=input_data, data_context={})
    result2 = summarize_articles(config={}, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert result1 == result2
    assert mock_client.chat.completions.create.call_count == 2

# === D. Test Edge Cases & Graceful Failure ===
def test_summarize_articles_empty_input():
    """Verify the gene handles an empty list."""
    assert summarize_articles(config={}, input_data=[], data_context={}) == []

def test_summarize_articles_none_input():
    """Verify the gene handles None as input."""
    assert summarize_articles(config={}, input_data=None, data_context={}) == []

@patch('genes.OpenAI')
def test_summarize_articles_api_error(mock_openai):
    """Verify the gene handles an API error gracefully."""
    # --- Assemble ---
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")
    mock_openai.return_value = mock_client
    
    input_data = [{"title": "Error Test", "text": "Content."}]
    
    # --- Act ---
    result = summarize_articles(config={}, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert len(result) == 1
    assert "Error summarizing: API Error" in result[0]["summary"]
