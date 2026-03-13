"""
Generate OpenAPI schema for OAS Checker e-service
Supports both modern 3.1.0 and legacy 3.0.3 formats for all environments.
Organized in subdirectories by environment and version.
"""
import json
import yaml
import sys
import copy
import shutil
from pathlib import Path

# Add parent directory to path to import main
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app


def fix_integer_formats(obj):
    """Recursively add format: int32 to integer types without format"""
    if isinstance(obj, dict):
        if obj.get("type") == "integer" and "format" not in obj:
            obj["format"] = "int32"
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
    """Recursively converts OpenAPI 3.1.0 constructs to 3.0.3"""
    if not isinstance(obj, (dict, list)):
        return obj
    if isinstance(obj, list):
        return [convert_to_v30(item) for item in obj]
    if isinstance(obj, dict):
        if "$ref" in obj: return {"$ref": obj["$ref"]}
        new_obj = {}
        for k, v in obj.items():
            # Remove properties not supported in 3.0.3
            if k == "contentMediaType":
                new_obj["format"] = "binary"
                continue
            if k == "contentEncoding":
                continue
                
            if k == "anyOf" and isinstance(v, list):
                has_null = any(isinstance(item, dict) and item.get("type") == "null" for item in v)
                non_null_types = [item for item in v if not (isinstance(item, dict) and item.get("type") == "null")]
                if has_null and len(non_null_types) == 1:
                    inner_type = convert_to_v30(non_null_types[0])
                    if isinstance(inner_type, dict):
                        new_obj.update(inner_type)
                        new_obj["nullable"] = True
                        continue
                elif has_null and len(non_null_types) > 1:
                    new_obj["anyOf"] = [convert_to_v30(item) for item in non_null_types]
                    new_obj["nullable"] = True
                    continue
            if k == "type" and isinstance(v, list):
                if "null" in v:
                    real_types = [t for t in v if t != "null"]
                    if len(real_types) == 1:
                        new_obj["type"] = real_types[0]
                        new_obj["nullable"] = True
                        continue
            new_obj[k] = convert_to_v30(v)
        return new_obj


def save_openapi_variants(schema_31, env_name, output_path):
    """Save variants in nested directories: openapi/<env>/v<ver>/openapi.<ext>"""
    # 1. Save v3.1
    v31_dir = output_path / env_name / "v3.1"
    v31_dir.mkdir(parents=True, exist_ok=True)
    with open(v31_dir / "openapi.json", "w", encoding="utf-8") as f:
        json.dump(schema_31, f, indent=2, ensure_ascii=False)
    with open(v31_dir / "openapi.yaml", "w", encoding="utf-8") as f:
        yaml.dump(schema_31, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
    
    # 2. Create and Save v3.0
    schema_30 = copy.deepcopy(schema_31)
    schema_30["openapi"] = "3.0.3"
    if "summary" in schema_30["info"]: del schema_30["info"]["summary"]
    schema_30 = convert_to_v30(schema_30)
    
    v30_dir = output_path / env_name / "v3.0"
    v30_dir.mkdir(parents=True, exist_ok=True)
    with open(v30_dir / "openapi.json", "w", encoding="utf-8") as f:
        json.dump(schema_30, f, indent=2, ensure_ascii=False)
    with open(v30_dir / "openapi.yaml", "w", encoding="utf-8") as f:
        yaml.dump(schema_30, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
    
    print(f"✓ Generated all variants for environment: {env_name}")


def generate_openapi_schema(output_dir: str = "openapi"):
    output_path = Path(output_dir)
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    openapi_base = app.openapi()
    openapi_base["tags"] = [
        {"name": "Validation", "description": "Operations related to OAS validation"},
        {"name": "Rulesets", "description": "Operations related to Spectral rulesets"},
        {"name": "Status", "description": "Service status and health check"}
    ]

    info = openapi_base["info"]
    info["summary"] = "Servizio di validazione OpenAPI"
    info["x-summary"] = "Servizio di validazione OpenAPI"
    info["termsOfService"] = "https://github.com/italia/api-oas-checker-eservice/blob/main/README.MD"
    info["x-api-id"] = "oas-checker-eservice"
    info["contact"] = {"name": "Dipartimento per la Trasformazione Digitale", "url": "https://github.com/italia/api-oas-checker-eservice"}
    info["license"] = {"name": "EUPL 1.2", "url": "https://github.com/italia/api-oas-checker-eservice/blob/main/LICENSE"}

    import config
    fix_integer_formats(openapi_base)
    problem_base_url = config.PROBLEM_BASE_URL
    
    if "Problem" not in openapi_base.get("components", {}).get("schemas", {}):
        from models.schemas import Problem
        problem_schema = Problem.model_json_schema()
        if "title" in problem_schema: del problem_schema["title"]
        openapi_base.setdefault("components", {}).setdefault("schemas", {})["Problem"] = problem_schema
        fix_integer_formats(openapi_base["components"]["schemas"]["Problem"])
    
    problem_schema = openapi_base["components"]["schemas"]["Problem"]
    problem_schema["properties"]["type"]["default"] = problem_base_url + "internal-error"
    if "example" in problem_schema: problem_schema["example"]["type"] = problem_base_url + "validation-not-found"

    for path_item in openapi_base.get("paths", {}).values():
        for operation in path_item.values():
            responses = operation.get("responses", {})
            for status_code, response in responses.items():
                content = response.get("content", {})
                if int(status_code) >= 400 or (status_code == "200" and "Status" in operation.get("tags", [])):
                    if "application/problem+json" in content and "application/json" in content: del content["application/json"]
                if "application/problem+json" in content:
                    prob_content = content["application/problem+json"]
                    if "examples" in prob_content:
                        for ex_val in prob_content["examples"].values():
                            if "value" in ex_val and "type" in ex_val["value"]:
                                type_map = {"400": "bad-request", "404": "not-found", "422": "validation-error", "429": "rate-limit-exceeded", "500": "internal-error"}
                                problem_type = type_map.get(status_code, "internal-error")
                                ex_val["value"]["type"] = problem_base_url + problem_type

    all_servers = [
        {"url": "https://api-oas-checker.innovazione.gov.it/govway/rest/in/DTD/api-oas-checker/v1", "description": "Produzione"},
        {"url": "https://uat-api-oas-checker.innovazione.gov.it/govway/rest/in/DTD/api-oas-checker/v1", "description": "Collaudo"},
        {"url": "https://att-api-oas-checker.innovazione.gov.it/govway/rest/in/DTD/api-oas-checker/v1", "description": "Attestazione"},
        {"url": "http://localhost:8000", "description": "Local Development Server", "x-sandbox": True}
    ]

    envs = {
        "full": all_servers,
        "produzione": [all_servers[0]],
        "collaudo": [all_servers[1]],
        "attestazione": [all_servers[2]]
    }
    
    for env_name, servers in envs.items():
        openapi_env = copy.deepcopy(openapi_base)
        openapi_env["servers"] = servers
        save_openapi_variants(openapi_env, env_name, output_path)


if __name__ == "__main__":
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "openapi"
    print(f"Generating OpenAPI variants in directory: {output_dir}...")
    generate_openapi_schema(output_dir)