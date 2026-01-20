# Instalación

## Requisitos Previos

- **Python 3.11+**
- **Docker** (opcional, recomendado)
- **Node.js 18+** (para frontend, futuro)
- **Git**

## Instalación Local

### 1. Clonar el Repositorio

```bash
git clone <repository-url>
cd iaops-platform
```

### 2. Backend Setup

```bash
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Linux/Mac:
source venv/bin/activate
# En Windows:
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración

Crear archivo `.env` en el directorio `backend/`:

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales:

```env
# Application
APP_NAME=IAOPS Platform
DEBUG=True

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/iaops

# Security
SECRET_KEY=your-secret-key-here

# AWS (opcional)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_DEFAULT_REGION=us-east-1

# Azure (opcional)
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
AZURE_SUBSCRIPTION_ID=your-subscription-id

# GCP (opcional)
GCP_PROJECT_ID=your-project-id
GCP_CREDENTIALS_PATH=/path/to/credentials.json

# GitHub (opcional)
GITHUB_TOKEN=your-github-token

# GitLab (opcional)
GITLAB_TOKEN=your-gitlab-token

# OpenAI (recomendado)
OPENAI_API_KEY=your-openai-key

# Anthropic (opcional)
ANTHROPIC_API_KEY=your-anthropic-key
```

### 4. Ejecutar el Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El backend estará disponible en `http://localhost:8000`

### 5. Documentación Interactiva

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Instalación con Docker

### 1. Usando Docker Compose

```bash
# Construir y ejecutar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

### 2. Usando Docker Directamente

```bash
# Backend
cd backend
docker build -t iaops-backend .
docker run -p 8000:8000 --env-file .env iaops-backend
```

## Instalación de MkDocs (Documentación)

```bash
# Instalar mkdocs y dependencias
pip install mkdocs mkdocs-material mkdocstrings

# Servir documentación localmente
mkdocs serve

# Documentación disponible en http://localhost:8001
```

## Verificación de la Instalación

### Health Check

```bash
curl http://localhost:8000/health
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Test API

```bash
curl http://localhost:8000/api/v1/clients/
```

## Troubleshooting

### Error: Puerto 8000 en uso

```bash
# Cambiar puerto
uvicorn app.main:app --port 8080
```

### Error: Credenciales de base de datos

Verificar que PostgreSQL esté ejecutándose:

```bash
docker run --name iaops-postgres \
  -e POSTGRES_PASSWORD=iaops \
  -e POSTGRES_USER=iaops \
  -e POSTGRES_DB=iaops \
  -p 5432:5432 \
  -d postgres:15
```

### Error: Módulos no encontrados

```bash
# Re-instalar dependencias
pip install --upgrade -r requirements.txt
```

## Próximos Pasos

- [Configuración Detallada](configuration.md)
- [Guía de Inicio Rápido](quickstart.md)
