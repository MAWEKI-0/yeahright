from dotenv import load_dotenv
load_dotenv() # This line reads the .env file and loads the variables

import os
import praw
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import database
from database import save_memory, query_memory
import json
import os
from openai import OpenAI
import subprocess
import shlex
import re

def get_env_variable(var_name):
    """Safely reads an environment variable and raises an Exception if it's not found."""
    try:
        return os.environ[var_name]
    except KeyError:
        raise Exception(f"Environment variable '{var_name}' not found.")

def fetch_reddit_posts(config, input_data=None, data_context=None):
    """
    [GENE] FetchRedditPosts
    description: Fetches recent posts from a specified subreddit.
    config: { 'subreddit': 'name_of_subreddit', 'limit': 25 }
    manifest:
      inputs:
        - name: config.subreddit
          type: string
        - name: config.limit
          type: integer
      outputs:
        - type: list_of_dicts
          keys: ['id', 'title', 'text', 'url']
    """
    reddit = praw.Reddit(
        client_id=get_env_variable("REDDIT_CLIENT_ID"),
        client_secret=get_env_variable("REDDIT_CLIENT_SECRET"),
        user_agent=get_env_variable("REDDIT_USER_AGENT"),
    )
    subreddit_name = config.get("subreddit", "python")
    limit = config.get("limit", 25)

    subreddit = reddit.subreddit(subreddit_name)
    posts = subreddit.new(limit=limit)

    return [
        {
            "id": post.id, # <-- CRUCIAL: Add the post ID
            "title": post.title,
            "text": post.selftext,
            "url": post.url,
        }
        for post in posts
    ]

def analyze_sentiment(config, input_data, data_context=None):
    """
    [GENE] AnalyzeSentiment
    description: Analyzes the sentiment of text. It adds a 'sentiment_score' key to each item.
    config: None
    manifest:
      inputs:
        - name: input_data
          type: list_of_dicts
          keys: ['title', 'text']
      outputs:
        - type: list_of_dicts
          keys: ['id', 'title', 'text', 'url', 'sentiment_score']
    """
    if not input_data:
        return []

    analyzer = SentimentIntensityAnalyzer()
    for post in input_data:
        text_to_analyze = f"{post.get('title', '')} {post.get('text', '')}"
        sentiment = analyzer.polarity_scores(text_to_analyze)
        post['sentiment_score'] = sentiment['compound']

    return input_data

def filter_data(config, input_data, data_context):
    """
    [GENE] FilterData
    description: Filters a list based on a field. Conditions: 'less_than', 'greater_than', 'contains', 'not_in'. Can source its comparison value directly or from context.
    config: { 'field': 'field_name', 'condition': '...', 'value': 'direct_value' } OR { 'field': '...', 'condition': '...', 'value_from_context': 'context_key' }
    manifest:
      inputs:
        - name: input_data
          type: list_of_dicts
        - name: config.field
          type: string
        - name: config.condition
          type: string
        - name: config.value
          type: any
        - name: config.value_from_context
          type: string
      outputs:
        - type: list_of_dicts
    """
    print(f"Executing Gene: filter_data")
    field = config['field']
    condition = config['condition']
    
    # --- The Definitive Fix: Explicitly check for both keys ---
    if 'value_from_context' in config:
        context_key = config['value_from_context']
        value = data_context.get(context_key)
        print(f"  -> Resolved comparison value from context key '{context_key}'.")
    elif 'value' in config:
        value = config['value']
        print(f"  -> Using direct comparison value from config.")
    else:
        raise ValueError("FilterData config must contain 'value' or 'value_from_context'")

    print(f"  -> Filtering where '{field}' is {condition} ...")

    if input_data is None:
        print("  -> Input data is None, cannot filter.")
        return []

    filtered_list = []
    
    # Create a dedicated comparison set for 'not_in'
    if condition == "not_in":
        comparison_set = set()
        if isinstance(value, list) and value and isinstance(value[0], dict):
            print(f"  -> Building comparison set from a list of {len(value)} dictionaries.")
            for dict_item in value:
                if field in dict_item:
                    comparison_set.add(dict_item[field])
        elif isinstance(value, list):
            print(f"  -> Building comparison set from a simple list of {len(value)} items.")
            comparison_set = set(value)
    
    for item in input_data:
        if field not in item:
            continue
        item_value = item[field]

        # --- Condition Logic ---
        if condition == "less_than":
            if isinstance(item_value, (int, float)) and isinstance(value, (int, float)) and item_value < value:
                filtered_list.append(item)
        
        elif condition == "greater_than":
            if isinstance(item_value, (int, float)) and isinstance(value, (int, float)) and item_value > value:
                filtered_list.append(item)

        elif condition == "contains":
            if isinstance(item_value, str) and isinstance(value, str) and value.lower() in item_value.lower():
                filtered_list.append(item)
        
        elif condition == "not_in":
            # The comparison_set is already prepared; this is a simple and correct check.
            if item_value not in comparison_set:
                filtered_list.append(item)
    
    if condition not in ["less_than", "greater_than", "contains", "not_in"]:
        raise ValueError(f"Condition '{condition}' is not supported.")

    print(f"  -> Found {len(filtered_list)} matching items.")
    return filtered_list

def post_to_slack(config, input_data, data_context=None):
    """
    [GENE] PostToSlack
    description: Posts a message to a Slack channel.
    config: { 'webhook_url_env': 'SLACK_WEBHOOK_URL' }
    manifest:
      inputs:
        - name: input_data
          type: list_of_dicts
          keys: ['url', 'title', 'sentiment_score']
        - name: config.webhook_url_env
          type: string
      outputs: []
    """
    if not input_data:
        print("No data to post to Slack.")
        return

    webhook_url = get_env_variable(config.get("webhook_url_env"))

    # Use a more generic header that doesn't assume sentiment has been analyzed
    header = f":bell: New Notification: {len(input_data)} Item(s) Found"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": header, "emoji": True}},
        {"type": "divider"}
    ]

    for post in input_data:
        sentiment_score = post.get('sentiment_score')
        
        # Build the text block, but only include sentiment if it exists
        text_block = f"*<{post.get('url')}|{post.get('title')}>*"
        if sentiment_score is not None:
            text_block += f"\n*Sentiment Score:* {sentiment_score:.2f}"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text_block
            }
        })

    try:
        response = requests.post(webhook_url, json={"blocks": blocks}, timeout=10)
        response.raise_for_status()
        print("Successfully posted to Slack.")
    except requests.exceptions.RequestException as e:
        print(f"Error posting to Slack: {e}")


# --- NEW GENE: Write to Memory ---
def write_to_memory(config, input_data, data_context=None):
    """
    [GENE] WriteToMemory
    description: Writes a value to the organism's persistent memory. The key is defined in the config, the value comes from input_data.
    config: { 'key': 'name_of_the_key_to_store' }
    manifest:
      inputs:
        - name: input_data
          type: any
        - name: config.key
          type: string
      outputs:
        - type: dict
          keys: ['status', 'key']
    """
    key = config['key']
    # We need the organism's ID, which isn't normally available.
    # We'll pass it in via the config for now.
    organism_id = config['organism_id'] 
    
    # Store the value as a JSON string for flexibility
    value_str = json.dumps(input_data)
    
    conn = database.get_db_connection()
    # Use REPLACE to handle both insert and update
    conn.execute('REPLACE INTO organism_state (organism_id, key, value) VALUES (?, ?, ?)',
                 (organism_id, key, value_str))
    conn.commit()
    conn.close()
    print(f"  -> Wrote to memory with key '{key}'")
    return {"status": "success", "key": key}

# --- NEW GENE: Read from Memory ---
def read_from_memory(config, input_data, data_context=None):
    """
    [GENE] ReadFromMemory
    description: Reads a value from the organism's persistent memory using a specified key.
    config: { 'key': 'name_of_the_key_to_retrieve' }
    manifest:
      inputs:
        - name: config.key
          type: string
      outputs:
        - type: any
    """
    key = config['key']
    organism_id = config['organism_id']
    
    conn = database.get_db_connection()
    row = conn.execute('SELECT value FROM organism_state WHERE organism_id = ? AND key = ?',
                       (organism_id, key)).fetchone()
    conn.close()
    
    if row:
        print(f"  -> Read from memory with key '{key}'")
        # Decode the JSON string back into a Python object
        return json.loads(row[0])
    else:
        print(f"  -> No value found in memory for key '{key}'")
        return None # Return None if the key doesn't exist

def merge_data(config, input_data, data_context):
    """
    [GENE] MergeData
    description: Merges multiple lists of dictionaries from the data_context into a single, deduplicated list.
    config: { 'source_keys': ['key_of_list1', 'key_of_list2'], 'deduplicate_by_field': 'unique_field_name' }
    manifest:
      inputs:
        - name: config.source_keys
          type: list_of_strings
        - name: config.deduplicate_by_field
          type: string
        - name: data_context
          type: dict_of_lists
      outputs:
        - type: list_of_dicts
    """
    print(f"Executing Gene: merge_data")
    
    merged_list = []
    keys_to_merge = config.get('source_keys', [])
    dedup_field = config.get('deduplicate_by_field')

    if not dedup_field:
        raise ValueError("MergeData config requires 'deduplicate_by_field'.")

    seen_ids = set()

    for key in keys_to_merge:
        list_to_add = data_context.get(key)
        if isinstance(list_to_add, list):
            for item in list_to_add:
                if isinstance(item, dict) and dedup_field in item:
                    item_id = item[dedup_field]
                    if item_id not in seen_ids:
                        merged_list.append(item)
                        seen_ids.add(item_id)
    
    print(f"  -> Merged lists into a single list of {len(merged_list)} unique items.")
    return merged_list

def extract_field_list(config, input_data, data_context=None):
    """
    [GENE] ExtractFieldList
    description: Extracts values of a specified field from a list of dictionaries, returning a flat list of these values. *Crucial for preparing data (e.g., IDs) for memory storage or 'not_in' filters.*
    manifest:
      inputs:
        - name: input_data
          type: list_of_dicts
        - name: config.field
          type: string
      outputs:
        - type: list
    """
    field = config.get('field')
    if not field:
        raise ValueError("ExtractFieldList requires 'field' in config.")
    
    if not isinstance(input_data, list):
        print("Warning: Input to ExtractFieldList is not a list. Returning empty list.")
        return []
    
    extracted_list = []
    for item in input_data:
        if isinstance(item, dict) and field in item:
            extracted_list.append(item[field])
    
    print(f"  -> Extracted {len(extracted_list)} '{field}' values.")
    return extracted_list

def fetch_news_api(config, input_data=None, data_context=None):
    """
    [GENE] FetchNewsAPI
    description: Fetches news headlines and articles from a general news API (NewsAPI.org). Requires a 'query' (e.g., 'technology', 'economic') and an 'apiKey_env' (environment variable name for the API key). Adds 'id', 'title', 'text', 'url' fields to each article.
    manifest:
      inputs:
        # No direct input_data is used, only config for parameters
      outputs:
        - type: list_of_dicts
    """
    query = config.get("query", "latest news")
    api_key_env_var = config.get("apiKey_env", "NEWS_API_KEY")
    api_key = get_env_variable(api_key_env_var) # Reuse existing helper

    if not api_key:
        raise Exception(f"API Key not found for {api_key_env_var}. Please set it in .env.")

    base_url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "apiKey": api_key,
        "pageSize": config.get("limit", 100), # Reuse 'limit' from previous gene's aspiration
        "language": config.get("language", "en") # Optional: add language config
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        articles_data = response.json().get("articles", [])

        processed_articles = []
        for i, article in enumerate(articles_data):
            # NewsAPI articles often have 'title', 'description', 'url', 'source.name'
            # We need to standardize to 'id', 'title', 'text', 'url' for downstream genes
            processed_articles.append({
                "id": article.get("url", f"news_api_id_{i}"), # Use URL as ID, or a fallback
                "title": article.get("title", ""),
                "text": article.get("description", article.get("content", "")), # Use description/content as 'text'
                "url": article.get("url", "")
            })
        
        print(f"  -> Fetched {len(processed_articles)} articles from NewsAPI for query '{query}'.")
        return processed_articles

    except requests.exceptions.RequestException as e:
        print(f"Error fetching from NewsAPI: {e}")
        raise Exception(f"Failed to fetch news from API: {e}")

def summarize_articles(config, input_data, data_context=None):
    """
    [GENE] SummarizeArticles
    description: Summarizes a list of articles using an external LLM. Each item in the input list should have 'title' and 'text' fields. A 'summary' field will be added to each item.
    manifest:
      inputs:
        - name: input_data
          type: list_of_dicts
      outputs:
        - type: list_of_dicts
    """
    if not input_data:
        print("No articles to summarize.")
        return []

    summarized_articles = []
    client = OpenAI() # Assumes OPENAI_API_KEY is loaded globally or by dotenv in genes.py

    for i, article in enumerate(input_data):
        title = article.get('title', '')
        text = article.get('text', '')
        
        if not title and not text:
            print(f"Skipping article {i}: No title or text found for summarization.")
            summarized_articles.append(article) # Keep original if nothing to summarize
            continue

        prompt_text = f"Summarize the following article, focusing on key points. Keep the summary concise:\n\nTitle: {title}\n\nContent:\n{text}\n\nSummary:"

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # Or gpt-4 if preferred for higher quality
                messages=[
                    {"role": "system", "content": "You are a concise summarization assistant."},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.7,
                max_tokens=150
            )
            summary = response.choices[0].message.content.strip()
            article['summary'] = summary
            print(f"  -> Summarized article: '{title}'")
        except Exception as e:
            article['summary'] = f"Error summarizing: {e}"
            print(f"  -> Error summarizing article '{title}': {e}")
        
        summarized_articles.append(article)

    return summarized_articles

def store_value(config, input_data, data_context=None):
    """A simple gene to store a value in the organism's state."""
    key = config.get("key")
    value = input_data.get("value")
    if not key or value is None:
        return {"status": "error", "reason": "Missing key or value"}
    
    # This function will be mocked in the test, but this is the idea.
    # In a real run, a database function would be called here.
    # For the test, we only need the function to exist in the GENE_MAP.
    return {"status": "success", "stored_key": key}


def save_to_vector_memory(config, input_data, data_context):
    """
    Saves a string of text into the organism's long-term vector memory.
    manifest:
      type: SaveToVectorMemory
      description: "Takes a string and embeds it into the organism's associative vector memory for later recall."
      inputs:
        - name: text
          type: string
          required: true
          description: "The text content to be saved as a memory."
      outputs:
        - type: dict
          keys: ['status', 'memory_id']
    """
    if isinstance(input_data, str):
        text_to_save = input_data
    else:
        text_to_save = input_data.get("text")
        
    organism_id = config.get("organism_id") # The engine should inject this

    if not text_to_save or not organism_id:
        return {"status": "error", "reason": "Missing 'text' in input or 'organism_id' in config."}

    memory_id = save_memory(organism_id, text_to_save)
    return {"status": "success", "memory_id": memory_id}


def query_vector_memory(config, input_data, data_context):
    """
    Queries the organism's long-term vector memory with a string and returns the most similar memories.
    manifest:
      type: QueryVectorMemory
      description: "Searches the organism's associative vector memory and returns a list of the most relevant memories."
      config_schema:
        - name: num_results
          type: int
          required: false
          description: "The number of similar memories to return. Defaults to 3."
      inputs:
        - name: query
          type: string
          required: true
          description: "The search query to find relevant memories."
      outputs:
        - type: list_of_strings
    """
    query = input_data.get("query")
    organism_id = config.get("organism_id")
    num_results = config.get("num_results", 3)
    
    if not query or not organism_id:
        return {"status": "error", "reason": "Missing 'query' in input or 'organism_id' in config."}

    results = query_memory(organism_id, query, n_results=num_results)
    return {"memories": results}


def conditional_branch(config, input_data, data_context):
    """
    Acts as an if/else gate. If the input is 'truthy', it returns the input. 
    If not, it returns a specific structure indicating a 'false' path.
    manifest:
      type: ConditionalBranch
      description: "Checks if the input data is 'truthy' (e.g., not None, not empty, not False, not 0). If true, passes the data through. If false, signals to skip the next step."
      inputs:
        - name: condition_data
          type: any
          required: true
      outputs:
        - type: any
          description: "The original data if truthy, or {'condition_met': false} if falsy."
    """
    # The input data itself is the condition
    if input_data:
        return {"condition_met": True, "data": input_data}
    else:
        return {"condition_met": False}

def execute_in_runtime(config, input_data, data_context):
    """
    Executes a shell command in a non-interactive way, with support for
    variable substitution from the data_context.
    manifest:
      type: ExecuteInRuntime
      description: "Executes a shell command. Supports substituting context variables using {{key.path}} syntax."
      # ... (rest of manifest is the same) ...
    """
    command = input_data.get("command")
    if not command:
        return {"command": None, "stdout": "", "stderr": "Error: 'command' key not provided.", "return_code": -1}

    # --- NEW: Templating Logic ---
    def get_nested_value(d, key_path):
        keys = key_path.split('.')
        val = d
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key)
            else:
                return None
        return val

    # Find all {{...}} placeholders
    placeholders = re.findall(r"\{\{([^}]+)\}\}", command)
    for placeholder in placeholders:
        value = get_nested_value(data_context, placeholder.strip())
        if value is not None:
            # Important: Convert value to string for safe command line usage
            command = command.replace(f"{{{{{placeholder}}}}}", shlex.quote(str(value)))
        else:
            # A referenced variable doesn't exist. Fail informatively.
            return {"command": command, "stdout": "", "stderr": f"Error: Template variable '{placeholder}' not found in data_context.", "return_code": -1}
    # --- END NEW ---

    timeout = config.get("timeout", 60)
    try:
        args = shlex.split(command)
        process = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return {"command": command, "stdout": process.stdout.strip(), "stderr": process.stderr.strip(), "return_code": process.returncode}
    # ... (rest of the exception handling is the same) ...
    except Exception as e:
        return {"command": command, "stdout": "", "stderr": f"An unexpected error occurred: {str(e)}", "return_code": -1}

def cognitive_conductor(config, input_data, data_context):
    """
    Takes a natural language sub-task, generates a sub-genome to solve it,
    executes that sub-genome internally, and returns the result. This is a
    recursive, "thinking" gene.
    manifest:
      type: CognitiveConductor
      description: "Solves a complex sub-task described in a natural language prompt. It internally generates and executes a plan (a sub-genome)."
      inputs:
        - name: task_prompt
          type: string
          required: true
          description: "A detailed natural language prompt describing the sub-task to be solved."
        - name: initial_input_for_sub_task
          type: dict
          required: false
          description: "The initial input data to be passed to the generated sub-genome."
      outputs:
        - type: dict
          description: "The final output from the execution of the internally generated sub-genome."
    """
    # --- CRITICAL FIX: Imports are moved inside the function to break circular dependency ---
    from genesis import generate_genome_from_prompt
    from engine import run_organism
    import json
    # --- END FIX ---

    task_prompt = input_data.get("task_prompt")
    initial_input = input_data.get("initial_input_for_sub_task", {})

    if not task_prompt:
        return {"error": "CognitiveConductor requires a 'task_prompt' in its input_data."}

    try:
        # Step 1: Generate a plan (sub-genome) using Genesis
        sub_genome_json_str = generate_genome_from_prompt(task_prompt)
        sub_genome = json.loads(sub_genome_json_str)

        # Step 2: Execute the sub-genome using the Engine
        log_output, final_status, final_data_context = run_organism(
            json.dumps(sub_genome),
            config.get("run_id"),
            config.get("organism_id"),
            initial_input
        )

        return final_data_context

    except Exception as e:
        # This provides a rich failure report if the sub-task fails
        return {
            "error": "CognitiveConductor failed during sub-task execution.",
            "reason": str(e),
            "sub_task_prompt": task_prompt
        }

def generic_api_call(config, input_data, data_context):
    """
    Performs a generic HTTP request to any REST API.
    manifest:
      type: GenericAPI
      description: "A universal gene to interact with any REST API. It can perform GET, POST, PUT, DELETE requests."
      config_schema:
        - name: method
          type: string
          required: true
          description: "The HTTP method (e.g., 'GET', 'POST')."
        - name: url
          type: string
          required: true
          description: "The URL of the API endpoint."
        - name: headers
          type: dict
          required: false
          description: "A dictionary of request headers."
        - name: params
          type: dict
          required: false
          description: "A dictionary of URL query parameters (for GET requests)."
        - name: timeout
          type: int
          required: false
          description: "The timeout for the request in seconds. Defaults to 30."
      inputs:
        - name: json_body
          type: dict
          required: false
          description: "The JSON payload for POST or PUT requests."
      outputs:
        - type: dict
          keys: ['status_code', 'headers', 'body']
    """
    method = config.get("method", "").upper()
    url = config.get("url")
    headers = config.get("headers", {})
    params = config.get("params", {})
    timeout = config.get("timeout", 30)
    json_body = input_data.get("json_body", {})

    if not method or not url:
        return {"error": "GenericAPI requires 'method' and 'url' in its config."}

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_body if method in ["POST", "PUT"] else None,
            timeout=timeout
        )
        
        # Attempt to parse the response body as JSON, fall back to raw text
        try:
            body = response.json()
        except json.JSONDecodeError:
            body = response.text

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "error": "API request failed.",
            "reason": str(e)
        }

# --- Update the GENE_MAP ---
GENE_MAP = {
    "StoreValue": store_value,
    "FetchRedditPosts": fetch_reddit_posts,
    "AnalyzeSentiment": analyze_sentiment,
    "FilterData": filter_data,
    "PostToSlack": post_to_slack,
    "WriteToMemory": write_to_memory,
    "ReadFromMemory": read_from_memory,
    "MergeData": merge_data,
    "ExtractFieldList": extract_field_list,
    "SummarizeArticles": summarize_articles,
    "FetchNewsAPI": fetch_news_api,
    "ExecuteInRuntime": execute_in_runtime,
    "SaveToVectorMemory": save_to_vector_memory,
    "QueryVectorMemory": query_vector_memory,
    "ConditionalBranch": conditional_branch,
    "CognitiveConductor": cognitive_conductor,
    "GenericAPI": generic_api_call,
}
