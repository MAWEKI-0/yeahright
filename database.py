import sqlite3
import chromadb
from chromadb.utils import embedding_functions

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect('foundry_new.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """Creates the necessary database tables if they don't already exist."""
    conn = get_db_connection()
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
    conn.commit()

def create_organism(name, genome_json):
    """Adds a new organism to the database."""
    conn = get_db_connection()
    conn.execute('INSERT INTO organisms (name, genome_json) VALUES (?, ?)', (name, genome_json))
    conn.commit()

def get_all_organisms():
    """Retrieves all organisms from the database."""
    conn = get_db_connection()
    organisms = conn.execute('SELECT * FROM organisms ORDER BY created_timestamp DESC').fetchall()
    return organisms

def get_organism_by_id(organism_id):
    """Retrieves a single organism by its ID."""
    conn = get_db_connection()
    organism = conn.execute('SELECT * FROM organisms WHERE id = ?', (organism_id,)).fetchone()
    return organism

def create_run(organism_id):
    """Creates a new run record and returns the run ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO organism_runs (organism_id, status) VALUES (?, ?)', (organism_id, 'running'))
    run_id = cursor.lastrowid
    conn.commit()
    return run_id

def update_run(run_id, status, log_output):
    """Updates a run record with the final status and log."""
    conn = get_db_connection()
    conn.execute('UPDATE organism_runs SET status = ?, log_output = ?, finished_timestamp = CURRENT_TIMESTAMP WHERE id = ?',
                 (status, log_output, run_id))
    conn.commit()

def get_runs_for_organism(organism_id):
    """Retrieves all runs for a specific organism."""
    conn = get_db_connection()
    runs = conn.execute('SELECT * FROM organism_runs WHERE organism_id = ? ORDER BY started_timestamp DESC', (organism_id,)).fetchall()
    return runs

def update_organism_last_run(organism_id, timestamp):
    """Updates the last run timestamp for an organism."""
    conn = get_db_connection()
    conn.execute('UPDATE organisms SET last_run_timestamp = ? WHERE id = ?', (timestamp, organism_id))
    conn.commit()

# --- ChromaDB Vector Store Integration ---
# Initialize the client. For prototyping, we can use an in-memory or on-disk instance.
# Using an on-disk instance ensures persistence between runs.
chroma_client = chromadb.PersistentClient(path="cortex_db/vector_store")

# Use a pre-built sentence transformer for creating embeddings
# This downloads the model on first use.
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Get or create a collection. A collection is like a table in a traditional DB.
# We pass the embedding function to the collection.
memory_collection = chroma_client.get_or_create_collection(
    name="organism_memories",
    embedding_function=sentence_transformer_ef
)

def save_memory(organism_id, memory_text):
    """Saves a piece of text to an Organism's associative memory."""
    # We use a unique ID for each memory chunk. Here, we can use a simple counter
    # or a more robust UUID. For now, we'll use a hash of the content.
    memory_id = f"{organism_id}_{hash(memory_text)}"
    
    memory_collection.add(
        documents=[memory_text],
        metadatas=[{"organism_id": organism_id}],
        ids=[memory_id]
    )
    return memory_id

def query_memory(organism_id, query_text, n_results=3):
    """Queries an Organism's associative memory and returns the most similar results."""
    results = memory_collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where={"organism_id": str(organism_id)} # Filter memories by organism
    )
    # The result object is complex; we'll return just the documents for simplicity.
    return results['documents'][0] if results['documents'] else []
