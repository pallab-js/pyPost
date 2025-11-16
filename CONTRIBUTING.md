# Contributing to pyPost

Thank you for your interest in contributing to pyPost! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites
- Python 3.9 or higher
- Git

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/pypost.git
   cd pypost
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"  # For development dependencies
   ```

4. Run the application:
   ```bash
   python main.py
   ```

## Development Workflow

### Code Style
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write descriptive commit messages

### Testing
- Write tests for new features
- Ensure all tests pass before submitting PRs
- Run tests with: `pytest`

### Code Quality
- Use `black` for code formatting
- Use `isort` for import sorting
- Use `flake8` for linting

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass
6. Format code: `black . && isort .`
7. Commit your changes: `git commit -m "Add feature description"`
8. Push to your fork: `git push origin feature/your-feature-name`
9. Create a Pull Request

## Reporting Issues

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Any relevant error messages

## Feature Requests

Feature requests are welcome! Please provide:
- Clear description of the feature
- Use case or problem it solves
- Any relevant examples or mockups

## License

By contributing to pyPost, you agree that your contributions will be licensed under the MIT License.