from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import httpx
from app.models.schemas import DeploymentTarget, Client
from app.models.database import ClientModel, DeploymentHistoryModel
from app.orchestrators.iaops_orchestrator import orchestrator
from app.core.database import get_db
from app.core.logging import logger
from app.core.config_resolver import ConfigResolver

router = APIRouter()

class DeploymentRequest(BaseModel):
    """Request de despliegue"""
    target: DeploymentTarget
    infrastructure_code: str
    architecture_metadata: Optional[Dict[str, Any]] = None
    repository_config: Optional[Dict[str, Any]] = None

class CodeDeploymentRequest(BaseModel):
    """Request para despliegue de código desde repositorio"""
    client_id: str
    repo_url: str
    branch: str
    resource_id: str
    resource_type: str
    environment: str = "production"

@router.post("/deploy")
async def deploy_infrastructure(request: DeploymentRequest, db: AsyncSession = Depends(get_db)):
    """
    Despliega infraestructura en el cloud especificado y guarda histórico en DB
    """
    # Verificar cliente en DB
    result = await db.execute(select(ClientModel).where(ClientModel.id == request.target.client_id))
    client_model = result.scalar_one_or_none()
    
    if not client_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente {request.target.client_id} no encontrado"
        )
    
    # Crear record de histórico (pendente)
    history = DeploymentHistoryModel(
        client_id=client_model.id,
        cloud_provider=request.target.cloud_provider,
        region=request.target.region,
        environment=request.target.environment,
        status="running",
        deployment_data={
            "target": request.target.model_dump(),
            "metadata": request.architecture_metadata
        }
    )
    db.add(history)
    await db.commit()
    
    # Convertir a esquema Pydantic para el orquestador
    client = Client(
        id=client_model.id,
        name=client_model.name,
        description=client_model.description,
        tech_profile=client_model.tech_profile,
        is_active=client_model.is_active,
        created_at=client_model.created_at,
        updated_at=client_model.updated_at
    )
    
    try:
        logger.info(f"Iniciando despliegue para {client.name} (Ref: {history.id})")
        
        # Orquestar despliegue
        result = await orchestrator.orchestrate_deployment(
            client=client,
            target=request.target,
            infrastructure_code=request.infrastructure_code,
            architecture_metadata=request.architecture_metadata,
            repository_config=request.repository_config
        )
        
        # Actualizar histórico a completado
        history.status = "completed"
        history.completed_at = datetime.utcnow()
        await db.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Error en despliegue: {e}")
        # Actualizar histórico a fallido
        history.status = "failed"
        history.error_message = str(e)
        history.completed_at = datetime.utcnow()
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/code")
async def deploy_code(request: CodeDeploymentRequest, db: AsyncSession = Depends(get_db)):
    """
    Despliega código desde un repositorio GitHub hacia un recurso cloud usando GitHub Actions
    """
    # Verificar cliente
    result = await db.execute(select(ClientModel).where(ClientModel.id == request.client_id))
    client_model = result.scalar_one_or_none()
    
    if not client_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente {request.client_id} no encontrado"
        )
    
    # Obtener token de GitHub
    resolver = ConfigResolver(db)
    repo_config = await resolver.get_repository_config(request.client_id)
    
    if not repo_config or not repo_config.get('token'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontró configuración de GitHub para este cliente"
        )
    
    # Crear registro de despliegue
    history = DeploymentHistoryModel(
        client_id=client_model.id,
        cloud_provider="azure",  # Por ahora asumimos Azure
        region="",
        environment=request.environment,
        status="running",
        deployment_data={
            "type": "code_deployment",
            "repo_url": request.repo_url,
            "branch": request.branch,
            "resource_id": request.resource_id,
            "resource_type": request.resource_type
        }
    )
    db.add(history)
    await db.commit()
    
    try:
        # Extraer owner/repo del URL
        import re
        match = re.search(r'github\.com[:/]([^/]+)/([^/\.]+)', request.repo_url)
        if not match:
            raise ValueError(f"URL de repositorio inválida: {request.repo_url}")
        
        owner, repo = match.group(1), match.group(2)
        
        # Trigger GitHub Actions workflow dispatch
        headers = {
            "Authorization": f"token {repo_config['token']}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        workflow_dispatch_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/deploy.yml/dispatches"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                workflow_dispatch_url,
                headers=headers,
                json={
                    "ref": request.branch,
                    "inputs": {
                        "resource_id": request.resource_id,
                        "environment": request.environment
                    }
                },
                timeout=10.0
            )
            
            if response.status_code == 204:
                # Workflow triggered successfully
                history.status = "completed"
                history.completed_at = datetime.utcnow()
                await db.commit()
                
                return {
                    "status": "success",
                    "message": f"Despliegue iniciado desde {request.branch} hacia {request.resource_id}",
                    "deployment_id": str(history.id)
                }
            else:
                error_msg = f"GitHub API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
                
    except Exception as e:
        logger.error(f"Error en despliegue de código: {e}")
        history.status = "failed"
        history.error_message = str(e)
        history.completed_at = datetime.utcnow()
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/history/{client_id}")
async def get_deployment_history(client_id: str, db: AsyncSession = Depends(get_db)):
    """
    Obtiene el historial de despliegues de un cliente
    """
    result = await db.execute(
        select(DeploymentHistoryModel)
        .where(DeploymentHistoryModel.client_id == client_id)
        .order_by(DeploymentHistoryModel.created_at.desc())
    )
    history = result.scalars().all()
    return history
