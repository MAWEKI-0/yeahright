import json
import copy
import time
import schedule
import io
import contextlib
from genes import GENE_MAP

def run_organism(genome_json_str, run_id, organism_id, initial_input=None): # <-- Add organism_id here
    """Executes a workflow defined by a genome JSON string and captures logs."""
    log_stream = io.StringIO()
    with contextlib.redirect_stdout(log_stream):
        print("--- Running Organism ---\n")
        try:
            genome = json.loads(genome_json_str)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid genome JSON provided. {e}")
            return log_stream.getvalue(), "failed"

        data_context = {"initial_input": initial_input} if initial_input else {}
        final_status = "success"

        for gene_def in genome['genes']:
            gene_id = gene_def['id']
            gene_type = gene_def['type']
            
            if "skip_if" in gene_def:
                # Basic evaluator for "key.subkey == value"
                # This is a prototype and can be made more robust later
                condition_str = gene_def["skip_if"]
                parts = condition_str.replace(" ", "").split("==")
                key_path, expected_value_str = parts[0], parts[1]
                
                # Safely get the actual value from data_context
                keys = key_path.split('.')
                actual_value = data_context
                for key in keys:
                    if isinstance(actual_value, dict):
                        actual_value = actual_value.get(key)
                    else:
                        actual_value = None
                        break
                        
                # Convert expected value string to the type of the actual value
                if expected_value_str.lower() == 'true':
                    expected_value = True
                elif expected_value_str.lower() == 'false':
                    expected_value = False
                elif actual_value is not None:
                    try:
                        expected_value = type(actual_value)(expected_value_str)
                    except (ValueError, TypeError):
                        expected_value = expected_value_str
                else:
                    expected_value = expected_value_str

                if actual_value == expected_value:
                    print(f"Skipping gene '{gene_def['id']}' due to condition: {condition_str}")
                    continue # Skip to the next gene
            
            print(f"[Executing Gene] ID: {gene_id}, Type: {gene_type}")

            try:
                gene_function = GENE_MAP.get(gene_type)
                if not gene_function:
                    raise Exception(f"Gene type '{gene_type}' not found in GENE_MAP.")
                
                config = gene_def.get('config', {})
                contextual_config = copy.deepcopy(config) if config else {}
                contextual_config['organism_id'] = organism_id
                contextual_config['run_id'] = run_id
                
                input_key_path = gene_def.get('input_from')
                if input_key_path:
                    print(f"  -> Input: Reading from '{input_key_path}' in data_context.")
                    # Handle nested lookups
                    keys = input_key_path.split('.')
                    input_data = data_context
                    for key in keys:
                        if isinstance(input_data, dict):
                            input_data = input_data.get(key)
                        else:
                            input_data = None
                            break
                else:
                    input_data = None
                
                # Execute the gene
                output_data = gene_function(contextual_config, input_data, copy.deepcopy(data_context))

                # --- The Definitive Engine Fix ---
                # If 'output_as' is specified, use it. Otherwise, default to the gene's 'id'.
                output_key = gene_def.get('output_as', gene_id)
                
                data_context[output_key] = output_data
                print(f"  <- Output: Storing result in '{output_key}' in data_context.")

            except Exception as e:
                print(f"  **ERROR** during execution of gene '{gene_id}': {e}")
                final_status = "failed"
                break

        print(f"\n--- Organism Run Finished with status: {final_status} ---")
        return log_stream.getvalue(), final_status, data_context

# --- Main Execution Loop (Legacy - disabled as of Flask-APScheduler integration) ---

# def main():
#     """Main function to run the scheduler loop."""
#     # Schedule the organism to run every 10 minutes
#     schedule.every(10).minutes.do(run_organism)

#     print("Scheduler initialized. Organism will run every 10 minutes.")

#     # Run once immediately at the start
#     run_organism()

#     while True:
#         schedule.run_pending()
#         time.sleep(1)

# if __name__ == "__main__":
#     main()
