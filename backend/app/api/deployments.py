"""
API endpoints para despliegues
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.models.schemas import DeploymentTarget
from app.orchestrators.iaops_orchestrator import orchestrator
from app.api.clients import clients_db
from app.core.logging import logger

router = APIRouter()


class DeploymentRequest(BaseModel):
    """Request de despliegue"""
    target: DeploymentTarget
    infrastructure_code: str
    repository_config: Optional[Dict[str, Any]] = None


@router.post("/deploy")
async def deploy_infrastructure(request: DeploymentRequest):
    """
    Despliega infraestructura en el cloud especificado
    
    - Valida que el cliente pueda usar el cloud provider
    - Orquesta el despliegue usando el conector apropiado
    - Opcionalmente sincroniza con el repositorio
    """
    # Verificar cliente
    if request.target.client_id not in clients_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente {request.target.client_id} no encontrado"
        )
    
    client = clients_db[request.target.client_id]
    
    try:
        logger.info(f"Iniciando despliegue para {client.name}")
        
        # Orquestar despliegue
        result = await orchestrator.orchestrate_deployment(
            client=client,
            target=request.target,
            infrastructure_code=request.infrastructure_code,
            repository_config=request.repository_config
        )
        
        return result
        
    except ValueError as e:
        # Error de validación (ej: cloud no permitido)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error en despliegue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
