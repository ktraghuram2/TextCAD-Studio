# 🎨 TextCAD Studio - Live Interactive Web Demo

## ⚡ Try it Now - No Installation Needed!

### **[👉 OPEN LIVE DEMO HERE 👈](./live.html)**

Just paste your API key and start generating CAD models instantly!

## 🔑 How to Get Your API Key

### Option 1: Google Gemini (Recommended - Free Tier)
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key
4. Paste it in the demo

### Option 2: OpenAI GPT-4
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create new API key
3. Copy and paste in demo

### Option 3: Claude by Anthropic
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create API key
3. Use in demo

## 🎯 Features

✨ **Real-time 3D Generation**
- Watch models generate instantly
- Interactive 3D viewer with rotation/zoom
- Wireframe mode
- Auto-rotate toggle

🚀 **Multiple LLM Support**
- Google Gemini (Free tier available)
- OpenAI GPT-4
- Claude API

💬 **Smart Chat Interface**
- Natural language descriptions
- Pre-built examples
- Code display and copy
- Generation history

🎮 **Interactive Controls**
- Rotate, zoom, pan the model
- Toggle wireframe view
- Reset view
- Auto-rotate option

## 🚀 Quick Start

1. **Open**: [./live.html](./live.html)
2. **Select**: Your LLM provider (top bar)
3. **Paste**: Your API key
4. **Click**: "💾 Save Key"
5. **Describe**: Your CAD model
6. **Click**: "🚀 Generate"
7. **View**: 3D model renders instantly!

## 📝 Example Prompts

### Simple
- "Create a 10mm cube"
- "Make a cylinder 30mm diameter, 50mm height"
- "Design a sphere 25mm radius"

### Intermediate
- "Box 100x80x50mm with 2mm walls"
- "Cylinder with a 5mm bore hole in the center"
- "Sphere with a flat base"

### Advanced
- "Create a hex bolt M10 with 15mm length"
- "Design a parametric box with rounded corners"
- "Make a gear with 20 teeth and 30mm diameter"

## 🎮 3D Viewer Controls

| Action | Control |
|--------|----------|
| Rotate | Left click + drag |
| Zoom | Scroll wheel |
| Pan | Right click + drag |
| Reset | Click "↻ Reset" button |
| Wireframe | Click "⊞ Wireframe" |
| Auto-Rotate | Click "🔄 Rotate" |

## 💾 Features

### Code Display
- AI-generated Python code
- Copy button for easy sharing
- Syntax-aware display

### Model Export
- Download STL files (local setup)
- Export to STEP format
- Perfect for 3D printing

### Responsive Design
- Desktop optimized (1600px+)
- Works on tablets
- Mobile-friendly interface

## ⚠️ Important Notes

### API Keys
- Keys are **stored locally** in your browser
- Never shared with us
- Uses browser's localStorage
- You can clear anytime

### Limitations
- Demo mode uses simulated models
- For full features, clone the repo and run locally
- Local setup allows custom model generation
- API calls count toward your account usage

### Free Options
- **Gemini**: 60 calls/minute free
- **OpenAI**: Use trial credits
- **Claude**: Free tier available

## 🔧 Advanced Setup (Full Features)

For complete local setup with real CAD generation:

```bash
git clone https://github.com/ktraghuram2/TextCAD-Studio.git
cd TextCAD-Studio

# Backend
cd backend
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"
python -m uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Then visit `http://localhost:3000`

## 📊 Supported Models

The demo supports:
- ✅ Cube/Box
- ✅ Cylinder
- ✅ Sphere
- ✅ Cone
- ✅ Torus
- ✅ Complex parametric models (local setup)

## 🐛 Troubleshooting

### "API Key not working"
- Verify key format
- Check API quotas
- Try different LLM provider

### "Model not generating"
- Describe more clearly
- Include dimensions
- Try example prompts

### "3D Viewer not showing"
- Check browser compatibility
- Enable WebGL
- Clear browser cache
- Try different browser

## 🎓 Learning Resources

- [QUICKSTART.md](../QUICKSTART.md) - 5-minute setup
- [INSTALLATION.md](../INSTALLATION.md) - Full installation
- [API.md](../API.md) - API documentation
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design
- [Examples](../examples/) - Code examples

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/ktraghuram2/TextCAD-Studio/issues)
- **Questions**: [GitHub Discussions](https://github.com/ktraghuram2/TextCAD-Studio/discussions)
- **Features**: Create an issue with "enhancement" label

## 📄 License

MIT License - Free to use and modify

---

**[🎨 START CREATING NOW! →](./live.html)**
