import sqlite3
import pytest
from datetime import datetime
import time

# Mock the database module to use an in-memory SQLite database for testing
from unittest.mock import patch

# Import the functions to be tested
import database as db

@pytest.fixture
def memory_db():
    """Fixture to set up an in-memory SQLite database for testing."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Create tables
    conn.execute('''
        CREATE TABLE IF NOT EXISTS organisms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            genome_json TEXT NOT NULL,
            created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_run_timestamp DATETIME
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS organism_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organism_id INTEGER,
            status TEXT,
            log_output TEXT,
            started_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_timestamp DATETIME,
            FOREIGN KEY (organism_id) REFERENCES organisms (id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS organism_state (
            organism_id INTEGER,
            key TEXT,
            value TEXT,
            PRIMARY KEY (organism_id, key),
            FOREIGN KEY (organism_id) REFERENCES organisms (id)
        )
    ''')
    
    yield conn
    
    conn.close()

@patch('database.get_db_connection')
def test_create_and_get_organism(mock_get_db_connection, memory_db):
    """Test creating and retrieving an organism."""
    mock_get_db_connection.return_value = memory_db
    
    db.create_organism("Test Organism", '{"genes":[]}')
    
    organisms = db.get_all_organisms()
    assert len(organisms) == 1
    assert organisms[0]['name'] == "Test Organism"
    
    organism = db.get_organism_by_id(organisms[0]['id'])
    assert organism['name'] == "Test Organism"

@patch('database.get_db_connection')
def test_create_and_manage_runs(mock_get_db_connection, memory_db):
    """Test creating, updating, and retrieving runs."""
    mock_get_db_connection.return_value = memory_db
    
    db.create_organism("Run Test Organism", '{"genes":[]}')
    organism = db.get_all_organisms()[0]
    
    run_id = db.create_run(organism['id'])
    assert run_id is not None
    
    runs = db.get_runs_for_organism(organism['id'])
    assert len(runs) == 1
    assert runs[0]['status'] == 'running'
    
    db.update_run(run_id, "success", "Log output")
    
    runs = db.get_runs_for_organism(organism['id'])
    assert runs[0]['status'] == 'success'
    assert runs[0]['log_output'] == "Log output"
    assert runs[0]['finished_timestamp'] is not None

@patch('database.get_db_connection')
def test_update_last_run_timestamp(mock_get_db_connection, memory_db):
    """Test updating the last run timestamp of an organism."""
    mock_get_db_connection.return_value = memory_db
    
    db.create_organism("Timestamp Test", '{"genes":[]}')
    organism = db.get_all_organisms()[0]
    
    assert organism['last_run_timestamp'] is None
    
    now = datetime.now()
    db.update_organism_last_run(organism['id'], now)
    
    updated_organism = db.get_organism_by_id(organism['id'])
    
    # Parse the timestamp string from the database back into a datetime object
    db_timestamp = datetime.fromisoformat(updated_organism['last_run_timestamp'])
    
    # Compare the timestamps with a tolerance of one second
    assert abs((db_timestamp - now).total_seconds()) < 1
