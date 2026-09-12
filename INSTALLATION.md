# Getting Started with TextCAD Studio

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ktraghuram2/TextCAD-Studio.git
cd TextCAD-Studio
```

### 2. Set Up Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
cp .env.example .env
# Edit .env and add your API keys:
# GEMINI_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here (optional)

# Start backend server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at `http://localhost:8000`

### 3. Set Up Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file
echo "REACT_APP_API_URL=http://localhost:8000" > .env

# Start development server
npm run dev
```

Frontend runs at `http://localhost:3000`

> **🌐 Alternatively, access the online CAD renderer:**
> - **Live Web App:** [https://ktraghuram2.github.io/TextCAD-Studio/](https://ktraghuram2.github.io/TextCAD-Studio/)
> - **Direct Live Demo:** [https://ktraghuram2.github.io/TextCAD-Studio/demo/live.html](https://ktraghuram2.github.io/TextCAD-Studio/demo/live.html)

## Docker Setup (Optional)

### Using Docker Compose

```bash
# From root directory
docker-compose up -d
```

This starts both backend and frontend automatically.

## API Keys Setup

### Google Gemini API

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to `.env`: `GEMINI_API_KEY=your-key`

### OpenAI API

1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create new API key
3. Add to `.env`: `OPENAI_API_KEY=your-key`

### Claude API

1. Get key from [Anthropic Console](https://console.anthropic.com/)
2. Add to `.env`: `CLAUDE_API_KEY=your-key`

## Running Examples

### Example 1: Simple Cube

```
User Input: "Create a 10mm cube"

Generated Code:
from build123d import *

with BuildPart() as bp:
    Box(10, 10, 10)

result = bp.part
```

### Example 2: Cylindrical Container

```
User Input: "Design a cylindrical container with 50mm outer diameter, 100mm height, 2mm wall thickness"

Generated Code:
from build123d import *

with BuildPart() as bp:
    Cylinder(radius=25, height=100)
    with BuildPart(mode=Mode.SUBTRACT):
        Cylinder(radius=23, height=98)

result = bp.part
```

### Example 3: Gear

```
User Input: "Create a spur gear with 20 teeth, 30mm diameter"

Generated Code:
from build123d import *
from build123d.examples.gear import create_spur_gear

result = create_spur_gear(
    teeth=20,
    pitch_diameter=30,
    face_width=10,
    pressure_angle=20
)
```

## Troubleshooting

### Backend Won't Start

```bash
# Check Python version
python --version  # Should be 3.10+

# Verify dependencies
pip list | grep -E "fastapi|cadquery"

# Check if port 8000 is in use
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

### Frontend Won't Connect

1. Check backend is running: `curl http://localhost:8000`
2. Verify CORS settings in `.env`
3. Clear browser cache and reload

### CAD Generation Fails

1. Check API key is valid
2. Verify API rate limits
3. Check model timeout: `MAX_EXECUTION_TIME=30`

## Development Tips

### Enable Debug Mode

```env
DEBUG=true
FASTAPI_ENV=development
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Generate CAD
curl -X POST http://localhost:8000/api/chat/generate \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a cube"}'
```

### View API Documentation

Visit `http://localhost:8000/docs` for interactive API docs (Swagger UI)

## Performance Optimization

### Backend Optimization

1. **Increase workers** (production):
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
   ```

2. **Cache frequently used models**:
   - Edit `CADGenerator` to implement caching

3. **Parallel execution**:
   - Use async/await for concurrent requests

### Frontend Optimization

1. **Code splitting**:
   ```bash
   npm run build
   ```

2. **Optimize 3D viewer**:
   - Reduce polygon count for large models
   - Use LOD (Level of Detail) techniques

## Next Steps

1. Explore the [API Documentation](./API.md)
2. Check [Examples](./examples/)
3. Read [Contributing Guide](./CONTRIBUTING.md)
4. Join our [Discussions](https://github.com/ktraghuram2/TextCAD-Studio/discussions)

## Getting Help

- **Issues**: [Report bugs](https://github.com/ktraghuram2/TextCAD-Studio/issues)
- **Discussions**: [Ask questions](https://github.com/ktraghuram2/TextCAD-Studio/discussions)
- **Docs**: [Full documentation](./docs/)
