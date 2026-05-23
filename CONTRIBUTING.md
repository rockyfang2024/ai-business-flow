# Contributing to AI Business Flow

Thank you for your interest in contributing! 🎉

## How to Contribute

### 🐛 Bug Reports

- Open an issue with a clear title and description
- Include your environment (Python version, Node.js version, OS)
- Include steps to reproduce the bug
- If possible, provide error logs or screenshots

### 💡 Feature Requests

- Open an issue and describe the feature
- Explain why it would be valuable to the community
- Provide use cases if possible

### 🛠️ Pull Requests

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone git@github.com:YOUR_USERNAME/ai-business-flow.git
   cd ai-business-flow
   ```
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Install dependencies**:
   ```bash
   cd backend && pip install -r requirements.txt
   cd ../frontend && npm install
   ```
5. **Make your changes** — follow the existing code style
6. **Test** your changes:
   ```bash
   # Run backend tests
   cd backend && python -m pytest

   # Run frontend type check
   cd frontend && npx tsc --noEmit
   ```
7. **Commit** with a clear message:
   ```bash
   git commit -m "feat: add new feature"
   ```
8. **Push and open a PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

- **Python**: Follow PEP 8, use `ruff` for formatting
- **TypeScript**: Use the existing patterns in the codebase, run `npx tsc --noEmit` before committing

## Commit Message Convention

```
feat:     new feature
fix:      bug fix
docs:     documentation only
refactor: code refactoring (no feature change)
test:     adding or updating tests
chore:    maintenance tasks
```

## Project Structure

See [README.md](README.md) for the full project structure.

## Questions?

- Open a [GitHub Discussion](https://github.com/rockyfang2024/ai-business-flow/discussions)
- Open an issue with the `question` label

---

## 🚀 Quick Setup for Development

```bash
git clone git@github.com:rockyfang2024/ai-business-flow.git
cd ai-business-flow
git clone https://github.com/rockyfang2024/business-flow-skill.git ../business-flow-skill
./start.sh
```