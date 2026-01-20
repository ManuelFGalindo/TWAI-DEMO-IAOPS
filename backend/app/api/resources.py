"""
API endpoints para gestión de recursos cloud
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from app.models.schemas import CloudProvider
from app.orchestrators.iaops_orchestrator import orchestrator
from app.api.clients import clients_db
from app.core.logging import logger

router = APIRouter()


@router.get("/{client_id}/{cloud_provider}/{resource_type}")
async def list_resources(
    client_id: str,
    cloud_provider: CloudProvider,
    resource_type: str
):
    """
    Lista recursos de un cliente en un cloud provider específico
    
    Ejemplos de resource_type:
    - AWS: ec2, s3, lambda, rds, ecs, eks
    - Azure: vms, storage, functions, aks
    - GCP: instances, storage, functions, gke
    """
    # Verificar cliente
    if client_id not in clients_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente {client_id} no encontrado"
        )
    
    client = clients_db[client_id]
    
    try:
        resources = await orchestrator.list_client_resources(
            client=client,
            cloud_provider=cloud_provider,
            resource_type=resource_type
        )
        
        return {
            'client_id': client_id,
            'cloud_provider': cloud_provider,
            'resource_type': resource_type,
            'count': len(resources),
            'resources': resources
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listando recursos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
