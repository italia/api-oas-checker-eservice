"""
Generate OpenAPI schema for OAS Checker e-service
Supports both modern 3.1.0 and legacy 3.0.3 formats.
"""
import json
import yaml
import sys
import copy
from pathlib import Path

# Add parent directory to path to import main
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app


def fix_integer_formats(obj):
    """Recursively add format: int32 to integer types without format"""
    if isinstance(obj, dict):
        if obj.get("type") == "integer" and "format" not in obj:
            obj["format"] = "int32"
        
        # Special case for anyOf/oneOf/allOf lists
        for key in ["anyOf", "oneOf", "allOf"]:
            if key in obj and isinstance(obj[key], list):
                for item in obj[key]:
                    fix_integer_formats(item)
        
        for key, value in obj.items():
            if key not in ["anyOf", "oneOf", "allOf"]:
                fix_integer_formats(value)
    elif isinstance(obj, list):
        for item in obj:
            fix_integer_formats(item)


def convert_to_v30(obj):
    """
    Recursively converts OpenAPI 3.1.0 constructs to 3.0.3:
    - anyOf: [{type: X}, {type: 'null'}] -> type: X, nullable: true
    - type: [X, 'null'] -> type: X, nullable: true
    """
    if not isinstance(obj, (dict, list)):
        return obj

    if isinstance(obj, list):
        return [convert_to_v30(item) for item in obj]

    if isinstance(obj, dict):
        if "$ref" in obj:
            # In 3.0.x, $ref does not allow siblings.
            return {"$ref": obj["$ref"]}
        
        new_obj = {}
        for k, v in obj.items():
            # Handle anyOf with null
            if k == "anyOf" and isinstance(v, list):
                has_null = any(isinstance(item, dict) and item.get("type") == "null" for item in v)
                non_null_types = [item for item in v if not (isinstance(item, dict) and item.get("type") == "null")]
                
                if has_null and len(non_null_types) == 1:
                    # Convert to single type + nullable: true
                    inner_type = convert_to_v30(non_null_types[0])
                    if isinstance(inner_type, dict):
                        new_obj.update(inner_type)
                        new_obj["nullable"] = True
                        continue
                elif has_null and len(non_null_types) > 1:
                    # Multiple types + null -> keep anyOf but convert internal items and add nullable
                    new_obj["anyOf"] = [convert_to_v30(item) for item in non_null_types]
                    new_obj["nullable"] = True
                    continue

            # Handle type as array [string, 'null']
            if k == "type" and isinstance(v, list):
                if "null" in v:
                    real_types = [t for t in v if t != "null"]
                    if len(real_types) == 1:
                        new_obj["type"] = real_types[0]
                        new_obj["nullable"] = True
                        continue
                    else:
                        new_obj["type"] = real_types
                        new_obj["nullable"] = True
                        continue

            new_obj[k] = convert_to_v30(v)
        
        return new_obj


def generate_openapi_schema(output_dir: str = "."):
    """
    Generate OpenAPI schemas in 3.1.0 and 3.0.3 formats
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Get Base Schema (3.1.0)
    openapi_31 = app.openapi()

    # Add global tags
    openapi_31["tags"] = [
        {"name": "Validation", "description": "Operations related to OAS validation"},
        {"name": "Rulesets", "description": "Operations related to Spectral rulesets"},
        {"name": "Status", "description": "Service status and health check"}
    ]

    # Add custom metadata
    info = openapi_31["info"]
    info["summary"] = "Servizio di validazione OpenAPI"
    info["x-summary"] = "Servizio di validazione OpenAPI"
    info["termsOfService"] = "https://example.com/terms"
    info["x-api-id"] = "oas-checker-eservice"
    info["contact"] = {
        "name": "API Support",
        "email": "support@example.com"
    }
    info["license"] = {
        "name": "CC0 1.0 Universal",
        "url": "https://creativecommons.org/publicdomain/zero/1.0/"
    }

    # Fix integer formats project-wide
    fix_integer_formats(openapi_31)
    
    # Mark localhost as sandbox
    for server in openapi_31.get("servers", []):
        if "localhost" in server["url"]:
            server["x-sandbox"] = True

    # Ensure Problem schema is in components/schemas
    if "Problem" not in openapi_31.get("components", {}).get("schemas", {}):
        from models.schemas import Problem
        problem_schema = Problem.model_json_schema()
        if "title" in problem_schema: del problem_schema["title"]
        openapi_31.setdefault("components", {}).setdefault("schemas", {})["Problem"] = problem_schema
        fix_integer_formats(openapi_31["components"]["schemas"]["Problem"])

    # RFC 7807 Cleanup for 3.1.0
    for path_item in openapi_31.get("paths", {}).values():
        for operation in path_item.values():
            responses = operation.get("responses", {})
            for status_code, response in responses.items():
                content = response.get("content", {})
                if int(status_code) >= 400 or (status_code == "200" and "Status" in operation.get("tags", [])):
                    if "application/problem+json" in content and "application/json" in content:
                        del content["application/json"]

    # --- SAVE 3.1.0 ---
    with open(output_path / "openapi.json", "w", encoding="utf-8") as f:
        json.dump(openapi_31, f, indent=2, ensure_ascii=False)
    with open(output_path / "openapi.yaml", "w", encoding="utf-8") as f:
        yaml.dump(openapi_31, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
    print("✓ Generated OpenAPI 3.1.0: openapi.json, openapi.yaml")

    # 2. CREATE 3.0.3 LEGACY VERSION
    openapi_30 = copy.deepcopy(openapi_31)
    openapi_30["openapi"] = "3.0.3"
    
    # Remove summary from info (not allowed in 3.0.x)
    if "summary" in openapi_30["info"]:
        del openapi_30["info"]["summary"]
    
    # Convert nulls
    openapi_30 = convert_to_v30(openapi_30)

    # --- SAVE 3.0.3 ---
    with open(output_path / "openapi_v3.json", "w", encoding="utf-8") as f:
        json.dump(openapi_30, f, indent=2, ensure_ascii=False)
    with open(output_path / "openapi_v3.yaml", "w", encoding="utf-8") as f:
        yaml.dump(openapi_30, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
    print("✓ Generated OpenAPI 3.0.3 (Legacy): openapi_v3.json, openapi_v3.yaml")


if __name__ == "__main__":
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print("Generating OpenAPI schemas...")
    generate_openapi_schema(output_dir)