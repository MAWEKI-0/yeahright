import re
import os
import argparse

# --- TEMPLATES ---

GENE_TEMPLATE = """
def {function_name}(config, input_data, data_context=None):
    \"\"\"
    [GENE] {gene_type}
    description: [Please provide a clear, one-line description of what this gene does.]
    manifest:
      inputs:
        # Based on the error, the following inputs are likely needed.
        # Please review and adjust them.
        # - name: input_data
        #   type: list_of_dicts
        # - name: config.parameter_name
        #   type: string
      outputs:
        # - type: list_of_dicts
        #   keys: ['id', 'title', 'text', 'url', 'new_field']
    \"\"\"
    print(f"Executing Gene: {function_name}")
    
    # --- Your gene logic goes here ---
    # Example: Access a configuration value
    # param = config.get('parameter_name')
    
    # Example: Process input data
    # if not input_data:
    #     return []
    
    # for item in input_data:
    #     item['new_field'] = "processed"
        
    # return input_data
    
    # If the gene is not yet implemented, it's best to raise an error.
    raise NotImplementedError("Gene '{gene_type}' is not yet implemented.")

"""

TEST_TEMPLATE = """
import pytest
from unittest.mock import patch
from genes import {function_name}

# --- Fixtures ---

@pytest.fixture
def mock_data_context():
    \"\"\"Provides a default data context for tests.\"\"\"
    return {{}}

# --- Test Cases ---

def test_{function_name}_basic_functionality(mock_data_context):
    \"\"\"
    Tests the basic, successful execution of the {function_name} gene.
    \"\"\"
    # --- Assemble ---
    # Create a sample config for the gene
    config = {{
        # 'parameter_name': 'test_value'
    }}
    
    # Create sample input data
    input_data = [
        # {{'id': 1, 'text': 'some data'}}
    ]
    
    # --- Act ---
    # Execute the gene with the test data
    # with pytest.raises(NotImplementedError):
    #     result = {function_name}(config, input_data, mock_data_context)
    
    # --- Assert ---
    # assert result is not None
    # assert len(result) == 1
    # assert result[0]['new_field'] == "processed"
    
    # For now, we expect it to fail until implemented
    with pytest.raises(NotImplementedError):
        {function_name}(config, input_data, mock_data_context)

def test_{function_name}_no_input_data(mock_data_context):
    \"\"\"
    Tests how the gene handles being called with None as its input_data.
    \"\"\"
    # --- Assemble ---
    config = {{}}
    input_data = None
    
    # --- Act & Assert ---
    # The default behavior for many genes is to raise an error or return an empty list.
    # Adjust the assertion based on the desired behavior.
    with pytest.raises(NotImplementedError):
        result = {function_name}(config, input_data, mock_data_context)
    # assert result == []

"""

# --- CORE FUNCTIONS ---

def to_snake_case(name):
    """Converts a PascalCase name to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def modify_genes_file(gene_type, function_name, gene_code):
    """
    Atomically modifies the genes.py file to add the new function
    before the GENE_MAP and update the GENE_MAP itself, preserving indentation.
    """
    filepath = 'genes.py'
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Find the line index for the GENE_MAP definition marker
    map_marker = '# --- Update the GENE_MAP ---'
    map_start_line_index = -1
    for i, line in enumerate(lines):
        if map_marker in line:
            map_start_line_index = i
            break
    
    if map_start_line_index == -1:
        print(f"[ERROR] Could not find GENE_MAP marker '{map_marker}' in '{filepath}'.")
        return False

    # --- Perform modifications in memory ---
    # 1. Prepare the new function code as a list of correctly-ended lines
    new_function_lines = [line + '\n' for line in gene_code.strip().split('\n')]
    # Add spacing before and after the function block
    new_function_lines.insert(0, '\n')
    new_function_lines.append('\n')

    # 2. Insert the new function lines before the GENE_MAP marker
    # This is a list-to-list insertion, which is safe.
    lines[map_start_line_index:map_start_line_index] = new_function_lines
    
    # The insertion shifts the end index, so we must re-calculate it
    # by searching from the new position of the marker.
    new_map_start_index = map_start_line_index + len(new_function_lines)
    new_map_end_index = -1
    for i in range(new_map_start_index, len(lines)):
        if '}' in lines[i]:
            new_map_end_index = i
            break

    if new_map_end_index == -1:
        print(f"[ERROR] Could not find closing brace of GENE_MAP after modification.")
        return False

    # 3. Insert the new GENE_MAP entry before the closing brace.
    # The indentation (4 spaces) is crucial.
    new_map_line = f'    "{gene_type}": {function_name},\n'
    lines.insert(new_map_end_index, new_map_line)

    # --- Write all changes back to the file at once ---
    with open(filepath, 'w') as f:
        f.writelines(lines)
    
    print(f"  - Atomically updated '{filepath}' with new gene and GENE_MAP entry.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new gene and test file from a 'Perfect Failure' error log.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'error_string', 
        type=str, 
        help="The error string, typically in the format:\n"
             "\"Gene 'YourGeneName' uses unknown type 'YourGeneType'.\""
    )
    args = parser.parse_args()

    # Regex to extract the gene type from the error message
    match = re.search(r"uses unknown type '(\w+)'", args.error_string)
    if not match:
        print("[ERROR] The error string does not match the expected format.")
        print("        Expected format: \"Gene '...' uses unknown type 'YourGeneType'.\"")
        exit(1)
        
    gene_type = match.group(1)
    function_name = to_snake_case(gene_type)
    
    print(f"\n--- Scaffolding for Gene Type: {gene_type} ---")
    print(f"  - Function name will be: {function_name}")

    # 1. Generate the gene code from the template
    gene_code = GENE_TEMPLATE.format(function_name=function_name, gene_type=gene_type)
    
    # 2. Atomically modify the genes.py file
    if not modify_genes_file(gene_type, function_name, gene_code):
        exit(1) # Exit if modification failed

    # 3. Generate the test code
    test_code = TEST_TEMPLATE.format(function_name=function_name)
    
    # Ensure the 'tests' directory exists relative to the current working directory
    tests_dir = 'tests'
    if not os.path.exists(tests_dir):
        os.makedirs(tests_dir)
        print(f"  - Created missing directory: '{tests_dir}'")
        
    test_filepath = os.path.join(tests_dir, f'test_{function_name}.py')
    with open(test_filepath, 'w') as f:
        f.write(test_code)
    print(f"  - Created new test file at '{test_filepath}'")
    
    print("\n--- Scaffolding Complete ---")
    print("Next steps:")
    print(f"1. Implement the logic in the '{function_name}' function in 'genes.py'.")
    print(f"2. Refine the auto-generated test cases in '{test_filepath}'.")
    print("3. Run 'pytest' to ensure your new, unimplemented gene fails its tests correctly.")

if __name__ == '__main__':
    main()
