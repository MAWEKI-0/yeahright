import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the sys.path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from genes import generic_api_call

@patch('genes.requests.request')
def test_generic_api_get_success(mock_request):
    """Verify a successful GET request is made with the correct parameters."""
    # ARRANGE
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "success"}
    mock_response.headers = {"Content-Type": "application/json"}
    mock_request.return_value = mock_response

    config = {
        "method": "GET",
        "url": "https://api.example.com/data",
        "params": {"id": "123"},
        "headers": {"Authorization": "Bearer token"}
    }
    
    # ACT
    result = generic_api_call(config=config, input_data={}, data_context={})

    # ASSERT
    mock_request.assert_called_once_with(
        method="GET",
        url="https://api.example.com/data",
        headers={"Authorization": "Bearer token"},
        params={"id": "123"},
        json=None,
        timeout=30
    )
    
    assert result["status_code"] == 200
    assert result["body"] == {"data": "success"}

@patch('genes.requests.request')
def test_generic_api_post_success(mock_request):
    """Verify a successful POST request is made with a JSON body."""
    # ARRANGE
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": "new_resource"}
    mock_request.return_value = mock_response

    config = {"method": "POST", "url": "https://api.example.com/create"}
    input_data = {"json_body": {"name": "test", "value": 42}}
    
    # ACT
    result = generic_api_call(config=config, input_data=input_data, data_context={})

    # ASSERT
    mock_request.assert_called_once()
    # Access call arguments by keyword
    assert mock_request.call_args.kwargs['method'] == "POST"
    assert mock_request.call_args.kwargs['json'] == {"name": "test", "value": 42}
    
    assert result["status_code"] == 201
    assert result["body"] == {"id": "new_resource"}

@patch('genes.requests.request')
def test_generic_api_handles_request_exception(mock_request):
    """Verify that a network error is handled gracefully."""
    # ARRANGE
    from requests.exceptions import ConnectionError
    mock_request.side_effect = ConnectionError("Failed to connect")

    config = {"method": "GET", "url": "https://api.example.com/data"}
    
    # ACT
    result = generic_api_call(config=config, input_data={}, data_context={})
    
    # ASSERT
    assert "error" in result
    assert "API request failed" in result["error"]
    assert "Failed to connect" in result["reason"]
