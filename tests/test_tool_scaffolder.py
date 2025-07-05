import subprocess
import sys
import os
import textwrap

# A template for a temporary genes.py file for isolated testing
TEMP_GENES_FILE_CONTENT = """
# --- Update the GENE_MAP ---
GENE_MAP = {
    # Existing genes would be here
}
"""

def test_scaffolder_tool_success(tmp_path):
    """
    Verify the scaffolder tool correctly generates a new gene function,
    a new test file, and updates the GENE_MAP.
    """
    # --- Assemble ---
    # 1. Create a temporary directory for the test to run in
    test_dir = tmp_path / "scaffold_test"
    test_dir.mkdir()
    
    # 2. Create a temporary genes.py file inside the test directory
    genes_file = test_dir / "genes.py"
    genes_file.write_text(textwrap.dedent(TEMP_GENES_FILE_CONTENT))
    
    # 3. Define the simulated error and expected new file paths
    error_string = "Gene 'scaffold_test_gene' uses unknown type 'MyNewTestGene'"
    expected_test_file = test_dir / "tests" / "test_my_new_test_gene.py"
    
    # The scaffolder script path
    scaffolder_script = os.path.join(os.getcwd(), "scaffold_from_failure.py")

    # --- Act ---
    # Run the scaffolder script from within the temporary directory
    result = subprocess.run(
        [sys.executable, scaffolder_script, error_string],
        capture_output=True, text=True, check=False, cwd=test_dir
    )

    # --- Assert ---
    # 1. Check that the script ran successfully
    assert result.returncode == 0, f"Scaffolder failed unexpectedly. Stderr: {result.stderr}"
    
    # 2. Verify the new test file was created
    assert expected_test_file.exists(), "The new test file was not created."
    
    # 3. Verify the content of the temporary genes.py file
    updated_genes_content = genes_file.read_text()
    
    # Assert that the new function definition is present
    assert "def my_new_test_gene(config, input_data, data_context=None):" in updated_genes_content
    
    # Assert that the GENE_MAP was updated correctly
    assert '"MyNewTestGene": my_new_test_gene,' in updated_genes_content
    
    # 4. Verify the content of the new test file
    new_test_content = expected_test_file.read_text()
    assert "from genes import my_new_test_gene" in new_test_content
    assert "def test_my_new_test_gene_basic_functionality(mock_data_context):" in new_test_content
