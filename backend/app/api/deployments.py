from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import httpx
import re
import base64
import asyncio
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
    Despliega código desde un repositorio GitHub hacia un recurso cloud usando GitHub Actions.
    Crea el workflow de despliegue automáticamente si no existe.
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
        cloud_provider="azure",
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
        # Extraer owner/repo
        match = re.search(r'github\.com[:/]([^/]+)/([^/\.]+)', request.repo_url)
        if not match:
            raise ValueError(f"URL de repositorio inválida: {request.repo_url}")
        
        owner, repo = match.group(1), match.group(2)
        logger.info(f"Parsed GitHub repo: {owner}/{repo}")
        
        headers = {
            "Authorization": f"token {repo_config['token']}",
            "Accept": "application/vnd.github.v3+json"
        }

        workflows_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows"

        async with httpx.AsyncClient() as client:
            # Listar workflows existentes
            logger.info(f"Listing workflows from {workflows_url}")
            wf_resp = await client.get(workflows_url, headers=headers, timeout=10.0)
            if wf_resp.status_code != 200:
                logger.error(f"GitHub list workflows error: {wf_resp.status_code} - {wf_resp.text}")
                raise HTTPException(status_code=500, detail=f"Error listing workflows: {wf_resp.status_code}")

            wf_json = wf_resp.json()
            workflows = wf_json.get("workflows", []) if isinstance(wf_json, dict) else []
            logger.info(f"Found {len(workflows)} workflows: {[w.get('path') for w in workflows]}")

            # Buscar workflow de despliegue
            workflow_id = None
            for wf in workflows:
                path = wf.get("path", "")
                name = (wf.get("name") or "").lower()
                wf_id = wf.get("id")
                logger.debug(f"Checking workflow: path={path}, name={name}, id={wf_id}")
                if path.endswith("deploy.yml") or path.endswith("deploy.yaml") or "deploy" in name:
                    workflow_id = wf_id
                    logger.info(f"Found existing workflow: id={workflow_id}")
                    break

            # Si no existe, crear
            if not workflow_id:
                logger.info(f"No deploy workflow found. Creating...")

                workflow_path = ".github/workflows/deploy.yml"
                script_path = ".github/scripts/deploy.sh"

                deploy_yml = """name: Deploy (IAOPS generated)
on:
  workflow_dispatch:
    inputs:
      resource_id:
        description: 'Resource ID'
        required: true
      environment:
        description: 'Environment'
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run repo deploy script if present
        run: |
          if [ -f .github/scripts/deploy.sh ]; then
            chmod +x .github/scripts/deploy.sh
            .github/scripts/deploy.sh "${{ github.event.inputs.resource_id }}" "${{ github.event.inputs.environment }}"
          else
            echo "No deploy script found; add .github/scripts/deploy.sh to implement deployment."
            exit 0
          fi
"""

                deploy_sh = """#!/bin/bash
RESOURCE_ID=$1
ENVIRONMENT=$2
echo "Placeholder deploy script. Resource: $RESOURCE_ID Environment: $ENVIRONMENT"
# TODO: implement actual deployment  commands here
"""

                async def ensure_file(path: str, content: str) -> bool:
                    contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
                    get_resp = await client.get(contents_url, headers=headers, params={"ref": request.branch}, timeout=10.0)
                    if get_resp.status_code == 200:
                        logger.info(f"File {path} already exists")
                        return True
                    
                    logger.debug(f"Creating file {path}")
                    payload = {
                        "message": f"chore(ci): add {path} (generated by IAOPS)",
                        "content": base64.b64encode(content.encode()).decode(),
                        "branch": request.branch
                    }
                    put_resp = await client.put(contents_url, headers=headers, json=payload, timeout=10.0)
                    if put_resp.status_code in (201, 200):
                        logger.info(f"Created {path}")
                        return True
                    else:
                        logger.error(f"Failed creating {path}: {put_resp.status_code} - {put_resp.text}")
                        return False

                created_wf = await ensure_file(workflow_path, deploy_yml)
                created_script = await ensure_file(script_path, deploy_sh)

                logger.info(f"File creation results: workflow={created_wf}, script={created_script}")

                if not (created_wf or created_script):
                    raise HTTPException(status_code=500, detail="Failed to create workflow/script")

                await asyncio.sleep(2)

                logger.info("Re-fetching workflows...")
                wf_resp2 = await client.get(workflows_url, headers=headers, timeout=10.0)
                if wf_resp2.status_code == 200:
                    wf_json2 = wf_resp2.json()
                    workflows = wf_json2.get("workflows", []) if isinstance(wf_json2, dict) else []
                    logger.info(f"After creation, found {len(workflows)} workflows")
                    
                    for wf in workflows:
                        path = wf.get("path", "")
                        name = (wf.get("name") or "").lower()
                        wf_id = wf.get("id")
                        if path.endswith("deploy.yml") or path.endswith("deploy.yaml") or "deploy" in name:
                            workflow_id = wf_id
                            logger.info(f"Found new workflow: id={workflow_id}")
                            break

            if not workflow_id:
                available = [wf.get("path") or wf.get("name") for wf in workflows]
                logger.error(f"No deploy workflow found. Available: {available}")
                raise HTTPException(status_code=404, detail=f"No deploy workflow found")

            # Disparar workflow
            dispatch_url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
            logger.info(f"Dispatching workflow: {dispatch_url}")

            response = await client.post(
                dispatch_url,
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
                history.status = "completed"
                history.completed_at = datetime.utcnow()
                await db.commit()

                logger.info(f"Deployment workflow dispatched successfully")
                return {
                    "status": "success",
                    "message": f"Despliegue iniciado desde {request.branch} hacia {request.resource_id}",
                    "deployment_id": str(history.id)
                }
            else:
                error_msg = f"GitHub API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en despliegue de código: {e}", exc_info=True)
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
