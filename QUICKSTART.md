# TextCAD Studio - Quick Start Guide 🚀

Welcome to **TextCAD Studio**! This guide will get you up and running in 5 minutes.

## What is TextCAD Studio?

TextCAD Studio is an AI-powered platform that converts your natural language descriptions into precise 3D CAD models. Just describe what you want, and watch it come to life!

**Example:**
- Input: "Create a cylindrical container 50mm diameter, 100mm tall with 2mm walls"
- Output: ✅ 3D CAD model ready to export

## Prerequisites

✅ Python 3.10 or higher  
✅ Node.js 18 or higher  
✅ An API key from:
  - [Google Gemini](https://makersuite.google.com/app/apikey) (Recommended)
  - [OpenAI](https://platform.openai.com/api-keys)
  - [Anthropic Claude](https://console.anthropic.com/)

## Installation (5 Minutes)

### Step 1: Clone Repository

```bash
git clone https://github.com/ktraghuram2/TextCAD-Studio.git
cd TextCAD-Studio
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API Key
export GEMINI_API_KEY="your-api-key-here"
# OR for OpenAI:
export OPENAI_API_KEY="your-api-key-here"

# Start server (runs on http://localhost:8000)
python -m uvicorn app.main:app --reload
```

### Step 3: Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Start dev server (runs on http://localhost:3000)
npm run dev
```

### Step 4: Open in Browser

```
http://localhost:3000
```

> **🌐 Published Cloud Version (No local setup required):**
> - **Live Web Studio:** [https://ktraghuram2.github.io/TextCAD-Studio/](https://ktraghuram2.github.io/TextCAD-Studio/)
> - **Direct Demo Link:** [https://ktraghuram2.github.io/TextCAD-Studio/demo/live.html](https://ktraghuram2.github.io/TextCAD-Studio/demo/live.html)

✅ **Done!** You're ready to create CAD models.

## Quick Examples

### Example 1: Simple Cube (30 seconds)

```
Chat: "Create a 10mm cube"
Result: 3D cube ready to export
```

### Example 2: Container with Holes (1 minute)

```
Chat: "Design a cylinder 50mm diameter, 100mm tall, with 2mm wall thickness and 5 holes on the bottom"
Result: Complex 3D model with features
```

### Example 3: Iterative Design (2 minutes)

```
Chat 1: "Create a gear with 20 teeth"
Chat 2: "Make it larger, 40mm diameter"
Chat 3: "Add a 5mm bore hole in the center"
Result: Refined gear model after 3 iterations
```

## Using Docker (Simpler Alternative)

```bash
# Start both backend and frontend with one command
docker-compose up

# Then open http://localhost:3000
```

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.10+

# Check if port 8000 is in use
lsof -i :8000

# Install missing dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend won't load
```bash
# Clear npm cache
npm cache clean --force
npm install

# Check Node version
node --version  # Should be 18+
```

### CAD generation fails
- Verify API key is correct
- Check you have API credits available
- Keep prompts clear and specific

## Next Steps

📖 Read full [Installation Guide](./INSTALLATION.md)  
📚 Explore [API Documentation](./API.md)  
🏗️ Learn the [Architecture](./ARCHITECTURE.md)  
💡 Try [Examples](./examples/)  
🤝 Check [Contributing Guide](./CONTRIBUTING.md)  

## Key Features

✨ **Natural Language Processing** - Describe in plain English  
🤖 **Multi-LLM Support** - Use Gemini, OpenAI, Claude, or local Ollama  
🎨 **Real-time 3D Viewer** - Instant visualization  
💾 **Export Support** - STL, STEP, DXF formats  
🔄 **Iterative Design** - Refine models through conversation  
⚡ **Fast Generation** - Most models ready in seconds  

## API Preview

```bash
# Generate CAD from text
curl -X POST http://localhost:8000/api/chat/generate \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a 10mm cube"}'

# View API documentation
http://localhost:8000/docs
```

## Tips for Best Results

✅ **Be Specific** - "10mm cube" not "small box"  
✅ **Use Units** - Always include mm, cm, inches  
✅ **Describe Features** - Holes, patterns, textures  
✅ **Iterate** - Refine progressively  
✅ **Check Preview** - Verify before exporting  

## Limitations

⚠️ Generated code is sandboxed for safety  
⚠️ 30-second timeout per model  
⚠️ Maximum model size: 100MB  
⚠️ API rate limits may apply  

## Support

❓ Questions? [Open a Discussion](https://github.com/ktraghuram2/TextCAD-Studio/discussions)  
🐛 Found a bug? [Report an Issue](https://github.com/ktraghuram2/TextCAD-Studio/issues)  
📧 Contact: Check GitHub profile  

## License

MIT License - See [LICENSE](./LICENSE) file

## Community

Starred this project? ⭐ Let us know!  
Built something cool? Share it with us! 🚀  

---

**Happy designing! 🎨**
