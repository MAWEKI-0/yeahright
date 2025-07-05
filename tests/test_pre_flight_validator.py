import json
import pytest
from app import validate_genome
import copy

# A baseline valid genome for testing
BASE_VALID_GENOME = {
    "name": "Test Organism",
    "trigger": {
        "type": "schedule",
        "cron": "*/5 * * * *"
    },
    "genes": [
        {
            "id": "gene_1",
            "type": "FetchRedditPosts",
            "config": {
                "subreddit": "testing"
            },
            "output_as": "reddit_posts"
        },
        {
            "id": "gene_2",
            "type": "FilterData",
            "input_from": "reddit_posts",
            "config": {
                "field": "title",
                "condition": "contains",
                "value": "test"
            }
        }
    ]
}

@pytest.fixture
def valid_genome():
    """Provides a fresh, deep copy of the base valid genome for each test."""
    return copy.deepcopy(BASE_VALID_GENOME)


def test_validator_valid_genome(valid_genome):
    """A syntactically perfect Genome should produce zero validation errors."""
    genome_str = json.dumps(valid_genome)
    errors = validate_genome(genome_str)
    assert len(errors) == 0, f"Valid genome produced unexpected errors: {errors}"

def test_validator_invalid_json():
    """A non-parseable JSON string should fail validation."""
    genome_str = '{"name": "Test", "genes": [}'
    errors = validate_genome(genome_str)
    assert len(errors) > 0
    assert "Invalid Genome JSON format" in errors[0]

def test_validator_missing_required_keys(valid_genome):
    """A Genome with missing top-level keys should fail."""
    # Missing 'name'
    genome_dict = valid_genome
    del genome_dict["name"]
    errors = validate_genome(json.dumps(genome_dict))
    assert "must have a 'name'" in errors[0]

    # Missing 'genes' - get a fresh copy first
    genome_dict = copy.deepcopy(BASE_VALID_GENOME)
    del genome_dict["genes"]
    errors = validate_genome(json.dumps(genome_dict))
    assert "must have a 'genes'" in errors[0]

def test_validator_incorrect_types(valid_genome):
    """A Genome with incorrect data types for keys should fail."""
    # 'genes' should be a list, not a dict
    genome_dict = valid_genome
    genome_dict["genes"] = {"not": "a list"}
    errors = validate_genome(json.dumps(genome_dict))
    assert "'genes' (list)" in errors[0]

def test_validator_unknown_gene_type(valid_genome):
    """A Genome referencing a non-existent Gene type should fail."""
    genome_dict = valid_genome
    genome_dict["genes"][0]["type"] = "ThisGeneDoesNotExist"
    errors = validate_genome(json.dumps(genome_dict))
    assert "uses unknown type 'ThisGeneDoesNotExist'" in errors[0]

def test_validator_duplicate_gene_id(valid_genome):
    """A Genome with a duplicate gene 'id' should fail."""
    genome_dict = valid_genome
    genome_dict["genes"][1]["id"] = "gene_1" # Duplicate ID
    errors = validate_genome(json.dumps(genome_dict))
    assert "Duplicate gene ID 'gene_1'" in errors[0]

def test_validator_missing_gene_id(valid_genome):
    """A gene definition missing its 'id' should fail."""
    genome_dict = valid_genome
    del genome_dict["genes"][0]["id"]
    errors = validate_genome(json.dumps(genome_dict))
    assert "must have an 'id'" in errors[0]
