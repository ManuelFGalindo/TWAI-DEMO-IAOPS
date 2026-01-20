# IAOPS Platform

**Intelligent AI Operations Platform** - Plataforma de orquestación inteligente multi-cloud y multi-repositorio.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)

## 🎯 Visión General

IAOPS es una plataforma de orquestación que permite a cada cliente gestionar su infraestructura tecnológica de manera inteligente, respetando sus estándares y tecnologías existentes.

### Características Principales

- **🏢 Perfil Tecnológico por Cliente**: Cada cliente define sus nubes permitidas, repositorios y estándares
- **☁️ Orquestación Multi-Cloud**: Soporte para AWS, Azure, GCP
- **📦 Orquestación de Repositorios**: Integración con GitHub, GitLab, Bitbucket
- **🤖 Generación Inteligente de Soluciones**: IA que respeta el stack tecnológico real del cliente
- **🏗️ Architecture as Code**: Diseño de arquitecturas alineadas a las tecnologías del cliente

## 🏗️ Arquitectura

```
iaops-platform/
├── backend/              # Backend FastAPI
│   ├── app/
│   │   ├── api/         # Endpoints REST
│   │   ├── core/        # Configuración y utilidades
│   │   ├── models/      # Modelos de datos
│   │   ├── services/    # Lógica de negocio
│   │   ├── orchestrators/ # Orquestadores principales
│   │   └── connectors/  # Conectores extensibles
│   │       ├── cloud/   # AWS, Azure, GCP
│   │       ├── repository/ # GitHub, GitLab, Bitbucket
│   │       └── ai/      # OpenAI, Anthropic, etc.
│   └── tests/           # Tests unitarios e integración
├── frontend/            # Frontend (React/Vue - futuro)
├── docs/               # Documentación MkDocs
├── config/             # Configuraciones
└── scripts/            # Scripts de utilidad
```

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.11+
- Docker y Docker Compose
- Node.js 18+ (para frontend)

### Instalación

```bash
# Clonar repositorio
git clone https://github.com/antape2615/TWAI-DEMO-IAOPS.git
cd TWAI-DEMO-IAOPS

# Instalar dependencias del backend
cd backend
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Ver documentación
cd ../docs
mkdocs serve
```

### Con Docker

```bash
docker-compose up -d
```

## 📚 Documentación

La documentación completa está disponible en:
- **Local**: `http://localhost:8001` (después de `mkdocs serve`)
- **API Docs**: `http://localhost:8000/docs`

## 🔌 Conectores Disponibles

### Cloud Providers
- ✅ AWS (EC2, S3, Lambda, ECS, EKS, RDS, etc.)
- ✅ Azure (VMs, Blob Storage, Functions, AKS, etc.)
- ✅ GCP (Compute Engine, Cloud Storage, Cloud Functions, GKE, etc.)

### Repositorios
- ✅ GitHub
- ✅ GitLab
- 🚧 Bitbucket (en desarrollo)

### IA
- ✅ OpenAI
- ✅ Anthropic
- 🚧 Azure OpenAI

## 🔧 Configuración

### Perfil Tecnológico del Cliente

```json
{
  "client_id": "client-001",
  "name": "Empresa ABC",
  "tech_profile": {
    "clouds": ["aws", "azure"],
    "repositories": ["github"],
    "standards": {
      "infrastructure": "terraform",
      "cicd": "github-actions",
      "container_orchestration": "kubernetes"
    }
  }
}
```

## 🧪 Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

## 🤝 Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para detalles sobre cómo contribuir al proyecto.

## 📝 Licencia

[MIT License](LICENSE)

## 👥 Equipo

Desarrollado con ❤️ por el equipo de IAOPS

## 🗺️ Roadmap

- [x] Backend con FastAPI
- [x] Conectores AWS, Azure, GCP
- [x] Conectores GitHub, GitLab
- [x] Orquestador de IA
- [x] Documentación con MkDocs
- [ ] Frontend con React
- [ ] Base de datos PostgreSQL
- [ ] Sistema de caché con Redis
- [ ] Métricas y monitoring
- [ ] Tests de integración completos
- [ ] CI/CD con GitHub Actions
