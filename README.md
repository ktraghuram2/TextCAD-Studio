# TextCAD-Studio 🎨

An AI-powered **Text-to-CAD generation platform** that converts natural language descriptions into precise 3D CAD models. Features a real-time chat interface with live 3D visualization.

---

### 🌐 Live CAD Studio & 3D Renderer URLs
> **Access the CAD Studio & Renderer directly in your browser:**
> - **Published Cloud Web App (GitHub Pages):** [https://ktraghuram2.github.io/TextCAD-Studio/](https://ktraghuram2.github.io/TextCAD-Studio/)
> - **Direct Live Demo Endpoint:** [https://ktraghuram2.github.io/TextCAD-Studio/demo/live.html](https://ktraghuram2.github.io/TextCAD-Studio/demo/live.html)
> - **Localhost Dev URL (When running locally):** [http://localhost:3000](http://localhost:3000) (or `http://127.0.0.1:3000`)

---

## 🚀 Features

- **Natural Language Processing**: Describe your CAD model in plain English
- **Multi-LLM Support**: Gemini, OpenAI GPT-4, Claude, Ollama (local)
- **CAD Code Generation**: Automatic CadQuery/Build123d Python code generation
- **Real-time 3D Visualization**: See your model rendered instantly with Three.js
- **Chat Interface**: Iterative refinement through natural conversation
- **Parametric Design**: Edit and adjust generated models interactively
- **Export Support**: STL, STEP, DXF file formats

## 🏗️ Architecture

```
TextCAD-Studio/
├── backend/              # Python FastAPI server
│   ├── llm_engine/      # Multi-LLM integration layer
│   ├── cad_generator/   # CadQuery/Build123d code generation
│   ├── cad_executor/    # Safe CAD code execution
│   └── api/             # FastAPI endpoints
├── frontend/            # React + TypeScript web UI
│   ├── components/      # Chat, 3D viewer, model panel
│   ├── services/        # API client, WebGL rendering
│   └── styles/          # Tailwind CSS styling
└── docs/                # Documentation & examples
```

## 🛠️ Tech Stack

**Backend:**
- FastAPI (Python web framework)
- CadQuery/Build123d (CAD modeling)
- Gemini API / OpenAI API / Claude API
- OpenCASCADE (geometry engine)

**Frontend:**
- React 18 + TypeScript
- Three.js (3D visualization)
- Tailwind CSS (styling)
- Socket.io (real-time updates)

## 📦 Key Dependencies

Integrated from:
- **CadQuery** (github.com/CadQuery/cadquery) - Python CAD scripting
- **Build123d** (github.com/gumyr/build123d) - Modern CAD programming
- **Text2CAD** (github.com/SadilKhan/Text2CAD) - NeurIPS'24 research
- **jupyter-cadquery** - 3D visualization in web
- **Gemini API** - Advanced LLM capabilities

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- API Key (Gemini, OpenAI, or Claude)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"  # Optional

python -m uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

Open http://localhost:3000

> **🚀 Live Web App (No installation required):**  
> You can also run the published CAD renderer directly in your browser:  
> - **Published Studio:** [https://ktraghuram2.github.io/TextCAD-Studio/](https://ktraghuram2.github.io/TextCAD-Studio/)  
> - **Direct Live URL:** [https://ktraghuram2.github.io/TextCAD-Studio/demo/live.html](https://ktraghuram2.github.io/TextCAD-Studio/demo/live.html)


## 💬 Usage Examples

### Example 1: Simple Box
```
"Create a 10mm cube"
```

### Example 2: Iterative Design
```
User: "Create a gear with 20 teeth"
AI: [Generates gear model]
User: "Make it bigger, 40mm diameter"
AI: [Adjusts parameters and regenerates]
User: "Add a 5mm bore hole in the center"
AI: [Adds hole and updates model]
```

## 📡 API Endpoints

```
POST /api/generate     - Generate CAD from text
POST /api/refine       - Refine existing design
GET  /api/preview      - Get STL preview
POST /api/export       - Export to STEP/STL/DXF
WS   /ws/chat          - WebSocket for real-time chat
```

## 🔐 Environment Variables

```env
# LLM Configuration
GEMINI_API_KEY=sk-...
OPENAI_API_KEY=sk-...
CLAUDE_API_KEY=sk-...

# Server
FASTAPI_ENV=development
CORS_ORIGINS=http://localhost:3000

# CAD Settings
MAX_EXECUTION_TIME=30
MAX_MODEL_SIZE=100000000  # bytes
```

## 🎯 Roadmap

- [ ] Advanced constraint solving
- [ ] Assembly generation
- [ ] Mesh optimization
- [ ] Collaborative design workspace
- [ ] CAD-to-text reverse engineering
- [ ] Integration with FreeCAD/Blender
- [ ] ML-based design suggestion

## 📚 References

- [CadQuery Documentation](https://cadquery.readthedocs.io/)
- [Build123d Guide](https://github.com/gumyr/build123d)
- [Text2CAD Paper](https://arxiv.org/abs/2405.14795)
- [Gemini API Docs](https://ai.google.dev/)

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md

## 💡 Support

Open an issue on GitHub for bugs/features requests
