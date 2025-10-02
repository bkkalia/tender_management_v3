# Contributing to Tender Management Utility

Thank you for your interest in contributing to Tender Management Utility! We welcome contributions from the community to help improve and enhance this project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Contributing Guidelines](#contributing-guidelines)
- [Testing](#testing)
- [Performance Testing](#performance-testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## 🤝 Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## 🚀 Getting Started

### Prerequisites

- Python 3.7 or higher
- Git
- Familiarity with Tkinter, pandas, and matplotlib

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/tender-management-utility.git
   cd tender-management-utility
   ```
3. Set up the upstream remote:
   ```bash
   git remote add upstream https://github.com/cloud84/tender-management-utility.git
   ```

## 🛠️ Development Setup

### Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies (if available)
pip install -r requirements-dev.txt
```

### Run the Application

```bash
python main.py
```

### Development Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the guidelines below

3. Test your changes thoroughly

4. Commit with clear, descriptive messages:
   ```bash
   git commit -m "feat: add new filtering capability for tender status"
   ```

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a Pull Request on GitHub

## 📁 Project Structure

```
tender-management-utility/
├── main.py                    # Application entry point
├── scripts/                   # Build and utility scripts
├── benchmark/                 # Performance testing
├── docs/                      # Documentation
├── tests/                     # Unit tests
├── tools/                     # Development tools
├── data/                      # Sample data files
├── config/                    # Configuration files
├── core/                      # Core business logic
├── ui/                        # User interface components
├── utils/                     # Utility functions
└── resources/                 # Static assets
```

## 📝 Contributing Guidelines

### Code Style

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused on single responsibilities
- Use type hints where appropriate

### Commit Messages

Use conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing related changes
- `chore`: Maintenance tasks

Examples:
```
feat(ui): add dark mode toggle to main window
fix(search): resolve case sensitivity issue in global search
docs(readme): update installation instructions
```

### Code Quality

- Write clear, readable code
- Add comments for complex logic
- Handle edge cases and errors gracefully
- Follow the existing code patterns
- Ensure backward compatibility

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_specific_feature.py

# Run with coverage
python -m pytest --cov=core --cov=ui tests/
```

### Writing Tests

- Place test files in the `tests/` directory
- Name test files with `test_` prefix
- Use descriptive test function names
- Test both positive and negative scenarios
- Mock external dependencies when appropriate

Example test structure:
```python
import pytest
from core.data_processor import DataProcessor

class TestDataProcessor:
    def test_load_excel_file_success(self):
        # Test successful Excel file loading
        pass

    def test_load_excel_file_invalid_format(self):
        # Test error handling for invalid files
        pass
```

## 📊 Performance Testing

### Running Benchmarks

```bash
# Run comprehensive benchmark suite
python benchmark/comprehensive_benchmark_suite.py

# Run specific benchmark
python benchmark/performance_test_demo.py

# Generate performance report
python scripts/compile_research_report.py
```

### Performance Guidelines

- Maintain or improve current performance benchmarks
- Profile code for bottlenecks before optimization
- Document performance impact of changes
- Consider memory usage in data processing operations

## 🔄 Submitting Changes

### Pull Request Process

1. **Update Documentation**: Ensure README, docstrings, and relevant docs are updated
2. **Add Tests**: Include tests for new features or bug fixes
3. **Update Changelog**: Add entry to `docs/CHANGELOG.md`
4. **Self Review**: Check your code meets the guidelines above
5. **Create PR**: Use the pull request template with clear description

### PR Template

```markdown
## Description
Brief description of the changes made

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing performed
- [ ] Performance benchmarks run

## Screenshots (if applicable)
Add screenshots of UI changes

## Additional Notes
Any additional context or considerations
```

## 🐛 Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. **Clear Title**: Describe the issue concisely
2. **Steps to Reproduce**: Detailed steps to reproduce the bug
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: OS, Python version, application version
6. **Screenshots/Logs**: If applicable
7. **Additional Context**: Any other relevant information

### Feature Requests

For feature requests, please include:

1. **Clear Title**: Describe the desired feature
2. **Problem Statement**: What problem does this solve?
3. **Proposed Solution**: How should it work?
4. **Alternatives Considered**: Other approaches you've thought of
5. **Additional Context**: Screenshots, mockups, or examples

## 🎯 Areas for Contribution

### High Priority
- Performance optimizations
- Bug fixes in data processing
- UI/UX improvements
- Additional export formats

### Medium Priority
- New visualization types
- Enhanced search capabilities
- Mobile responsiveness
- Internationalization

### Future Enhancements
- Web-based version
- API development
- Machine learning integration
- Cloud storage integration

## 📞 Getting Help

- **Documentation**: Check the [User Manual](HELP.md) first
- **Discussions**: Use [GitHub Discussions](https://github.com/cloud84/tender-management-utility/discussions) for questions
- **Issues**: Create detailed bug reports or feature requests

## 🙏 Recognition

Contributors will be recognized in:
- CHANGELOG.md for significant contributions
- GitHub repository contributors list
- Project documentation acknowledgments

Thank you for contributing to Tender Management Utility! 🚀
