# TextCAD Studio - Complete Repository Guide

## 📂 Repository Structure

```
TextCAD-Studio/
│
├── 📄 README.md                    # Main project documentation
├── 📄 QUICKSTART.md                # 5-minute setup guide
├── 📄 INSTALLATION.md              # Detailed installation instructions
├── 📄 API.md                       # API endpoint documentation
├── 📄 ARCHITECTURE.md              # System design and architecture
├── 📄 CONTRIBUTING.md              # Contribution guidelines
│
├── 🐳 docker-compose.yml           # Docker orchestration
├── 🐳 Dockerfile.backend           # Backend container
├── 🐳 Dockerfile.frontend          # Frontend container
│
├── 📁 backend/                     # Python FastAPI Backend
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── routes/
│   │   │   ├── chat.py             # Chat/generation endpoints
│   │   │   ├── cad.py              # CAD operations endpoints
│   │   │   └── export.py           # Export endpoints
│   │   ├── services/
│   │   │   ├── llm_engine.py       # LLM integration (Gemini/OpenAI/Claude)
│   │   │   └── cad_generator.py    # CAD code generation & execution
│   │   └── __init__.py
│   │
│   ├── requirements.txt             # Python dependencies
│   └── .env.example                 # Environment template
│
├── 📁 frontend/                    # React + TypeScript Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx       # Main chat interface
│   │   │   ├── ModelViewer.tsx      # 3D model visualization
│   │   │   ├── ParameterPanel.tsx   # Parameter editor
│   │   │   ├── MessageBubble.tsx    # Chat message component
│   │   │   └── CodeBlock.tsx        # Code display component
│   │   │
│   │   ├── services/
│   │   │   └── api.ts               # API client
│   │   │
│   │   ├── store/
│   │   │   └── cadStore.ts          # Zustand state management
│   │   │
│   │   ├── App.tsx                  # Main app component
│   │   ├── main.tsx                 # Entry point
│   │   └── index.css                # Global styles
│   │
│   ├── index.html                   # HTML template
│   ├── vite.config.ts               # Vite configuration
│   ├── tsconfig.json                # TypeScript config
│   ├── tailwind.config.js           # Tailwind CSS config
│   ├── package.json                 # Node dependencies
│   └── postcss.config.js            # PostCSS config
│
├── 📁 examples/                    # Example Scripts
│   ├── 01_simple_cube.py            # Basic cube generation
│   ├── 02_container_with_holes.py   # Complex part with features
│   ├── 03_parametric_box.py         # Parametric model
│   └── api_client_example.py        # API usage examples
│
├── 📁 demo/                        # Live Demo
│   └── index.html                   # Standalone demo page
│
└── 📁 docs/                        # Additional Documentation
    ├── SCREENSHOTS.md               # Generated model examples
    ├── API_EXAMPLES.md              # API usage examples
    └── TROUBLESHOOTING.md           # Common issues & solutions
```

## 🚀 Quick Navigation

### For Users
1. **Start Here**: [QUICKSTART.md](./QUICKSTART.md) (5 minutes)
2. **Detailed Setup**: [INSTALLATION.md](./INSTALLATION.md)
3. **Try Examples**: [examples/](./examples/)
4. **Live Demo**: [demo/index.html](./demo/index.html) (No setup needed!)

### For Developers
1. **Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md)
2. **API Docs**: [API.md](./API.md)
3. **Contributing**: [CONTRIBUTING.md](./CONTRIBUTING.md)
4. **Backend Code**: [backend/](./backend/)
5. **Frontend Code**: [frontend/src/](./frontend/src/)

## 🎯 Key Features by Component

### Backend (Python)
- ✅ FastAPI REST API
- ✅ Multi-LLM support (Gemini, OpenAI, Claude)
- ✅ CAD code generation
- ✅ Safe code execution
- ✅ STL/STEP export
- ✅ WebSocket support

### Frontend (React)
- ✅ Real-time chat interface
- ✅ 3D model visualization (Three.js)
- ✅ Parameter editor
- ✅ Code display
- ✅ Export controls
- ✅ Responsive design

### Integrations
- ✅ CadQuery (Python CAD)
- ✅ Build123d (Modern CAD)
- ✅ Gemini API (Advanced LLM)
- ✅ OpenAI GPT-4 (Alternative)
- ✅ Claude API (Alternative)
- ✅ Three.js (3D Web)

## 📊 File Counts

```
Backend:     9 Python files
Frontend:   11 TypeScript/React files
Docs:       10+ Documentation files
Examples:    4 Example scripts
Config:      5 Configuration files
Total:       39+ files
```

## 🔧 Development Workflow

### Adding a New Feature

1. **Backend Feature**:
   ```bash
   cd backend
   # Create in app/services/
   # Create route in app/routes/
   # Test with pytest
   ```

2. **Frontend Feature**:
   ```bash
   cd frontend
   # Create component in src/components/
   # Add to store if needed
   # Test with npm test
   ```

3. **Both**:
   - Update [API.md](./API.md)
   - Update [ARCHITECTURE.md](./ARCHITECTURE.md)
   - Add examples

## 📋 File Size Reference

| Component | Files | Size |
|-----------|-------|------|
| Backend Core | 3 | ~800 lines |
| Frontend Components | 5 | ~1200 lines |
| Services | 2 | ~400 lines |
| Configs | 6 | ~200 lines |
| Docs | 6 | ~2000 lines |
| Examples | 4 | ~300 lines |

## 🎓 Learning Path

### Beginner
1. Read [QUICKSTART.md](./QUICKSTART.md)
2. Run the [demo/index.html](./demo/index.html)
3. Try local setup
4. Run examples

### Intermediate
1. Read [INSTALLATION.md](./INSTALLATION.md)
2. Explore [API.md](./API.md)
3. Study frontend code
4. Study backend code

### Advanced
1. Read [ARCHITECTURE.md](./ARCHITECTURE.md)
2. Modify services
3. Add new features
4. Contribute improvements

## 🔗 Important Links

### Documentation
- [README.md](./README.md) - Overview
- [QUICKSTART.md](./QUICKSTART.md) - Fast setup
- [INSTALLATION.md](./INSTALLATION.md) - Detailed setup
- [API.md](./API.md) - API reference
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Dev guidelines

### Resources
- [CadQuery Docs](https://cadquery.readthedocs.io/)
- [Build123d Docs](https://github.com/gumyr/build123d)
- [Gemini API](https://ai.google.dev/)
- [OpenAI API](https://platform.openai.com/)
- [Three.js Docs](https://threejs.org/docs/)

### External Examples
- [examples/](./examples/) - Local Python examples
- [demo/index.html](./demo/index.html) - Standalone web demo
- [GitHub Issues](https://github.com/ktraghuram2/TextCAD-Studio/issues) - Real use cases

## ✨ Tips

1. **First Time?**
   - Start with [QUICKSTART.md](./QUICKSTART.md)
   - Try [demo/index.html](./demo/index.html) first

2. **Want to Contribute?**
   - Read [CONTRIBUTING.md](./CONTRIBUTING.md)
   - Check GitHub Issues
   - Fork and create PR

3. **Having Issues?**
   - Check [INSTALLATION.md](./INSTALLATION.md)
   - Search [GitHub Issues](https://github.com/ktraghuram2/TextCAD-Studio/issues)
   - Open new issue with details

4. **Want More Features?**
   - Read [ARCHITECTURE.md](./ARCHITECTURE.md)
   - Check [Roadmap](./README.md#-roadmap)
   - Discuss in GitHub Discussions

## 📞 Support

- **Questions**: [GitHub Discussions](https://github.com/ktraghuram2/TextCAD-Studio/discussions)
- **Bugs**: [GitHub Issues](https://github.com/ktraghuram2/TextCAD-Studio/issues)
- **Contributions**: [CONTRIBUTING.md](./CONTRIBUTING.md)

---

**Happy coding! 🚀**
