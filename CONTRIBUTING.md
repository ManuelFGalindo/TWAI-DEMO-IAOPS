# Contributing to IAOPS Platform

¡Gracias por tu interés en contribuir a IAOPS! Este documento proporciona guías para contribuir al proyecto.

## 🎯 Formas de Contribuir

- Reportar bugs
- Sugerir nuevas funcionalidades
- Escribir o mejorar documentación
- Crear nuevos conectores (cloud providers, repositorios, etc.)
- Optimizar código existente
- Agregar tests

## 🚀 Proceso de Contribución

### 1. Fork y Clone

```bash
# Fork el repositorio en GitHub

# Clonar tu fork
git clone https://github.com/tu-usuario/iaops-platform.git
cd iaops-platform
```

### 2. Crear una Rama

```bash
git checkout -b feature/mi-nueva-funcionalidad
# o
git checkout -b fix/correccion-de-bug
```

### 3. Hacer Cambios

- Escribe código limpio y documentado
- Sigue las convenciones de estilo del proyecto
- Agrega tests para nuevas funcionalidades
- Actualiza la documentación si es necesario

### 4. Ejecutar Tests

```bash
cd backend
pytest tests/ -v
```

### 5. Commit

```bash
git add .
git commit -m "feat: agregar conector para Kubernetes"
```

Usa [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` nueva funcionalidad
- `fix:` corrección de bug
- `docs:` cambios en documentación
- `test:` agregar o modificar tests
- `refactor:` refactorización de código
- `chore:` tareas de mantenimiento

### 6. Push y Pull Request

```bash
git push origin feature/mi-nueva-funcionalidad
```

Luego crea un Pull Request en GitHub.

## 📝 Guías de Código

### Python (Backend)

- Seguir PEP 8
- Usar type hints
- Documentar funciones con docstrings
- Mantener funciones pequeñas y enfocadas

Ejemplo:

```python
async def create_resource(
    self,
    resource_type: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Crea un recurso en el cloud provider.
    
    Args:
        resource_type: Tipo de recurso (ec2, s3, etc.)
        config: Configuración del recurso
        
    Returns:
        Información del recurso creado
        
    Raises:
        ValueError: Si el tipo de recurso no es soportado
    """
    # Implementación
```

### Estructura de Conectores

Para agregar un nuevo conector, heredar de la clase base:

```python
from app.connectors.cloud.base import BaseCloudConnector

class MyCloudConnector(BaseCloudConnector):
    async def connect(self) -> bool:
        # Implementación
        
    async def validate_credentials(self) -> bool:
        # Implementación
        
    # ... otros métodos requeridos
```

## 🧪 Tests

- Escribir tests para nuevas funcionalidades
- Mantener cobertura de tests > 80%
- Usar fixtures de pytest para datos de prueba

```python
@pytest.mark.asyncio
async def test_my_feature(sample_client):
    # Test implementation
    pass
```

## 📖 Documentación

- Actualizar `docs/` para nuevas funcionalidades
- Incluir ejemplos de uso
- Actualizar README.md si es relevante

## 🐛 Reportar Bugs

Incluir en el reporte:

1. Descripción del bug
2. Pasos para reproducir
3. Comportamiento esperado vs. actual
4. Versión de Python y dependencias
5. Logs relevantes

## 💡 Sugerir Funcionalidades

Incluir:

1. Descripción de la funcionalidad
2. Caso de uso
3. Beneficios
4. Posible implementación

## ⚖️ Código de Conducta

- Ser respetuoso y profesional
- Aceptar críticas constructivas
- Enfocarse en lo mejor para el proyecto
- Ayudar a otros contribuidores

## 📞 Contacto

Para preguntas, contactar a través de:

- GitHub Issues
- Discussions en GitHub

¡Gracias por contribuir a IAOPS! 🎉
