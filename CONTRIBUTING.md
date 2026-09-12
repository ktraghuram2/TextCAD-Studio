# TextCAD Studio - Contribution Guide

## Code of Conduct

We are committed to providing a welcoming and inspiring community. Please read our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

Before submitting a bug report, check the issue list to ensure it hasn't been reported.

**Include:**
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Screenshots/logs if applicable
- Environment info (OS, Python version, etc.)

### Suggesting Features

**Include:**
- Clear use case
- Example scenarios
- Why it would be useful
- Possible implementation approach

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/your-username/TextCAD-Studio.git
   cd TextCAD-Studio
   git checkout -b feature/your-feature-name
   ```

2. **Set up development environment**
   ```bash
   # Backend
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Frontend
   cd ../frontend
   npm install
   ```

3. **Make your changes**
   - Follow existing code style
   - Add tests for new features
   - Update documentation

4. **Run tests**
   ```bash
   # Backend
   cd backend
   pytest
   pytest --cov=app tests/
   
   # Frontend
   cd frontend
   npm test
   npm run lint
   ```

5. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   # Use conventional commits: feat, fix, docs, style, refactor, test
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Open a Pull Request**
   - Title: Clear description of changes
   - Description: Why and what changed
   - Reference related issues
   - Screenshots for UI changes

## Development Guidelines

### Backend (Python)

```python
# Follow PEP 8 style guide
# Use type hints
# Write docstrings

def generate_cad(prompt: str, context: Dict[str, Any]) -> str:
    """
    Generate CAD code from natural language prompt.
    
    Args:
        prompt: User description of desired model
        context: Additional context information
        
    Returns:
        Generated Python CAD code as string
    """
    pass
```

### Frontend (TypeScript/React)

```typescript
// Use functional components with hooks
// Add proper TypeScript types
// Use descriptive component names

interface Props {
  message: string;
  onSend: (text: string) => void;
}

const ChatInput: React.FC<Props> = ({ message, onSend }) => {
  return <div>...</div>;
};
```

## Testing

### Backend Tests

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_llm_engine.py

# With coverage
pytest --cov=app tests/
```

### Frontend Tests

```bash
# Run tests
npm test

# Run linter
npm run lint

# Build check
npm run build
```

## Documentation

- Update README.md for major changes
- Add docstrings to all functions
- Include examples in code comments
- Keep CHANGELOG.md updated

## Project Structure

```
TextCAD-Studio/
├── backend/
│   ├── app/
│   │   ├── services/      # Business logic
│   │   ├── routes/        # API endpoints
│   │   └── main.py        # App entry point
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── services/      # API clients
│   │   ├── store/         # State management
│   │   └── App.tsx        # Main app
│   └── package.json
└── docs/
```

## Common Tasks

### Adding a New API Endpoint

1. Create route in `backend/app/routes/`
2. Add service logic in `backend/app/services/`
3. Write tests in `backend/tests/`
4. Update API.md

### Adding a New Component

1. Create component in `frontend/src/components/`
2. Add tests in `frontend/src/components/__tests__/`
3. Export from `frontend/src/components/index.ts`
4. Use in parent component

## Getting Help

- **Questions**: Open a discussion
- **Issues**: Check existing issues
- **Chat**: Join our Discord community

## Recognition

Contributors will be:
- Added to CONTRIBUTORS.md
- Mentioned in release notes
- Featured in community spotlights

Thank you for contributing to TextCAD Studio! 🚀
