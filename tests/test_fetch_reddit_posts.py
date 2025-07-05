import pytest
from unittest.mock import patch, MagicMock
from genes import fetch_reddit_posts

# === A. Test the Happy Path ===
@patch('genes.praw.Reddit')
def test_fetch_reddit_posts_success(mock_reddit):
    """Verify the gene successfully fetches and formats posts from Reddit."""
    # --- Assemble ---
    # Mock the PRAW library's structure
    mock_post1 = MagicMock()
    mock_post1.id = "post1"
    mock_post1.title = "Title 1"
    mock_post1.selftext = "Text 1"
    mock_post1.url = "http://reddit.com/post1"
    
    mock_post2 = MagicMock()
    mock_post2.id = "post2"
    mock_post2.title = "Title 2"
    mock_post2.selftext = "Text 2"
    mock_post2.url = "http://reddit.com/post2"

    mock_subreddit = MagicMock()
    mock_subreddit.new.return_value = [mock_post1, mock_post2]
    
    mock_reddit_instance = mock_reddit.return_value
    mock_reddit_instance.subreddit.return_value = mock_subreddit

    config = {"subreddit": "testsub", "limit": 2}
    
    # --- Act ---
    result = fetch_reddit_posts(config=config, input_data=None, data_context={})
    
    # --- Assert ---
    assert len(result) == 2
    mock_reddit_instance.subreddit.assert_called_once_with("testsub")
    mock_subreddit.new.assert_called_once_with(limit=2)
    
    assert result[0]['id'] == "post1"
    assert result[1]['title'] == "Title 2"

# === C. Test for Statelessness ===
@patch('genes.praw.Reddit')
def test_fetch_reddit_posts_is_stateless(mock_reddit):
    """Verify calling the gene twice with the same input yields the same result."""
    # --- Assemble ---
    mock_post = MagicMock()
    mock_post.id = "stateless_post"
    mock_post.title = "Stateless"
    mock_post.selftext = ""
    mock_post.url = ""
    
    mock_subreddit = MagicMock()
    mock_subreddit.new.return_value = [mock_post]
    
    mock_reddit_instance = mock_reddit.return_value
    mock_reddit_instance.subreddit.return_value = mock_subreddit
    
    config = {"subreddit": "stateless_sub"}
    
    # --- Act ---
    result1 = fetch_reddit_posts(config=config, input_data=None, data_context={})
    result2 = fetch_reddit_posts(config=config, input_data=None, data_context={})
    
    # --- Assert ---
    assert result1 == result2
    assert mock_reddit.call_count == 2

# === D. Test Edge Cases & Graceful Failure ===
@patch('genes.praw.Reddit')
def test_fetch_reddit_posts_empty_response(mock_reddit):
    """Verify the gene handles an empty list of posts from the API."""
    # --- Assemble ---
    mock_subreddit = MagicMock()
    mock_subreddit.new.return_value = []
    
    mock_reddit_instance = mock_reddit.return_value
    mock_reddit_instance.subreddit.return_value = mock_subreddit
    
    config = {"subreddit": "empty_sub"}
    
    # --- Act ---
    result = fetch_reddit_posts(config=config, input_data=None, data_context={})
    
    # --- Assert ---
    assert result == []

@patch('genes.praw.Reddit', side_effect=Exception("PRAW Error"))
def test_fetch_reddit_posts_praw_exception(mock_reddit):
    """Verify the gene raises an exception if PRAW fails."""
    config = {"subreddit": "failing_sub"}
    
    with pytest.raises(Exception, match="PRAW Error"):
        fetch_reddit_posts(config=config, input_data=None, data_context={})
