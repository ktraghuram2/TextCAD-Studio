#!/usr/bin/env python3
"""
Example: API client usage
"""

import requests
import json
import base64
from pathlib import Path

API_URL = "http://localhost:8000"

def generate_cad_from_text(description: str):
    """
    Generate CAD model from text description using the API.
    """
    url = f"{API_URL}/api/chat/generate"
    
    payload = {
        "message": description,
        "design_history": [],
        "model_context": {}
    }
    
    print(f"Generating CAD for: {description}")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"\nGenerated Code:\n{data['cad_code']}")
        
        # Save STL preview if available
        if data.get('model_preview'):
            stl_data = base64.b64decode(data['model_preview'])
            Path("output.stl").write_bytes(stl_data)
            print("\nModel saved to output.stl")
        
        return data
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

def execute_cad_code(code: str):
    """
    Execute CAD code directly.
    """
    url = f"{API_URL}/api/cad/generate-from-code"
    
    payload = {
        "code": code,
        "parameters": {}
    }
    
    print(f"Executing CAD code...")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Info: {data['info']}")
        return data
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

def validate_cad_code(code: str):
    """
    Validate CAD code syntax.
    """
    url = f"{API_URL}/api/cad/validate-code"
    
    payload = {
        "code": code
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data['valid']:
            print("✓ Code is valid")
        else:
            print(f"✗ Code error: {data['error']}")
        return data
    else:
        print(f"Error: {response.status_code}")
        return None

if __name__ == "__main__":
    # Example 1: Generate from text
    print("=" * 50)
    print("Example 1: Generate from text description")
    print("=" * 50)
    result = generate_cad_from_text("Create a 10mm cube")
    
    if result:
        # Example 2: Validate the generated code
        print("\n" + "=" * 50)
        print("Example 2: Validate generated code")
        print("=" * 50)
        validate_cad_code(result['cad_code'])
        
        # Example 3: Execute the code
        print("\n" + "=" * 50)
        print("Example 3: Execute the code")
        print("=" * 50)
        execute_cad_code(result['cad_code'])
