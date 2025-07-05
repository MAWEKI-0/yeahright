import pytest
from unittest.mock import MagicMock, patch
import json

# Import the gene functions to be tested
from genes import filter_data, write_to_memory, read_from_memory, merge_data, extract_field_list, summarize_articles, fetch_news_api
import requests

# Sample data for testing
SAMPLE_POSTS = [
    {'id': 'a', 'score': 10, 'text': 'apple banana'},
    {'id': 'b', 'score': -5, 'text': 'orange grape'},
    {'id': 'c', 'score': 20, 'text': 'apple pear'},
]

def test_filter_data_greater_than():
    """Tests the 'greater_than' condition in FilterData."""
    config = {'field': 'score', 'condition': 'greater_than', 'value': 15}
    result = filter_data(config, SAMPLE_POSTS, {})
    assert len(result) == 1
    assert result[0]['id'] == 'c'

def test_filter_data_less_than():
    """Tests the 'less_than' condition in FilterData."""
    config = {'field': 'score', 'condition': 'less_than', 'value': 0}
    result = filter_data(config, SAMPLE_POSTS, {})
    assert len(result) == 1
    assert result[0]['id'] == 'b'

def test_filter_data_contains():
    """Tests the 'contains' condition in FilterData."""
    config = {'field': 'text', 'condition': 'contains', 'value': 'apple'}
    result = filter_data(config, SAMPLE_POSTS, {})
    assert len(result) == 2
    assert result[0]['id'] == 'a'
    assert result[1]['id'] == 'c'

def test_filter_data_not_in():
    """Tests the 'not_in' condition in FilterData."""
    seen_items = [{'id': 'a'}, {'id': 'c'}]
    config = {'field': 'id', 'condition': 'not_in', 'value_from_context': 'seen'}
    data_context = {'seen': seen_items}
    result = filter_data(config, SAMPLE_POSTS, data_context)
    assert len(result) == 1
    assert result[0]['id'] == 'b'


def test_merge_data():
    """Tests that MergeData correctly combines and deduplicates lists."""
    data_context = {
        'list1': [{'id': 'a', 'data': 'foo'}, {'id': 'b', 'data': 'bar'}],
        'list2': [{'id': 'c', 'data': 'baz'}, {'id': 'a', 'data': 'qux'}] # 'a' is a duplicate
    }
    config = {'source_keys': ['list1', 'list2'], 'deduplicate_by_field': 'id'}
    
    result = merge_data(config, None, data_context)
    
    assert len(result) == 3
    # Check that the first 'a' was kept
    assert {'id': 'a', 'data': 'foo'} in result
    assert {'id': 'b', 'data': 'bar'} in result
    assert {'id': 'c', 'data': 'baz'} in result
    # Check that the duplicate 'a' was not included
    assert {'id': 'a', 'data': 'qux'} not in result

def test_extract_field_list_basic():
    """Test ExtractFieldList extracts a simple field correctly."""
    input_data = [
        {"id": "post1", "title": "Title A"},
        {"id": "post2", "title": "Title B"},
        {"id": "post3", "title": "Title C"}
    ]
    config = {"field": "id"}
    result = extract_field_list(config, input_data)
    assert result == ["post1", "post2", "post3"]

def test_extract_field_list_missing_field_in_some_items():
    """Test ExtractFieldList handles items missing the specified field."""
    input_data = [
        {"id": "post1", "title": "Title A"},
        {"title": "Title B_no_id"}, # Missing 'id'
        {"id": "post3", "title": "Title C"}
    ]
    config = {"field": "id"}
    result = extract_field_list(config, input_data)
    assert result == ["post1", "post3"] # Should skip the item without 'id'

def test_extract_field_list_empty_input():
    """Test ExtractFieldList with an empty input list."""
    input_data = []
    config = {"field": "id"}
    result = extract_field_list(config, input_data)
    assert result == []

def test_extract_field_list_non_list_input():
    """Test ExtractFieldList with non-list input (should return empty and print warning)."""
    input_data = {"key": "value"} # Not a list
    config = {"field": "id"}
    
    with patch('builtins.print') as mock_print:
        result = extract_field_list(config, input_data)
        mock_print.assert_called_with(
            "Warning: Input to ExtractFieldList is not a list. Returning empty list."
        )
    assert result == []

def test_extract_field_list_missing_field_in_config():
    """Test ExtractFieldList raises ValueError if 'field' is missing from config."""
    input_data = [{"id": "post1"}]
    config = {} # Missing 'field'
    with pytest.raises(ValueError, match="ExtractFieldList requires 'field' in config."):
        extract_field_list(config, input_data)

def test_extract_field_list_mixed_field_types():
    """Test ExtractFieldList extracts values of mixed types."""
    input_data = [
        {"data": "string_val"},
        {"data": 123},
        {"data": True}
    ]
    config = {"field": "data"}
    result = extract_field_list(config, input_data)
    assert result == ["string_val", 123, True]

@pytest.fixture
def mock_env_vars(mocker):
    """Mocks environment variables for testing."""
    mocker.patch.dict('os.environ', {
        "REDDIT_CLIENT_ID": "mock_client_id",
        "REDDIT_CLIENT_SECRET": "mock_client_secret",
        "REDDIT_USER_AGENT": "mock_user_agent",
        "SLACK_WEBHOOK_URL": "http://mock.slack.com/webhook",
        "NEWS_API_KEY": "mock_api_key",
        "OPENAI_API_KEY": "mock_openai_key"
    })

@pytest.fixture
def mock_news_api_requests_get(mocker):
    """Mock requests.get for FetchNewsAPI."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "ok",
        "totalResults": 2,
        "articles": [
            {
                "source": {"id": "wired", "name": "Wired"},
                "author": "Author A",
                "title": "Mock Article 1 Title",
                "description": "Mock Article 1 Description.",
                "url": "http://mockurl1.com",
                "urlToImage": "...",
                "publishedAt": "...",
                "content": "Full content of mock article 1."
            },
            {
                "source": {"id": "techcrunch", "name": "TechCrunch"},
                "author": "Author B",
                "title": "Mock Article 2 Title",
                "description": "Mock Article 2 Description.",
                "url": "http://mockurl2.com",
                "urlToImage": "...",
                "publishedAt": "...",
                "content": "Full content of mock article 2."
            }
        ]
    }
    mock_response.raise_for_status.return_value = None # Simulate success
    mock_get = mocker.patch('requests.get', return_value=mock_response)
    return mock_get

def test_fetch_news_api_basic(mock_news_api_requests_get, mock_env_vars):
    """Test FetchNewsAPI fetches and formats articles correctly."""
    config = {"query": "AI", "limit": 2, "apiKey_env": "NEWS_API_KEY"}
    result = fetch_news_api(config)
    
    assert len(result) == 2
    assert result[0]["id"] == "http://mockurl1.com"
    assert result[0]["title"] == "Mock Article 1 Title"
    assert result[0]["text"] == "Mock Article 1 Description."
    assert result[1]["url"] == "http://mockurl2.com"

    # Verify requests.get was called with correct parameters
    mock_news_api_requests_get.assert_called_once()
    args, kwargs = mock_news_api_requests_get.call_args
    assert kwargs['params']['q'] == "AI"
    assert kwargs['params']['apiKey'] == "mock_api_key"
    assert kwargs['params']['pageSize'] == 2

def test_fetch_news_api_missing_api_key(mocker):
    """Test FetchNewsAPI raises exception if API key is missing."""
    # Unset the NEWS_API_KEY env var for this test
    mocker.patch.dict('os.environ', {}, clear=True)
    
    config = {"query": "AI", "apiKey_env": "NEWS_API_KEY"}
    with pytest.raises(Exception, match="Environment variable 'NEWS_API_KEY' not found."):
        fetch_news_api(config)

def test_fetch_news_api_request_failure(mock_news_api_requests_get, mock_env_vars):
    """Test FetchNewsAPI handles request exceptions gracefully."""
    # The mock_news_api_requests_get fixture returns the mock for requests.get
    # We can set the side_effect on this returned mock object
    mock_news_api_requests_get.side_effect = requests.exceptions.RequestException("Network error")
    
    config = {"query": "AI", "apiKey_env": "NEWS_API_KEY"}
    with pytest.raises(Exception, match="Failed to fetch news from API: Network error"):
        fetch_news_api(config)

@pytest.fixture
def mock_openai_chat_completions(mocker):
    """Mock the OpenAI client's chat.completions.create method."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="This is a mock summary."))]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mocker.patch('genes.OpenAI', return_value=mock_client) # Patch genes.OpenAI specifically
    return mock_client

def test_summarize_articles_basic(mock_openai_chat_completions):
    """Test SummarizeArticles gene with basic input."""
    input_data = [
        {"title": "Test Article", "text": "This is some test content that needs to be summarized."},
        {"title": "Another Article", "text": "More content for summarization."}
    ]
    config = {}
    result = summarize_articles(config, input_data)
    
    assert len(result) == 2
    assert result[0]["summary"] == "This is a mock summary."
    assert result[1]["summary"] == "This is a mock summary." # Mock always returns same value
    assert mock_openai_chat_completions.chat.completions.create.call_count == 2
    
    # Verify prompts sent to OpenAI
    args, kwargs = mock_openai_chat_completions.chat.completions.create.call_args_list[0]
    assert "Test Article" in kwargs['messages'][1]['content']
    
    args, kwargs = mock_openai_chat_completions.chat.completions.create.call_args_list[1]
    assert "Another Article" in kwargs['messages'][1]['content']


def test_summarize_articles_empty_input(mock_openai_chat_completions):
    """Test SummarizeArticles with empty input data."""
    result = summarize_articles({}, [])
    assert result == []
    mock_openai_chat_completions.chat.completions.create.assert_not_called()

def test_summarize_articles_error_handling(mock_openai_chat_completions):
    """Test SummarizeArticles handles OpenAI errors gracefully."""
    mock_openai_chat_completions.chat.completions.create.side_effect = Exception("OpenAI API error")
    
    input_data = [{"title": "Error Article", "text": "Content"}]
    result = summarize_articles({}, input_data)
    
    assert len(result) == 1
    assert "Error summarizing: OpenAI API error" in result[0]["summary"]
    mock_openai_chat_completions.chat.completions.create.assert_called_once()
