# 📦 Guía para Publicar toonpy en PyPI

Esta guía te ayudará a publicar el paquete `toonpy` en PyPI (Python Package Index).

## 📋 Prerrequisitos

1. **Cuenta en PyPI**: 
   - Crea una cuenta en [PyPI](https://pypi.org/account/register/)
   - Crea una cuenta en [TestPyPI](https://test.pypi.org/account/register/) para pruebas

2. **Herramientas necesarias**:
   ```bash
   pip install --upgrade build twine
   ```

## 🔧 Paso 1: Preparar el Proyecto

### 1.1 Verificar `pyproject.toml`

Asegúrate de que `pyproject.toml` tenga toda la información correcta:
- ✅ Nombre del paquete: `toonpy`
- ✅ Versión: `0.1.0` (o la versión que quieras publicar)
- ✅ Descripción clara
- ✅ Autor con email
- ✅ URLs del repositorio
- ✅ Licencia
- ✅ Clasificadores apropiados

### 1.2 Verificar que los tests pasen

```bash
cd c:\proj\Python\toontools
pytest tests/ -v
```

### 1.3 Limpiar builds anteriores

```bash
# Eliminar builds anteriores
rm -rf dist/ build/ *.egg-info/
# O en Windows:
rmdir /s /q dist build *.egg-info
```

## 🧪 Paso 2: Probar en TestPyPI (Recomendado)

### 2.1 Generar los archivos de distribución

```bash
python -m build
```

Esto creará:
- `dist/toonpy-0.1.0.tar.gz` (source distribution)
- `dist/toonpy-0.1.0-py3-none-any.whl` (wheel)

### 2.2 Verificar el paquete

```bash
twine check dist/*
```

### 2.3 Subir a TestPyPI

```bash
twine upload --repository testpypi dist/*
```

Te pedirá:
- **Username**: Tu nombre de usuario de TestPyPI
- **Password**: Tu contraseña (o mejor, un API token)

### 2.4 Probar la instalación desde TestPyPI

```bash
pip install --index-url https://test.pypi.org/simple/ toonpy
```

Verifica que funciona:
```bash
python -c "import toonpy; print(toonpy.__version__)"
toonpy --help
```

## 🚀 Paso 3: Publicar en PyPI Real

### 3.1 Generar API Token (Recomendado)

1. Ve a [PyPI Account Settings](https://pypi.org/manage/account/)
2. Crea un **API token** con scope `project:toonpy`
3. Copia el token (solo se muestra una vez)

### 3.2 Subir a PyPI

```bash
twine upload dist/*
```

O usando el token:
```bash
twine upload --username __token__ --password pypi-<tu-token> dist/*
```

### 3.3 Verificar en PyPI

Visita: https://pypi.org/project/toonpy/

## 📝 Paso 4: Verificar la Instalación

```bash
# Instalar desde PyPI
pip install toonpy

# Verificar
python -c "import toonpy; print(toonpy.__version__)"
toonpy --help
```

## 🔄 Paso 5: Actualizar Versiones Futuras

Para publicar nuevas versiones:

1. **Actualizar la versión en `pyproject.toml`**:
   ```toml
   version = "0.1.1"  # o "0.2.0", "1.0.0", etc.
   ```

2. **Crear un tag en Git**:
   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```

3. **Seguir los pasos 2-4 nuevamente**

## 📌 Convenciones de Versionado

Usa [Semantic Versioning](https://semver.org/):
- **MAJOR** (1.0.0): Cambios incompatibles
- **MINOR** (0.2.0): Nuevas funcionalidades compatibles
- **PATCH** (0.1.1): Correcciones de bugs

## ⚠️ Notas Importantes

1. **No puedes eliminar versiones publicadas** en PyPI, solo puedes ocultarlas
2. **No puedes reutilizar números de versión** una vez publicados
3. **TestPyPI** es ideal para probar antes de publicar en PyPI real
4. **API Tokens** son más seguros que contraseñas

## 🐛 Solución de Problemas

### Error: "File already exists"
- La versión ya existe en PyPI
- Actualiza el número de versión en `pyproject.toml`

### Error: "Invalid distribution"
- Ejecuta `twine check dist/*` para ver detalles
- Verifica que `pyproject.toml` esté bien formado

### Error: "Authentication failed"
- Verifica tu username/password
- Si usas 2FA, necesitas un API token

## 📚 Recursos Adicionales

- [PyPI Documentation](https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Python Packaging Guide](https://packaging.python.org/)

