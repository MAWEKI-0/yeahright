import ast
import yaml
import textwrap
import os
import argparse

def validate_all_manifests(file_path):
    """
    Parses a given Python file, finds all function docstrings, extracts their
    'manifest:' blocks, and validates their YAML syntax.
    """
    print(f"--- Starting Manifest Validation for {file_path} ---")
    
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return False

    with open(file_path, 'r') as f:
        source_code = f.read()

    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        print(f"[ERROR] Could not parse {GENES_FILE_PATH}: {e}")
        return False

    all_passed = True
    functions_found = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # We only care about top-level functions for now
            if node.col_offset == 0:
                functions_found += 1
                func_name = node.name
                docstring = ast.get_docstring(node)

                if not docstring:
                    print(f"  - [SKIP]  '{func_name}': No docstring found.")
                    continue

                clean_doc = textwrap.dedent(docstring).strip()
                
                if 'manifest:' not in clean_doc:
                    print(f"  - [SKIP]  '{func_name}': No 'manifest:' block found in docstring.")
                    continue

                # Isolate the manifest string
                try:
                    manifest_str = clean_doc.split('manifest:', 1)[1]
                    
                    # Attempt to parse the YAML
                    yaml.safe_load(manifest_str)
                    
                    print(f"  - [PASS]  '{func_name}'")

                except yaml.YAMLError as e:
                    all_passed = False
                    print(f"  - [FAIL]  '{func_name}': Invalid YAML syntax.")
                    # Indent the error message for clarity
                    error_lines = str(e).split('\n')
                    for line in error_lines:
                        print(f"      > {line}")
                except IndexError:
                    # This case should be rare if 'manifest:' is present
                    all_passed = False
                    print(f"  - [FAIL]  '{func_name}': 'manifest:' keyword found, but no content followed.")

    print("\n--- Validation Summary ---")
    if functions_found == 0:
        print("No functions were found in the file.")
        return False
        
    if all_passed:
        print("Result: All found manifests are valid YAML.")
        return True
    else:
        print("Result: One or more manifests failed validation.")
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Validate the YAML syntax of 'manifest:' blocks in a Python file's docstrings."
    )
    parser.add_argument(
        'file_path', 
        type=str, 
        nargs='?', 
        default='genes.py',
        help="The path to the Python file to validate. Defaults to 'genes.py'."
    )
    args = parser.parse_args()

    if validate_all_manifests(args.file_path):
        # Exit with a success code
        exit(0)
    else:
        # Exit with a failure code, useful for CI/CD
        exit(1)
