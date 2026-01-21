# Publishing to PyPI

This document provides instructions for publishing the `omarchy-mcp` package to PyPI.

## Prerequisites

1. Install build tools:
   ```bash
   pip install build twine
   ```

2. Create a PyPI account at https://pypi.org/account/register/

3. Generate an API token at https://pypi.org/manage/account/token/

## Building the Package

1. Build the distribution packages:
   ```bash
   python -m build
   ```

   This will create:
   - `dist/omarchy_mcp-0.1.0-py3-none-any.whl` (wheel)
   - `dist/omarchy_mcp-0.1.0.tar.gz` (source distribution)

## Publishing to PyPI

### Test PyPI (Recommended First)

1. Upload to Test PyPI:
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

2. Install from Test PyPI to verify:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ omarchy-mcp
   ```

### Production PyPI

1. Upload to PyPI:
   ```bash
   python -m twine upload dist/*
   ```

2. Install from PyPI:
   ```bash
   pip install omarchy-mcp
   ```

## Versioning

To release a new version:

1. Update the version in `pyproject.toml`
2. Update the version in `src/omarchy_mcp/__init__.py`
3. Commit the changes
4. Create a git tag:
   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```
5. Rebuild and publish

## Verification

After publishing, verify the package:

1. Check the PyPI page: https://pypi.org/project/omarchy-mcp/
2. Install in a clean environment and test:
   ```bash
   python -m venv test_env
   source test_env/bin/activate  # On Windows: test_env\Scripts\activate
   pip install omarchy-mcp
   omarchy-mcp --version
   ```
