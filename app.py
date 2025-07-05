from dotenv import load_dotenv
load_dotenv()

# --- IMPORTS ---
import threading
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from flask_apscheduler import APScheduler
from croniter import croniter
import logging

import database as db
from engine import run_organism
from genesis import generate_genome_from_prompt
from genes import GENE_MAP # Import GENE_MAP to validate gene types

# --- APP AND SCHEDULER SETUP ---
class Config:
    SCHEDULER_API_ENABLED = True

app = Flask(__name__)

# Explicitly configure the Flask logger to ensure output is visible
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

app.config.from_object(Config())

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# --- DATABASE INITIALIZATION ---
# This ensures the database tables are created when the app starts.
with app.app_context():
    db.create_tables()

# --- ASYNC EXECUTION HELPERS ---
def run_and_log(genome_json, run_id, organism_id):
    """Target function for the background thread. Executes the organism and updates the run log."""
    with app.app_context(): # CRITICAL: A new thread needs the app context to use the db
        app.logger.info(f"Thread for run {run_id} started for organism {organism_id}.")
        log_output, final_status = run_organism(genome_json, run_id, organism_id)
        db.update_run(run_id, final_status, log_output)
        app.logger.info(f"Thread for run {run_id} finished.")

def validate_genome(genome_json_str):
    """
    Performs a pre-flight validation of the genome JSON.
    Returns a list of errors if any, otherwise an empty list.
    """
    errors = []
    try:
        genome = json.loads(genome_json_str)
    except json.JSONDecodeError:
        errors.append("Invalid Genome JSON format.")
        return errors

    # Basic structure checks
    if not isinstance(genome, dict):
        errors.append("Genome must be a dictionary.")
        return errors
    if "name" not in genome or not isinstance(genome["name"], str):
        errors.append("Genome must have a 'name' (string).")
    if "genes" not in genome or not isinstance(genome["genes"], list):
        errors.append("Genome must have a 'genes' (list).")
    
    # Check trigger block (optional but good practice)
    if "trigger" in genome:
        trigger = genome["trigger"]
        if not isinstance(trigger, dict):
            errors.append("Trigger must be a dictionary.")
        if "type" not in trigger or not isinstance(trigger["type"], str):
            errors.append("Trigger must have a 'type' (string).")
        if trigger.get("type") == "schedule" and "cron" not in trigger:
            errors.append("Schedule trigger must specify 'cron'.")

    # Validate each gene in the list
    if "genes" in genome and isinstance(genome["genes"], list):
        gene_ids = set() # Initialize the set here, inside the validation logic for a specific genome
        for i, gene_def in enumerate(genome["genes"]):
            if not isinstance(gene_def, dict):
                errors.append(f"Gene at index {i} must be a dictionary.")
                continue

            # Check required keys for each gene
            if "id" not in gene_def or not isinstance(gene_def["id"], str):
                errors.append(f"Gene at index {i} must have an 'id' (string).")
            else:
                if gene_def["id"] in gene_ids:
                    errors.append(f"Duplicate gene ID '{gene_def['id']}' at index {i}.")
                gene_ids.add(gene_def["id"])

            if "type" not in gene_def or not isinstance(gene_def["type"], str):
                errors.append(f"Gene '{gene_def.get('id', i)}' must have a 'type' (string).")
            elif gene_def["type"] not in GENE_MAP:
                errors.append(f"Gene '{gene_def.get('id', i)}' uses unknown type '{gene_def['type']}'.")

            # Check config (must be a dict if present)
            if "config" in gene_def and not isinstance(gene_def["config"], dict):
                errors.append(f"Gene '{gene_def.get('id', i)}' 'config' must be a dictionary.")

            # Check input_from/output_as (must be strings if present)
            if "input_from" in gene_def and not isinstance(gene_def["input_from"], str):
                errors.append(f"Gene '{gene_def.get('id', i)}' 'input_from' must be a string.")
            if "output_as" in gene_def and not isinstance(gene_def["output_as"], str):
                errors.append(f"Gene '{gene_def.get('id', i)}' 'output_as' must be a string.")
        
    return errors

def trigger_run_in_background(organism_id, genome_json):
    """Helper to start a run from any context (manual or scheduled)."""
    with app.app_context(): # Use context to ensure db calls are safe
        run_id = db.create_run(organism_id)
        db.update_organism_last_run(organism_id, datetime.now())

        # Run the organism in a new background thread
        run_thread = threading.Thread(target=run_and_log, args=(genome_json, run_id, organism_id))
        run_thread.start()
        app.logger.info(f"--- Started background run {run_id} for Organism #{organism_id} ---")

# --- SCHEDULER HEARTBEAT ---
@scheduler.task('interval', id='scheduler_heartbeat', seconds=60)
def check_and_run_organisms():
    """
    The autonomic nervous system. Runs every minute to check which organisms to trigger.
    Flask-APScheduler automatically provides an app context for scheduled tasks.
    """
    app.logger.info(f"--- [SCHEDULER] Heartbeat at {datetime.now()} ---")
    organisms = db.get_all_organisms()
    
    for organism in organisms:
        try:
            genome = json.loads(organism['genome_json'])
            cron_schedule = genome.get('trigger', {}).get('cron')
            
            if not cron_schedule:
                continue

            now = datetime.now()
            last_run_str = organism['last_run_timestamp']
            last_run = datetime.fromisoformat(last_run_str) if last_run_str else None

            # Use croniter to check if a job should have run since the last check
            base_time = last_run or now
            cron = croniter(cron_schedule, base_time)
            scheduled_time = cron.get_prev(datetime)
            
            if last_run is None or last_run < scheduled_time:
                app.logger.info(f"--- [SCHEDULER] Triggering Organism #{organism['id']}: {organism['name']} ---")
                trigger_run_in_background(organism['id'], organism['genome_json'])
        
        except Exception as e:
            app.logger.error(f"--- [SCHEDULER] Error processing Organism #{organism['id']}: {e} ---")

# --- FLASK WEB ROUTES ---
@app.route('/')
def index():
    """Displays a list of all organisms."""
    organisms = db.get_all_organisms()
    return render_template('index.html', organisms=organisms)

@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        name = request.form['name']
        genome_json_str = request.form['genome_json'] # The raw string from the form

        # --- NEW LOGIC: Attempt to unwrap API response format ---
        genome_to_validate_and_store = genome_json_str # Default to original string

        try:
            # First, try to parse the entire input string
            temp_parsed_input = json.loads(genome_json_str)

            # Check if it matches the API response wrapper format
            if isinstance(temp_parsed_input, dict) and "generated_genome" in temp_parsed_input and isinstance(temp_parsed_input["generated_genome"], (str, dict, list)):
                # It's the API response wrapper. Extract the actual Genome.
                app.logger.info("Create Organism: Detected API response wrapper. Attempting to unwrap Genome.")
                
                # The inner "generated_genome" value might be a string (from old API)
                # or already a parsed object (from new API). Handle both.
                inner_genome_data = temp_parsed_input["generated_genome"]
                if isinstance(inner_genome_data, str):
                    # If it's a string, try to parse it (from older /generate_genome output)
                    app.logger.info("Create Organism: Inner generated_genome is a string, parsing it.")
                    genome_to_validate_and_store = inner_genome_data # Now it's the raw JSON string again
                elif isinstance(inner_genome_data, (dict, list)):
                    # If it's already a dict/list, stringify it for validate_genome and storage
                    app.logger.info("Create Organism: Inner generated_genome is already parsed. Stringifying for validation/storage.")
                    genome_to_validate_and_store = json.dumps(inner_genome_data, indent=2)
                else:
                    app.logger.warning(f"Create Organism: Unhandled type for inner generated_genome: {type(inner_genome_data)}")
                    # Fallback: use original string, let validate_genome handle error
                    genome_to_validate_and_store = genome_json_str
        except json.JSONDecodeError:
            # Input string is not even valid JSON at the top level.
            # Let validate_genome catch the primary "Invalid Genome JSON format" error.
            app.logger.info("Create Organism: Input is not a JSON wrapper. Passing original string for validation.")
            genome_to_validate_and_store = genome_json_str
        # --- END NEW LOGIC ---

        # Now, call validate_genome with the (potentially unwrapped) Genome JSON string
        validation_errors = validate_genome(genome_to_validate_and_store)
        if validation_errors:
            # Pass original genome_json_str back to maintain user's input in form
            return render_template('create.html', errors=validation_errors, name=name, genome_json=genome_json_str)

        # Store the unwrapped/validated genome string in the database
        db.create_organism(name, genome_to_validate_and_store)
        return redirect(url_for('index'))
    return render_template('create.html')

@app.route('/organism/<int:organism_id>')
def detail(organism_id):
    """Displays the details and run history of a specific organism."""
    organism = db.get_organism_by_id(organism_id)
    runs = db.get_runs_for_organism(organism_id)
    return render_template('detail.html', organism=organism, runs=runs)


@app.route('/organism/<int:organism_id>/run', methods=['POST'])
def trigger_run(organism_id):
    """Action to MANUALLY trigger a new run for an organism."""
    organism = db.get_organism_by_id(organism_id)
    trigger_run_in_background(organism['id'], organism['genome_json'])
    return redirect(url_for('detail', organism_id=organism_id))

@app.route('/generate_genome', methods=('GET', 'POST'))
def generate_genome():
    """Handles generating a new genome from a prompt."""
    if request.method == 'POST':
        if request.is_json:
            user_prompt = request.json['prompt']
        else:
            user_prompt = request.form['prompt']
        
        # --- ORIGINAL GENOME GENERATION ---
        generated_genome_str = generate_genome_from_prompt(user_prompt)

        # --- ADD THIS NEW PRE-PROCESSING BLOCK ---
        # Strip markdown code block wrappers if present (```json\n...\n```)
        if generated_genome_str.strip().startswith("```json") and \
           generated_genome_str.strip().endswith("```"):
            generated_genome_str = generated_genome_str.strip()[len("```json"):].rsplit("```", 1)[0].strip()
            app.logger.info("Stripped markdown code block wrapper from AI-generated Genome.")
        # --- END NEW PRE-PROCESSING BLOCK ---

        # --- NEW LOGIC: Parse the genome string into a Python object for consistent return ---
        try:
            parsed_genome_obj = json.loads(generated_genome_str)
        except json.JSONDecodeError as e:
            app.logger.error(f"Failed to re-parse AI-generated Genome string after stripping: {e}")
            return jsonify({
                "status": "internal_error",
                "message": "AI generated non-parseable JSON after stripping.",
                "raw_output_attempt": generated_genome_str
            }), 500 # Internal Server Error


        validation_errors = validate_genome(generated_genome_str) # Keep validation on string for now
        if validation_errors:
            app.logger.warning(f"AI-generated Genome failed validation: {validation_errors}")
            return jsonify({
                "status": "validation_failed",
                "errors": validation_errors,
                "generated_genome": parsed_genome_obj # <--- Return parsed object here
            }), 400 # Bad Request

        return jsonify({
            "status": "success",
            "generated_genome": parsed_genome_obj # <--- Return parsed object here
        })

    # For a GET request, just show the page.
    return render_template('generate.html', generated_genome="", user_prompt="")

# --- Main Execution ---
if __name__ == '__main__':
    with app.app_context():
        app.logger.info("--- Flask app starting ---") # Revert to a simpler message
    app.run(debug=True, use_reloader=True) # <--- CRITICAL CHANGE HERE
