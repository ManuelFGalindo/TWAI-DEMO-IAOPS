"""
Conector base para proveedores de repositorios
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.core.logging import logger


class BaseRepositoryConnector(ABC):
    """
    Clase base abstracta para conectores de repositorios
    
    Todos los conectores de repositorios deben implementar estos métodos
    """
    
    def __init__(self, credentials: Dict[str, Any], organization: Optional[str] = None):
        """
        Inicializa el conector
        
        Args:
            credentials: Credenciales del proveedor
            organization: Organización/grupo
        """
        self.credentials = credentials
        self.organization = organization
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
    async def list_repositories(self) -> List[Dict[str, Any]]:
        """Lista repositorios"""
        pass
    
    @abstractmethod
    async def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = True
    ) -> Dict[str, Any]:
        """Crea un repositorio"""
        pass
    
    @abstractmethod
    async def delete_repository(self, repo_name: str) -> bool:
        """Elimina un repositorio"""
        pass
    
    @abstractmethod
    async def create_branch(
        self,
        repo_name: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> Dict[str, Any]:
        """Crea una rama"""
        pass
    
    @abstractmethod
    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main"
    ) -> Dict[str, Any]:
        """Crea un pull request"""
        pass
    
    @abstractmethod
    async def commit_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        message: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Crea o actualiza un archivo en el repositorio"""
        pass
    
    @abstractmethod
    async def get_file_content(
        self,
        repo_name: str,
        file_path: str,
        branch: str = "main"
    ) -> str:
        """Obtiene el contenido de un archivo"""
        pass
    
    async def disconnect(self):
        """Cierra la conexión"""
        if self._client:
            logger.info(f"Desconectando de {self.__class__.__name__}")
            self._client = None
