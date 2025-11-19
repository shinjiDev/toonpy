#!/bin/bash
# Script to publish toonpy on PyPI

set -e  # Exit on error

echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/ toonpy.egg-info/

echo "✅ Running tests..."
pytest tests/ -v

echo "📦 Building package..."
python -m build

echo "🔍 Checking package..."
twine check dist/*

echo ""
echo "✅ Package ready to publish!"
echo ""
echo "To publish on TestPyPI:"
echo "  twine upload --repository testpypi dist/*"
echo ""
echo "To publish on PyPI:"
echo "  twine upload dist/*"
echo ""

