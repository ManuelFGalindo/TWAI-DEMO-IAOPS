# IAOPS Platform

![IAOPS Logo](assets/logo.png)

## 🎯 Visión General

**IAOPS** (Intelligent AI Operations) es una plataforma de orquestación inteligente que permite a las organizaciones gestionar su infraestructura multi-cloud y multi-repositorio de manera centralizada, respetando sus estándares tecnológicos existentes.

### ¿Por qué IAOPS?

En el mundo actual, las empresas utilizan múltiples proveedores de nube (AWS, Azure, GCP) y diferentes sistemas de control de versiones (GitHub, GitLab, Bitbucket). IAOPS proporciona una capa de orquestación unificada que:

- ✅ **Respeta tu Stack Tecnológico**: No impone tecnologías nuevas, trabaja con lo que ya tienes
- ✅ **Inteligencia Artificial**: Genera arquitecturas y código de infraestructura alineado a tus estándares
- ✅ **Multi-Cloud Native**: Soporta AWS, Azure y GCP desde el primer día
- ✅ **Architecture as Code**: Convierte descripciones en arquitecturas reales
- ✅ **Orquestación Centralizada**: Un solo punto de control para todos tus recursos

## 🚀 Características Principales

### Perfil Tecnológico por Cliente

Cada cliente define su "tech profile" que incluye:

```json
{
  "clouds": ["aws", "azure"],
  "repositories": ["github"],
  "standards": {
    "infrastructure": "terraform",
    "cicd": "github-actions",
    "container_orchestration": "kubernetes"
  },
  "allowed_services": {
    "aws": ["ec2", "s3", "lambda", "rds"],
    "azure": ["vms", "storage"]
  }
}
```

### Generación Inteligente de Arquitecturas

La IA genera arquitecturas respetando:

- Nubes permitidas por el cliente
- Servicios específicos autorizados
- Estándares de infraestructura como código
- Mejores prácticas de cada proveedor

### Orquestación Multi-Cloud

Despliega infraestructura en múltiples clouds desde una sola API:

```python
deployment = await orchestrator.deploy(
    client=client,
    target=DeploymentTarget(
        cloud_provider="aws",
        region="us-east-1",
        environment="production"
    ),
    infrastructure_code=terraform_code
)
```

### Integración con Repositorios

Sincroniza automáticamente el código de infraestructura con GitHub/GitLab:

```python
await orchestrator.sync_with_repository(
    repository="my-org/infrastructure",
    branch="main",
    code=infrastructure_code
)
```

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                      IAOPS Platform                      │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   API REST   │  │  Orquestador │  │  IA Engine   │  │
│  │   FastAPI    │──│   Principal  │──│  OpenAI/     │  │
│  │              │  │              │  │  Anthropic   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                           │                              │
│         ┌─────────────────┼─────────────────┐           │
│         │                 │                 │           │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐    │
│  │   Cloud     │  │    Repo     │  │   AI        │    │
│  │  Connectors │  │  Connectors │  │  Services   │    │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘    │
└─────────┼─────────────────┼──────────────────────────────┘
          │                 │
     ┌────┴────┐      ┌─────┴─────┐
     │ AWS     │      │  GitHub   │
     │ Azure   │      │  GitLab   │
     │ GCP     │      │  Bitbucket│
     └─────────┘      └───────────┘
```

## 📦 Componentes

### Backend (FastAPI)

- **API REST**: Endpoints para gestión de clientes, arquitecturas, despliegues
- **Orquestadores**: Coordinan las operaciones entre conectores
- **Conectores Cloud**: Adaptadores para AWS, Azure, GCP
- **Conectores Repositorio**: Adaptadores para GitHub, GitLab, Bitbucket
- **Motor IA**: Generación de arquitecturas con OpenAI/Anthropic

### Conectores Extensibles

La arquitectura permite agregar nuevos conectores fácilmente:

```python
class NewCloudConnector(BaseCloudConnector):
    async def connect(self): ...
    async def deploy_infrastructure(self, code): ...
    # ... otros métodos
```

## 🎓 Casos de Uso

### 1. Arquitectura Generada por IA

```bash
POST /api/v1/architecture/generate
{
  "client_id": "client-123",
  "description": "Necesito una aplicación web escalable con base de datos",
  "requirements": {
    "scalability": "high",
    "availability": "99.9%"
  }
}
```

Respuesta:
- Arquitectura diseñada con los servicios permitidos del cliente
- Código Terraform/CloudFormation generado
- Estimación de costos
- Recomendaciones de optimización

### 2. Despliegue Multi-Cloud

```bash
POST /api/v1/deployments/deploy
{
  "target": {
    "client_id": "client-123",
    "cloud_provider": "aws",
    "region": "us-east-1",
    "environment": "production"
  },
  "infrastructure_code": "...",
  "repository_config": {
    "provider": "github",
    "repository": "my-org/infrastructure"
  }
}
```

### 3. Gestión de Recursos

```bash
GET /api/v1/resources/client-123/aws/ec2
```

Lista todas las instancias EC2 del cliente en AWS.

## 🔐 Seguridad

- ✅ Credenciales encriptadas en base de datos
- ✅ Autenticación JWT
- ✅ Validación de permisos por cliente
- ✅ Logs de auditoría
- ✅ Rotación de credenciales

## 📚 Próximos Pasos

- [Instalación](getting-started/installation.md)
- [Configuración](getting-started/configuration.md)
- [Guía de Inicio Rápido](getting-started/quickstart.md)
- [Referencia de API](api/clients.md)

## 🤝 Contribuir

¿Quieres contribuir al proyecto? Lee nuestra [guía de contribución](development/contributing.md).

## 📄 Licencia

MIT License - Ver [LICENSE](../LICENSE) para más detalles.
