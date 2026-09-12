# TextCAD Studio API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, no authentication is required. In production, add JWT tokens.

## Endpoints

### Chat & Generation

#### POST /api/chat/generate

Generate CAD model from natural language description.

**Request:**
```json
{
  "message": "Create a 10mm cube",
  "design_history": ["previous_code_1", "previous_code_2"],
  "model_context": {"last_dimensions": "10mm"}
}
```

**Response:**
```json
{
  "status": "success",
  "message": "CAD model generated successfully",
  "cad_code": "from build123d import *\nwith BuildPart() as bp:\n    Box(10, 10, 10)\nresult = bp.part",
  "model_preview": "base64_encoded_stl",
  "design_id": "2024-09-12T12:15:30.123Z"
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid request
- `500`: Server error

#### WebSocket /ws/chat

Real-time chat with streaming model updates.

**Connect:**
```javascript
const socket = io('http://localhost:8000/ws/chat');

socket.on('message', (data) => {
  console.log(data);
});

socket.emit('send', { message: 'Create a cube' });
```

### CAD Operations

#### POST /api/cad/generate-from-code

Generate model directly from Python code.

**Request:**
```json
{
  "code": "from build123d import *\nwith BuildPart() as bp:\n    Box(10, 10, 10)\nresult = bp.part",
  "parameters": {"size": 10}
}
```

**Response:**
```json
{
  "status": "success",
  "model_preview": "base64_encoded_stl",
  "info": {
    "type": "BuildPart",
    "vertices": 8,
    "faces": 6
  }
}
```

#### POST /api/cad/validate-code

Validate CAD code syntax without execution.

**Request:**
```json
{
  "code": "from build123d import *\nBox(10, 10, 10)"
}
```

**Response:**
```json
{
  "valid": true,
  "error": null
}
```

### Export

#### POST /api/export/stl

Export model to STL format.

**Request:**
```json
{
  "model_id": "design_123",
  "filename": "my_model.stl"
}
```

**Response:**
Binary STL file

#### POST /api/export/step

Export model to STEP format.

**Request:**
```json
{
  "model_id": "design_123",
  "filename": "my_model.step"
}
```

**Response:**
Binary STEP file

### Utility

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

#### GET /

API information.

**Response:**
```json
{
  "name": "TextCAD-Studio API",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "chat": "/api/chat/generate",
    "cad": "/api/cad/generate",
    "export": "/api/export/stl",
    "docs": "/docs"
  }
}
```

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message explaining what went wrong"
}
```

### Common Errors

| Error | Status | Cause | Fix |
|-------|--------|-------|-----|
| `Invalid request` | 400 | Malformed JSON | Check request format |
| `CAD execution timeout` | 400 | Code took too long | Simplify model |
| `No model created` | 400 | Code didn't create object | Verify code validity |
| `API rate limit exceeded` | 429 | Too many requests | Wait and retry |
| `Server error` | 500 | Internal server error | Check logs |

## Rate Limiting

Current limits:
- 100 requests per minute per IP
- 10 concurrent generations per user

## Pagination

List endpoints support pagination:

```
?page=1&limit=10
```

## Filtering

Supported filters:
```
?status=success&created_after=2024-09-12
```

## Code Examples

### Python

```python
import requests
import json

url = "http://localhost:8000/api/chat/generate"
payload = {
    "message": "Create a cube 20mm on each side",
    "design_history": []
}

response = requests.post(url, json=payload)
data = response.json()

print(f"Status: {data['status']}")
print(f"CAD Code:\n{data['cad_code']}")
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8000/api/chat/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Create a cube 20mm on each side',
    design_history: []
  })
});

const data = await response.json();
console.log(data.cad_code);
```

### cURL

```bash
curl -X POST http://localhost:8000/api/chat/generate \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a cube 20mm on each side",
    "design_history": []
  }'
```

## OpenAPI/Swagger

Interactive API documentation available at:
```
http://localhost:8000/docs
```

JSON schema:
```
http://localhost:8000/openapi.json
```
