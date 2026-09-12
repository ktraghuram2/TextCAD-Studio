# TextCAD Studio - Architecture & Design

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React + Three.js)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐        │
│  │  Chat Panel  │  │ 3D Viewer    │  │  Parameters    │        │
│  └──────────────┘  └──────────────┘  └────────────────┘        │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              API Routes & WebSocket                  │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │            LLM Engine (Gemini/OpenAI/Claude)         │      │
│  │  - Prompt engineering                                │      │
│  │  - Response parsing                                  │      │
│  │  - Error handling                                    │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │          CAD Generator & Executor                    │      │
│  │  - Code generation from LLM output                   │      │
│  │  - Safe execution with sandboxing                    │      │
│  │  - STL/STEP export                                   │      │
│  └──────────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │        CAD Libraries Integration                     │      │
│  │  - Build123d    - CadQuery    - OpenCASCADE          │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Text-to-CAD Generation Flow

```
1. User Input
   └─→ "Create a cube 10mm"

2. Frontend
   └─→ Send to API: /api/chat/generate

3. Backend - API Handler
   └─→ Parse request

4. LLM Engine
   ├─→ Create prompt template
   ├─→ Add design history context
   ├─→ Call Gemini/OpenAI API
   └─→ Get CAD code response

5. CAD Generator
   ├─→ Clean and validate code
   ├─→ Extract imports
   └─→ Pass to executor

6. CAD Executor
   ├─→ Create sandbox environment
   ├─→ Execute code with timeout
   ├─→ Capture model object
   └─→ Return success/error

7. Model Processing
   ├─→ Convert to mesh (STL format)
   ├─→ Encode to base64
   └─→ Create preview

8. Response
   ├─→ Status: success
   ├─→ CAD Code
   ├─→ Model Preview (base64 STL)
   └─→ Design ID

9. Frontend Display
   ├─→ Show chat message
   ├─→ Render 3D model
   └─→ Display parameters
```

## Component Interaction

### Backend Components

**LLMEngine**
- Manages LLM provider selection
- Handles API communication
- Implements prompt engineering
- Caches responses

**CADGenerator**
- Orchestrates CAD generation
- Manages executor lifecycle
- Handles export formats
- Implements caching

**CADExecutor**
- Executes generated Python code
- Manages sandboxed environment
- Implements timeout/size limits
- Handles errors safely

**API Routes**
- `/api/chat/generate` - Main endpoint
- `/api/cad/generate-from-code` - Direct code execution
- `/api/export/stl` - Export to STL
- `/api/export/step` - Export to STEP

### Frontend Components

**ChatWindow**
- User message input
- Message history display
- Real-time updates via WebSocket
- Loading states

**ModelViewer**
- 3D model visualization using Three.js
- Orbit controls for interaction
- Lighting and shadows
- Export functionality

**ParameterPanel**
- Display editable parameters
- Real-time parameter updates
- Model refresh on parameter change

## Database Schema (Future)

```sql
TABLE users
├── id (UUID)
├── email (String)
├── created_at (DateTime)
└── updated_at (DateTime)

TABLE designs
├── id (UUID)
├── user_id (FK)
├── name (String)
├── description (Text)
├── code (Text)
├── preview (Blob)
├── status (Enum: pending, success, error)
├── created_at (DateTime)
└── updated_at (DateTime)

TABLE design_versions
├── id (UUID)
├── design_id (FK)
├── version (Int)
├── code (Text)
├── timestamp (DateTime)
└── llm_model (String)

TABLE exports
├── id (UUID)
├── design_id (FK)
├── format (Enum: stl, step, dxf)
├── file_path (String)
├── created_at (DateTime)
└── updated_at (DateTime)
```

## Security Considerations

### Code Execution Safety

1. **Sandboxing**
   - Execute in isolated namespace
   - Whitelist allowed imports
   - Restrict file system access

2. **Resource Limits**
   - Timeout: 30 seconds default
   - Memory limit: Check during execution
   - Model size limit: 100MB

3. **Input Validation**
   - Sanitize user prompts
   - Validate generated code before execution
   - Check for suspicious patterns

### API Security

1. **Authentication** (Future)
   - JWT tokens
   - OAuth2 integration

2. **Rate Limiting**
   - Per-IP rate limits
   - Per-user concurrency limits

3. **CORS Configuration**
   - Whitelist allowed origins
   - Validate content-type headers

## Performance Optimization

### Caching Strategy

```python
# Cache identical prompts
if prompt_hash in cache:
    return cached_result

# Cache LLM responses
llm_response_cache.set(prompt_hash, response)

# Cache generated models
model_cache.set(code_hash, model)
```

### Async Processing

- Use FastAPI async endpoints
- Implement concurrent model generation
- Stream large file exports

### Frontend Optimization

- Code splitting with Vite
- Lazy load Three.js components
- Memoize expensive computations
- Virtual scrolling for chat history

## Scalability Considerations

### Horizontal Scaling

1. **Load Balancing**
   - Nginx reverse proxy
   - Round-robin distribution

2. **Worker Pool**
   - Gunicorn with multiple workers
   - Redis for distributed caching

3. **Message Queue**
   - Celery for async tasks
   - Long-running exports

### Vertical Scaling

1. **Resource Allocation**
   - Docker memory limits
   - CPU quotas

2. **Optimization**
   - Model caching
   - LLM response caching
   - Database indexing

## Testing Strategy

### Unit Tests
- LLM engine mock responses
- Code validation logic
- Export functions

### Integration Tests
- End-to-end API flows
- CAD generation pipeline
- Export with different formats

### Performance Tests
- Load testing with multiple concurrent requests
- Memory profiling
- Timeout handling

## Deployment Architecture

### Development
```
Docker Compose
├── Backend (uvicorn - reload mode)
├── Frontend (Vite dev server)
└── Volume mounts for hot reload
```

### Production
```
Kubernetes / Docker Swarm
├── Backend Service
│   ├── Multiple replicas
│   └── Resource limits
├── Frontend Service
│   ├── CDN for static files
│   └── Nginx proxy
├── Redis Cache
├── PostgreSQL Database
└── Monitoring (Prometheus/Grafana)
```
