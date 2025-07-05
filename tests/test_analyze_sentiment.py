import pytest
from genes import analyze_sentiment

# === A. Test the Happy Path ===
def test_analyze_sentiment_happy_path():
    """Verify the gene correctly analyzes sentiment for a list of posts."""
    # --- Assemble ---
    input_data = [
        {"id": 1, "title": "I love this product!", "text": "It's absolutely fantastic."},
        {"id": 2, "title": "I hate this product!", "text": "It's truly terrible."},
        {"id": 3, "title": "This is neutral.", "text": "It is what it is."},
    ]
    
    # --- Act ---
    result = analyze_sentiment(config={}, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert len(result) == 3
    assert "sentiment_score" in result[0]
    assert "sentiment_score" in result[1]
    assert "sentiment_score" in result[2]
    
    # VaderSentiment scores are compound: >0.05 is positive, <-0.05 is negative
    assert result[0]["sentiment_score"] > 0.05
    assert result[1]["sentiment_score"] < -0.05
    assert -0.05 <= result[2]["sentiment_score"] <= 0.05

# === C. Test for Statelessness ===
def test_analyze_sentiment_is_stateless():
    """Verify calling the gene twice with the same input yields the same result."""
    # --- Assemble ---
    input_data = [{"id": 1, "title": "A test sentence.", "text": "This is for consistency."}]
    
    # --- Act ---
    result1 = analyze_sentiment(config={}, input_data=input_data.copy(), data_context={})
    result2 = analyze_sentiment(config={}, input_data=input_data.copy(), data_context={})
    
    # --- Assert ---
    assert result1 == result2
    assert result1[0]["sentiment_score"] == result2[0]["sentiment_score"]

# === D. Test Edge Cases & Graceful Failure ===
def test_analyze_sentiment_empty_input():
    """Verify the gene handles an empty list of posts."""
    # --- Assemble ---
    input_data = []
    
    # --- Act ---
    result = analyze_sentiment(config={}, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert result == []

def test_analyze_sentiment_none_input():
    """Verify the gene handles None as input."""
    # --- Assemble ---
    input_data = None
    
    # --- Act ---
    result = analyze_sentiment(config={}, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert result == []

def test_analyze_sentiment_missing_keys():
    """Verify the gene handles posts with missing title or text keys."""
    # --- Assemble ---
    input_data = [
        {"id": 1, "title": "Only title"},
        {"id": 2, "text": "Only text"},
        {"id": 3, "url": "other data"},
    ]
    
    # --- Act ---
    result = analyze_sentiment(config={}, input_data=input_data, data_context={})
    
    # --- Assert ---
    assert len(result) == 3
    assert "sentiment_score" in result[0]
    assert "sentiment_score" in result[1]
    assert "sentiment_score" in result[2]
    # All should be neutral or near-neutral
    assert -0.05 <= result[2]["sentiment_score"] <= 0.05
