"""
Unit tests for OpenAPI 3.1 to 3.0.3 down-conversion
"""
import pytest
from scripts.generate_openapi import convert_to_v30


def test_convert_null_anyof():
    schema = {
        "anyOf": [
            {"type": "string"},
            {"type": "null"}
        ]
    }
    converted = convert_to_v30(schema)
    assert converted == {"type": "string", "nullable": True}


def test_convert_null_type_array():
    schema = {
        "type": ["string", "null"]
    }
    converted = convert_to_v30(schema)
    assert converted == {"type": "string", "nullable": True}


def test_recursive_conversion():
    schema = {
        "properties": {
            "field1": {
                "anyOf": [{"type": "integer"}, {"type": "null"}]
            },
            "field2": {
                "items": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "type": "array"
            }
        }
    }
    converted = convert_to_v30(schema)
    assert converted["properties"]["field1"] == {"type": "integer", "nullable": True}
    assert converted["properties"]["field2"]["items"] == {"type": "string", "nullable": True}


def test_multiple_types_with_null():
    schema = {
        "anyOf": [
            {"type": "string"},
            {"type": "integer"},
            {"type": "null"}
        ]
    }
    converted = convert_to_v30(schema)
    assert "anyOf" in converted
    assert len(converted["anyOf"]) == 2
    assert converted["nullable"] is True
