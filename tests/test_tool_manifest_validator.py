import subprocess
import sys
import textwrap

# A valid gene manifest for testing
VALID_GENE_CONTENT = """
def some_valid_gene(config, input_data, data_context):
    \"\"\"
    manifest:
      type: SomeValidGene
      description: A gene that is properly documented.
      config_schema:
        - name: param1
          type: str
          required: true
    \"\"\"
    pass
"""

# An invalid gene manifest (bad indentation)
INVALID_GENE_CONTENT = """
def some_invalid_gene(config, input_data, data_context):
    \"\"\"
    manifest:
      type: SomeInvalidGene
    description: A broken manifest.
      config_schema:
        - name: param1
          type: str
    \"\"\"
    pass
"""

def test_manifest_validator_success(tmp_path):
    """Verify the validator passes with a well-formed manifest."""
    genes_file = tmp_path / "genes_valid.py"
    # Use textwrap.dedent to ensure consistent indentation
    genes_file.write_text(textwrap.dedent(VALID_GENE_CONTENT))

    result = subprocess.run(
        [sys.executable, "validate_manifests.py", str(genes_file)],
        capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, f"Validator failed unexpectedly. Stderr: {result.stderr}"
    assert "[PASS]  'some_valid_gene'" in result.stdout

def test_manifest_validator_failure(tmp_path):
    """Verify the validator fails with a malformed manifest."""
    genes_file = tmp_path / "genes_invalid.py"
    genes_file.write_text(textwrap.dedent(INVALID_GENE_CONTENT))

    result = subprocess.run(
        [sys.executable, "validate_manifests.py", str(genes_file)],
        capture_output=True, text=True, check=False
    )

    assert result.returncode == 1, "Validator did not fail as expected."
    assert "[FAIL]  'some_invalid_gene'" in result.stdout
    assert "Invalid YAML syntax" in result.stdout
