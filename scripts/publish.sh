#!/bin/bash
# Script para publicar toonpy en PyPI

set -e  # Salir si hay errores

echo "🧹 Limpiando builds anteriores..."
rm -rf dist/ build/ *.egg-info/ toonpy.egg-info/

echo "✅ Ejecutando tests..."
pytest tests/ -v

echo "📦 Construyendo paquete..."
python -m build

echo "🔍 Verificando paquete..."
twine check dist/*

echo ""
echo "✅ Paquete listo para publicar!"
echo ""
echo "Para publicar en TestPyPI:"
echo "  twine upload --repository testpypi dist/*"
echo ""
echo "Para publicar en PyPI:"
echo "  twine upload dist/*"
echo ""

