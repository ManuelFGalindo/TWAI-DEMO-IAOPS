# Guía de Inicio Rápido

Esta guía te llevará paso a paso para realizar tu primera operación con IAOPS.

## 1. Crear un Cliente

Primero, crea un cliente con su perfil tecnológico:

```bash
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mi Empresa",
    "description": "Cliente de prueba",
    "tech_profile": {
      "clouds": ["aws"],
      "repositories": ["github"],
      "standards": {
        "infrastructure": "terraform",
        "cicd": "github-actions",
        "container_orchestration": "kubernetes"
      }
    }
  }'
```

Respuesta:
```json
{
  "id": "abc-123-def",
  "name": "Mi Empresa",
  "tech_profile": { ... },
  "created_at": "2024-01-20T10:00:00Z",
  "is_active": true
}
```

**Guarda el `id` del cliente**, lo usaremos en los siguientes pasos.

## 2. Generar una Arquitectura con IA

Ahora vamos a pedirle a la IA que genere una arquitectura:

```bash
curl -X POST http://localhost:8000/api/v1/architecture/generate \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "abc-123-def",
    "description": "Necesito una API REST con base de datos PostgreSQL, que sea escalable y segura",
    "requirements": {
      "scalability": "high",
      "availability": "99.9%",
      "environment": "production"
    }
  }'
```

Respuesta:
```json
{
  "client_id": "abc-123-def",
  "architecture": {
    "architecture_overview": "Arquitectura de 3 capas con ALB, ECS Fargate y RDS PostgreSQL",
    "components": [
      {
        "name": "Load Balancer",
        "type": "load_balancer",
        "cloud_service": "AWS Application Load Balancer",
        "description": "Distribuye tráfico entre contenedores"
      },
      {
        "name": "API Service",
        "type": "compute",
        "cloud_service": "AWS ECS Fargate",
        "description": "Contenedores sin servidor para la API"
      },
      {
        "name": "Database",
        "type": "database",
        "cloud_service": "AWS RDS PostgreSQL",
        "description": "Base de datos relacional administrada"
      }
    ],
    "security": {
      "authentication": "JWT tokens",
      "encryption": "TLS 1.3 en tránsito, AES-256 en reposo",
      "network_isolation": "VPC con subnets privadas"
    }
  },
  "infrastructure_code": "# Terraform code\n...",
  "estimated_cost": {
    "monthly_estimate": {
      "min": 200,
      "max": 500,
      "currency": "USD"
    }
  },
  "recommendations": [
    "Implemente WAF y DDoS protection",
    "Configure monitoring con CloudWatch"
  ]
}
```

## 3. Listar Recursos Existentes

Consulta los recursos que ya tienes en AWS:

```bash
curl http://localhost:8000/api/v1/resources/abc-123-def/aws/ec2
```

Respuesta:
```json
{
  "client_id": "abc-123-def",
  "cloud_provider": "aws",
  "resource_type": "ec2",
  "count": 3,
  "resources": [
    {
      "id": "i-1234567890abcdef0",
      "type": "t3.medium",
      "state": "running",
      "launch_time": "2024-01-15T09:00:00Z"
    }
  ]
}
```

## 4. Desplegar Infraestructura

Despliega la infraestructura generada:

```bash
curl -X POST http://localhost:8000/api/v1/deployments/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "target": {
      "client_id": "abc-123-def",
      "cloud_provider": "aws",
      "region": "us-east-1",
      "environment": "production",
      "resource_tags": {
        "Project": "IAOPS-Demo",
        "ManagedBy": "IAOPS"
      }
    },
    "infrastructure_code": "...",
    "repository_config": {
      "provider": "github",
      "repository": "my-org/infrastructure",
      "file_path": "production/main.tf",
      "branch": "main"
    }
  }'
```

Respuesta:
```json
{
  "client_id": "abc-123-def",
  "deployment": {
    "stack_id": "arn:aws:cloudformation:...",
    "status": "CREATE_IN_PROGRESS"
  },
  "status": "success"
}
```

## 5. Validar Perfil del Cliente

Valida que las credenciales estén configuradas correctamente:

```bash
curl -X POST http://localhost:8000/api/v1/clients/abc-123-def/validate
```

Respuesta:
```json
{
  "client_id": "abc-123-def",
  "clouds": {
    "aws": {
      "status": "valid",
      "message": "Credentials validated"
    }
  },
  "repositories": {
    "github": {
      "status": "valid",
      "message": "Credentials validated"
    }
  },
  "overall_status": "valid"
}
```

## Ejemplos Avanzados

### Multi-Cloud

Cliente con múltiples clouds:

```json
{
  "name": "Empresa Multi-Cloud",
  "tech_profile": {
    "clouds": ["aws", "azure", "gcp"],
    "repositories": ["github", "gitlab"],
    "standards": {
      "infrastructure": "terraform",
      "cicd": "github-actions",
      "container_orchestration": "kubernetes"
    },
    "allowed_services": {
      "aws": ["ec2", "s3", "lambda", "rds", "eks"],
      "azure": ["vms", "storage", "functions", "aks"],
      "gcp": ["compute", "storage", "functions", "gke"]
    }
  }
}
```

### Restricciones Específicas

Cliente con restricciones de seguridad:

```json
{
  "tech_profile": {
    "clouds": ["aws"],
    "restrictions": {
      "allowed_regions": ["us-east-1", "us-west-2"],
      "require_encryption": true,
      "require_vpc": true,
      "max_instance_type": "t3.xlarge"
    }
  }
}
```

## Próximos Pasos

- Explora la [Referencia Completa de API](../api/clients.md)
- Lee sobre [Arquitectura de Conectores](../architecture/cloud-connectors.md)
- Aprende sobre [Casos de Uso Avanzados](../use-cases/multi-cloud.md)
