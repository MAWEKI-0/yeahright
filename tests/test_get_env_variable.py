import pytest
from unittest.mock import patch
from genes import get_env_variable

# === A. Test the Happy Path ===
@patch.dict('os.environ', {'MY_TEST_VAR': 'test_value'})
def test_get_env_variable_success():
    """Verify the function successfully retrieves an existing environment variable."""
    # --- Act ---
    result = get_env_variable('MY_TEST_VAR')
    
    # --- Assert ---
    assert result == 'test_value'

# === D. Test Edge Cases & Graceful Failure ===
def test_get_env_variable_not_found():
    """Verify the function raises a specific Exception for a missing variable."""
    # --- Act & Assert ---
    with pytest.raises(Exception, match="Environment variable 'MISSING_VAR' not found."):
        get_env_variable('MISSING_VAR')
