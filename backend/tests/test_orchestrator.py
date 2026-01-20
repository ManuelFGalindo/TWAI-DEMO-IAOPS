"""
Tests para el orquestador principal de IAOPS
"""
import pytest
from app.models.schemas import (
    Client, TechProfile, TechStandards, CloudProvider,
    RepositoryProvider, InfrastructureStandard, CICDStandard
)
from app.orchestrators.iaops_orchestrator import IAOPSOrchestrator


@pytest.fixture
def sample_client():
    """Cliente de prueba"""
    return Client(
        id="test-client-123",
        name="Test Company",
        description="Cliente de prueba",
        tech_profile=TechProfile(
            clouds=[CloudProvider.AWS],
            repositories=[RepositoryProvider.GITHUB],
            standards=TechStandards(
                infrastructure=InfrastructureStandard.TERRAFORM,
                cicd=CICDStandard.GITHUB_ACTIONS,
                container_orchestration="kubernetes"
            )
        ),
        created_at=None,
        updated_at=None,
        is_active=True
    )


@pytest.fixture
def orchestrator():
    """Orquestador de prueba"""
    return IAOPSOrchestrator()


@pytest.mark.asyncio
async def test_validate_tech_profile_structure(sample_client, orchestrator):
    """Test que valida la estructura del perfil tecnológico"""
    # Verificar que el cliente tiene el perfil correcto
    assert sample_client.tech_profile.clouds == [CloudProvider.AWS]
    assert sample_client.tech_profile.repositories == [RepositoryProvider.GITHUB]
    assert sample_client.tech_profile.standards.infrastructure == InfrastructureStandard.TERRAFORM


@pytest.mark.asyncio
async def test_client_validation_with_invalid_cloud(sample_client, orchestrator):
    """Test que valida que un cliente no pueda usar clouds no permitidos"""
    from app.models.schemas import DeploymentTarget
    
    # Intentar desplegar en Azure (no permitido)
    target = DeploymentTarget(
        client_id=sample_client.id,
        cloud_provider=CloudProvider.AZURE,
        region="eastus",
        environment="dev"
    )
    
    with pytest.raises(ValueError, match="no tiene permitido usar"):
        await orchestrator.orchestrate_deployment(
            client=sample_client,
            target=target,
            infrastructure_code="test code"
        )


@pytest.mark.asyncio
async def test_orchestrator_cleanup(orchestrator):
    """Test que verifica la limpieza de conectores"""
    await orchestrator.cleanup()
    
    assert len(orchestrator.cloud_connectors) == 0
    assert len(orchestrator.repo_connectors) == 0


def test_client_model_creation():
    """Test de creación de modelo de cliente"""
    tech_profile = TechProfile(
        clouds=[CloudProvider.AWS, CloudProvider.AZURE],
        repositories=[RepositoryProvider.GITHUB, RepositoryProvider.GITLAB],
        standards=TechStandards(
            infrastructure=InfrastructureStandard.TERRAFORM,
            cicd=CICDStandard.GITHUB_ACTIONS,
            container_orchestration="kubernetes",
            monitoring="prometheus",
            logging="elk"
        ),
        allowed_services={
            "aws": ["ec2", "s3", "lambda"],
            "azure": ["vms", "storage"]
        }
    )
    
    client = Client(
        id="test-123",
        name="Multi-Cloud Company",
        description="Empresa con multi-cloud",
        tech_profile=tech_profile,
        created_at=None,
        updated_at=None,
        is_active=True
    )
    
    assert len(client.tech_profile.clouds) == 2
    assert len(client.tech_profile.repositories) == 2
    assert "aws" in client.tech_profile.allowed_services
    assert "ec2" in client.tech_profile.allowed_services["aws"]
