"""
Conector base para todos los proveedores de nube
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.core.logging import logger


class BaseCloudConnector(ABC):
    """
    Clase base abstracta para conectores de nube
    
    Todos los conectores de cloud deben implementar estos métodos
    """
    
    def __init__(self, credentials: Dict[str, Any], region: Optional[str] = None):
        """
        Inicializa el conector
        
        Args:
            credentials: Credenciales del proveedor
            region: Región por defecto
        """
        self.credentials = credentials
        self.region = region
        self._client = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establece conexión con el proveedor"""
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Valida las credenciales"""
        pass
    
    @abstractmethod
    async def list_resources(self, resource_type: str) -> List[Dict[str, Any]]:
        """Lista recursos de un tipo específico"""
        pass
    
    @abstractmethod
    async def create_resource(
        self,
        resource_type: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crea un recurso"""
        pass
    
    @abstractmethod
    async def delete_resource(
        self,
        resource_type: str,
        resource_id: str
    ) -> bool:
        """Elimina un recurso"""
        pass
    
    @abstractmethod
    async def get_resource_status(
        self,
        resource_type: str,
        resource_id: str
    ) -> Dict[str, Any]:
        """Obtiene el estado de un recurso"""
        pass
    
    @abstractmethod
    async def deploy_infrastructure(
        self,
        infrastructure_code: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Despliega infraestructura como código"""
        pass
    
    async def disconnect(self):
        """Cierra la conexión"""
        if self._client:
            logger.info(f"Desconectando de {self.__class__.__name__}")
            self._client = None
