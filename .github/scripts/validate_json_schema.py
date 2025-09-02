#!/usr/bin/env python3
"""
JSON Schema Validation Script for Copilot Feature JSON files.

This script validates generated JSON files against a predefined schema,
creating a basic schema if none exists.
"""

import json
import jsonschema
import sys
from pathlib import Path


def validate_file(json_file, schema_file):
    """Validate a JSON file against a schema file."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        with open(schema_file, 'r') as f:
            schema = json.load(f)
        
        jsonschema.validate(data, schema)
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error loading files: {str(e)}"


def create_basic_schema(schema_file):
    """Create a basic schema if none exists."""
    basic_schema = {
        "type": "object",
        "required": ["metadata", "features"],
        "properties": {
            "metadata": {
                "type": "object",
                "required": ["platform", "lastUpdated", "generatedBy", "feedSources"],
                "properties": {
                    "platform": {"type": "string"},
                    "lastUpdated": {"type": "string"},
                    "generatedBy": {"type": "string"},
                    "feedSources": {"type": "array", "items": {"type": "string"}}
                }
            },
            "features": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "featureCapability", "category", "firstIntroduced", 
                        "currentStatus", "latestUpdate", "keyMilestones", 
                        "sourceLinks", "detectionDate", "lastModified"
                    ],
                    "properties": {
                        "featureCapability": {"type": "string"},
                        "category": {"type": "string"},
                        "firstIntroduced": {"type": "string"},
                        "currentStatus": {"type": "string"},
                        "latestUpdate": {"type": "string"},
                        "keyMilestones": {"type": "string"},
                        "sourceLinks": {"type": "array"},
                        "detectionDate": {"type": "string"},
                        "lastModified": {"type": "string"}
                    }
                }
            }
        }
    }
    
    # Create directory and write schema
    Path(schema_file).parent.mkdir(parents=True, exist_ok=True)
    with open(schema_file, 'w') as f:
        json.dump(basic_schema, f, indent=2)
    
    print(f"✅ Created basic schema: {schema_file}")


def main():
    """Main validation function."""
    print("🔍 Validating JSON files against schema...")
    
    # Define schema file path
    schema_file = ".github/schemas/copilot-feature-schema.json"
    
    # Check if schema file exists, create if not
    if not Path(schema_file).exists():
        print(f"⚠️  Schema file not found: {schema_file}")
        print("Creating basic schema for validation...")
        create_basic_schema(schema_file)
    
    # Define files to validate
    files_to_validate = [
        ("copilot-ide-features.json", "IDE Features"),
        ("copilot-platform-features.json", "Platform Features")
    ]
    
    all_valid = True
    errors = []
    
    # Validate each file
    for json_file, description in files_to_validate:
        if Path(json_file).exists():
            valid, error = validate_file(json_file, schema_file)
            if valid:
                print(f"✅ {description}: Valid JSON schema")
            else:
                print(f"❌ {description}: Schema validation failed")
                print(f"   Error: {error}")
                errors.append(f"{description}: {error}")
                all_valid = False
        else:
            print(f"❌ {json_file} not found")
            errors.append(f"{json_file} not found")
            all_valid = False
    
    # Output results
    if all_valid:
        print("🎉 All JSON files passed schema validation!")
        return 0
    else:
        print("💥 Schema validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
