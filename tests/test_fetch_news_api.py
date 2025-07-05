import pytest
from unittest.mock import patch, MagicMock
import requests
from genes import fetch_news_api

# === A. Test the Happy Path ===
@patch('genes.requests.get')
@patch('genes.get_env_variable', return_value='fake_api_key')
def test_fetch_news_api_success(mock_get_env, mock_get):
    """Verify the gene successfully fetches and formats articles."""
    # --- Assemble ---
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "articles": [
            {"title": "Article 1", "description": "Desc 1", "url": "http://a.com"},
            {"title": "Article 2", "content": "Content 2", "url": "http://b.com"},
        ]
    }
    mock_get.return_value = mock_response
    
    config = {"query": "testing", "apiKey_env": "DUMMY_KEY"}
    
    # --- Act ---
    result = fetch_news_api(config=config, input_data=None, data_context={})
    
    # --- Assert ---
    assert len(result) == 2
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert 'params' in kwargs
    assert kwargs['params']['q'] == 'testing'
    assert kwargs['params']['apiKey'] == 'fake_api_key'
    
    assert result[0]['title'] == "Article 1"
    assert result[0]['text'] == "Desc 1"
    assert result[0]['id'] == "http://a.com"

# === C. Test for Statelessness ===
@patch('genes.requests.get')
@patch('genes.get_env_variable', return_value='fake_api_key')
def test_fetch_news_api_is_stateless(mock_get_env, mock_get):
    """Verify calling the gene twice with the same input yields the same result."""
    # --- Assemble ---
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"articles": [{"title": "Stateless", "url": "http://s.com"}]}
    mock_get.return_value = mock_response
    
    config = {"query": "stateless"}
    
    # --- Act ---
    result1 = fetch_news_api(config=config, input_data=None, data_context={})
    result2 = fetch_news_api(config=config, input_data=None, data_context={})
    
    # --- Assert ---
    assert result1 == result2
    assert mock_get.call_count == 2

# === D. Test Edge Cases & Graceful Failure ===
@patch('genes.requests.get')
@patch('genes.get_env_variable', return_value='fake_api_key')
def test_fetch_news_api_http_error(mock_get_env, mock_get):
    """Verify the gene raises an exception on HTTP error."""
    # --- Assemble ---
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
    mock_get.return_value = mock_response
    
    config = {"query": "failing"}
    
    # --- Act & Assert ---
    with pytest.raises(Exception, match="Failed to fetch news from API"):
        fetch_news_api(config=config, input_data=None, data_context={})

@patch('genes.get_env_variable', side_effect=Exception("API Key not found"))
def test_fetch_news_api_missing_key(mock_get_env):
    """Verify the gene raises an exception if the API key is not found."""
    config = {"query": "no_key"}
    with pytest.raises(Exception, match="API Key not found"):
        fetch_news_api(config=config, input_data=None, data_context={})

@patch('genes.requests.get')
@patch('genes.get_env_variable', return_value='fake_api_key')
def test_fetch_news_api_empty_response(mock_get_env, mock_get):
    """Verify the gene handles an empty list of articles from the API."""
    # --- Assemble ---
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"articles": []}
    mock_get.return_value = mock_response
    
    config = {"query": "empty"}
    
    # --- Act ---
    result = fetch_news_api(config=config, input_data=None, data_context={})
    
    # --- Assert ---
    assert result == []
