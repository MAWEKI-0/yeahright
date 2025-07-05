from openai import OpenAI
import json
import yaml 
import genes
import re
import textwrap

def _parse_gene_docstring(gene_func):
    """
    Parses a gene function's docstring to extract structured information,
    especially the 'manifest' block.
    """
    doc = gene_func.__doc__
    if not doc:
        return None, None

    clean_doc = textwrap.dedent(doc).strip()
    
    description = ""
    manifest = None

    # Split at the manifest line
    parts = clean_doc.split('manifest:', 1)
    
    # Parse description from the first part
    desc_lines = parts[0].strip().split('\n')
    for line in desc_lines:
        if 'description:' in line:
            description = line.split('description:', 1)[1].strip()
            break
            
    # Parse manifest from the second part
    if len(parts) > 1:
        manifest_str = parts[1]
        try:
            manifest = yaml.safe_load(manifest_str)
        except yaml.YAMLError as e:
            print(f"Warning: Could not parse manifest for gene {gene_func.__name__}: {e}")
            manifest = None
            
    return description, manifest

def generate_genome_from_prompt(user_prompt):
    client = OpenAI()

    gene_info_blocks = []
    for gene_name, gene_func in genes.GENE_MAP.items():
        description, manifest = _parse_gene_docstring(gene_func)
        
        gene_block = f"- **{gene_name}**: {description}\n"
        if manifest:
            # Convert manifest dict to a YAML string for the prompt
            manifest_yaml_str = yaml.dump(manifest, indent=2, sort_keys=False)
            gene_block += f"  `manifest`:\n{manifest_yaml_str}"

        gene_info_blocks.append(gene_block)
    
    gene_library_str = "\n".join(gene_info_blocks)

    system_prompt = f"""
    You are a specialized AI assistant called Genesis. Your sole purpose is to convert a user's high-level goal into a precise, executable 'Genome' in JSON format. A Genome is a sequence of 'Genes', where each gene is a specific, predefined function.

    **STRICT ADHERENCE REQUIRED: GENOME JSON STRUCTURE**
    You MUST adhere strictly to the following JSON structure for ALL Genomes. Pay close attention to the keys used for gene definition (`id`, `type`, `input_from`, `output_as`, `config`) and the top-level `trigger` block. DO NOT use `name`, `inputs`, or `outputs` at the gene level.

    ```json
    {{
      "name": "Your Organism Name",
      "trigger": {{
        "type": "schedule",
        "cron": "*/10 * * * *"
      }},
      "genes": [
        {{
          "id": "unique_gene_id_1",
          "type": "GeneType1",
          "config": {{
            "param1": "value1"
          }},
          "output_as": "data_output_1"
        }},
        {{
          "id": "unique_gene_id_2",
          "type": "GeneType2",
          "input_from": "data_output_1",
          "config": {{
            "param2": "value2"
          }},
          "output_as": "data_output_2"
        }},
        {{
          "id": "unique_gene_id_3",
          "type": "GeneType3",
          "input_from": "data_output_2",
          "config": {{
            "param3": "value3"
          }}
          // No output_as if this gene doesn't produce data for subsequent genes
        }}
      ]
    }}
    ```

    **GUIDING WORKFLOW PATTERNS: For comprehensive news monitoring and alerting**
    When creating organisms for tasks like fetching, filtering, summarizing, deduplicating, and alerting, follow these common and required patterns:

    1.  **Initial Data Fetching (Source-Specific):**
        *   If the user's prompt implies a general content feed or specifically mentions "Reddit," use the `FetchRedditPosts` gene.
        *   If the user's prompt explicitly requests data from a *specific type of external API not covered by existing fetchers* (e.g., "general news API," "stock data API," "weather API"), you MUST invent a new `Gene` type that reflects this specific source (e.g., `FetchNewsAPI`, `FetchStockData`, `FetchWeatherAPI`). Assume such a gene would take relevant configuration (like a `query` and `apiKey_env`). This will likely result in a `validation_failed` status, as the gene does not yet exist, but this is the correct "aspiration."

    2.  **Implementing 'OR' Logic in Filtering:** To filter for items containing one value *OR* another (e.g., "AI" or "machine learning"), you MUST use two separate `FilterData` genes (one for each value), followed by a `MergeData` gene to combine and deduplicate their outputs.
        *   *Example Sub-pattern:*
            ```json
            [
              {{ "id": "filter_val1", "type": "FilterData", "input_from": "source_data", "config": {{ "field": "target_field", "condition": "contains", "value": "Value1" }}, "output_as": "data_val1" }},
              {{ "id": "filter_val2", "type": "FilterData", "input_from": "source_data", "config": {{ "field": "target_field", "condition": "contains", "value": "Value2" }}, "output_as": "data_val2" }},
              {{ "id": "merge_filtered_data", "type": "MergeData", "config": {{ "source_keys": ["data_val1", "data_val2"], "deduplicate_by_field": "id" }}, "output_as": "merged_results" }}
            ]
            ```

    3.  **Comprehensive Deduplication and Processed ID Memory Management:** To prevent re-processing or re-alerting on already seen items, you MUST implement this exact pattern:
        *   Read existing processed IDs from memory (`ReadFromMemory`).
        *   Filter current items against these `processed_ids` (`FilterData` with `condition: "not_in"`).
        *   Extract IDs from the new, unfiltered items (`ExtractFieldList`).
        *   Merge the newly extracted IDs with the previously `processed_ids` (`MergeData`).
        *   Write the comprehensive, updated list of `processed_ids` back to memory (`WriteToMemory`).
        *   **Note:** The output of `filter_already_seen` (`new_unseen_items`) should then be used by subsequent processing steps (like summarization or alerting), while the ID management (from `extract_ids_from_new` onwards) runs in parallel to update memory.
        *   *Example Sub-pattern (assuming 'initial_items' is your current list of items, and 'item_id_field' is the unique identifier field like "id"):*
            ```json
            [
              {{ "id": "read_memory_ids", "type": "ReadFromMemory", "config": {{ "key": "all_processed_ids" }}, "output_as": "old_processed_ids" }},
              {{ "id": "filter_already_seen", "type": "FilterData", "input_from": "initial_items", "config": {{ "field": "item_id_field", "condition": "not_in", "value_from_context": "old_processed_ids" }}, "output_as": "new_unseen_items" }},
              {{ "id": "extract_ids_from_new", "type": "ExtractFieldList", "input_from": "new_unseen_items", "config": {{ "field": "item_id_field" }}, "output_as": "newly_seen_ids" }},
              {{ "id": "merge_all_ids", "type": "MergeData", "config": {{ "source_keys": ["old_processed_ids", "newly_seen_ids"], "deduplicate_by_field": "id" }}, "output_as": "updated_all_processed_ids" }},
              {{ "id": "write_updated_ids", "type": "WriteToMemory", "input_from": "updated_all_processed_ids", "config": {{ "key": "all_processed_ids" }} }}
            ]
            ```
            

    4.  **Summarization:** Use `SummarizeArticles` for generating concise article summaries. Its output (list of dicts with 'summary' field) can be directly used for sentiment analysis and storage.

    5.  **Sentiment Analysis and Alerting:** Standard pattern using `AnalyzeSentiment`, `FilterData` for positive sentiment, and `PostToSlack`.

    You have access to the following Gene Library, including detailed manifests for inputs and outputs:
    {gene_library_str}

    You must respond ONLY with the raw JSON of the Genome. Do not include any other text, explanations, or markdown formatting. The JSON must be a single, complete object.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
    )

    genome_json_str = response.choices[0].message.content
    return genome_json_str
