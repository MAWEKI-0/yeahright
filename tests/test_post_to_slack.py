import pytest
from unittest.mock import patch, MagicMock
import requests
from genes import post_to_slack

# === A. Test the Happy Path ===
@patch('genes.requests.post')
@patch('genes.get_env_variable', return_value='fake_webhook_url')
def test_post_to_slack_success(mock_get_env, mock_post):
    """Verify the gene successfully constructs and sends a Slack message."""
    # --- Assemble ---
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    input_data = [
        {"url": "http://a.com", "title": "Article 1", "sentiment_score": 0.8},
        {"url": "http://b.com", "title": "Article 2"}, # No sentiment score
    ]
    config = {"webhook_url_env": "DUMMY_KEY"}
    
    # --- Act ---
    post_to_slack(config=config, input_data=input_data, data_context={})
    
    # --- Assert ---
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == 'fake_webhook_url'
    
    # Check the structure of the sent JSON
    sent_json = kwargs['json']
    assert "blocks" in sent_json
    assert len(sent_json["blocks"]) == 4 # Header, divider, two articles
    assert "Article 1" in sent_json["blocks"][2]["text"]["text"]
    # The f-string formatting creates a string like '*Sentiment Score:* 0.80'
    assert "*Sentiment Score:* 0.80" in sent_json["blocks"][2]["text"]["text"]
    assert "Article 2" in sent_json["blocks"][3]["text"]["text"]
    assert "Sentiment Score" not in sent_json["blocks"][3]["text"]["text"]

# === C. Test for Statelessness ===
@patch('genes.requests.post')
@patch('genes.get_env_variable', return_value='fake_webhook_url')
def test_post_to_slack_is_stateless(mock_get_env, mock_post):
    """Verify calling the gene twice with the same input yields the same result."""
    input_data = [{"url": "http://s.com", "title": "Stateless"}]
    config = {"webhook_url_env": "DUMMY_KEY"}
    
    post_to_slack(config=config, input_data=input_data, data_context={})
    post_to_slack(config=config, input_data=input_data, data_context={})
    
    assert mock_post.call_count == 2

# === D. Test Edge Cases & Graceful Failure ===
def test_post_to_slack_empty_input():
    """Verify the gene does nothing with an empty list."""
    # This test needs no mocks because the function should exit early.
    post_to_slack(config={}, input_data=[], data_context={})

def test_post_to_slack_none_input():
    """Verify the gene does nothing with None as input."""
    post_to_slack(config={}, input_data=None, data_context={})

@patch('genes.requests.post')
@patch('genes.get_env_variable', return_value='fake_webhook_url')
def test_post_to_slack_http_error(mock_get_env, mock_post):
    """Verify the gene handles HTTP errors gracefully."""
    mock_post.side_effect = requests.exceptions.RequestException("Network Error")
    input_data = [{"url": "http://a.com", "title": "Article 1"}]
    config = {"webhook_url_env": "DUMMY_KEY"}
    
    # The function should catch the exception and print an error, not crash.
    # We can't easily assert the print, but we can ensure it doesn't raise.
    try:
        post_to_slack(config=config, input_data=input_data, data_context={})
    except requests.exceptions.RequestException:
        pytest.fail("The function should have handled the RequestException internally.")
