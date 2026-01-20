"""
Conector para GitHub
"""
from github import Github, GithubException
from typing import Dict, Any, List, Optional
from app.connectors.repository.base import BaseRepositoryConnector
from app.core.logging import logger
import base64


class GitHubConnector(BaseRepositoryConnector):
    """
    Conector para GitHub
    
    Soporta repositorios, branches, commits, pull requests, etc.
    """
    
    def __init__(self, credentials: Dict[str, Any], organization: Optional[str] = None):
        super().__init__(credentials, organization)
        
    async def connect(self) -> bool:
        """Establece conexión con GitHub"""
        try:
            token = self.credentials.get('token')
            self._client = Github(token)
            
            # Test connection
            user = self._client.get_user()
            logger.info(f"Conectado a GitHub - User: {user.login}")
            return True
            
        except GithubException as e:
            logger.error(f"Error conectando a GitHub: {e}")
            return False
    
    async def validate_credentials(self) -> bool:
        """Valida las credenciales de GitHub"""
        try:
            if not self._client:
                await self.connect()
            
            self._client.get_user()
            return True
            
        except GithubException as e:
            logger.error(f"Credenciales GitHub inválidas: {e}")
            return False
    
    async def list_repositories(self) -> List[Dict[str, Any]]:
        """Lista repositorios"""
        try:
            if self.organization:
                org = self._client.get_organization(self.organization)
                repos = org.get_repos()
            else:
                user = self._client.get_user()
                repos = user.get_repos()
            
            result = []
            for repo in repos:
                result.append({
                    'name': repo.name,
                    'full_name': repo.full_name,
                    'description': repo.description,
                    'private': repo.private,
                    'url': repo.html_url,
                    'default_branch': repo.default_branch,
                    'created_at': str(repo.created_at),
                    'updated_at': str(repo.updated_at)
                })
            
            return result
            
        except GithubException as e:
            logger.error(f"Error listando repositorios: {e}")
            return []
    
    async def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = True
    ) -> Dict[str, Any]:
        """Crea un repositorio"""
        try:
            if self.organization:
                org = self._client.get_organization(self.organization)
                repo = org.create_repo(
                    name=name,
                    description=description or "",
                    private=private,
                    auto_init=True
                )
            else:
                user = self._client.get_user()
                repo = user.create_repo(
                    name=name,
                    description=description or "",
                    private=private,
                    auto_init=True
                )
            
            logger.info(f"Repositorio creado: {repo.full_name}")
            
            return {
                'name': repo.name,
                'full_name': repo.full_name,
                'url': repo.html_url,
                'clone_url': repo.clone_url
            }
            
        except GithubException as e:
            logger.error(f"Error creando repositorio: {e}")
            raise
    
    async def delete_repository(self, repo_name: str) -> bool:
        """Elimina un repositorio"""
        try:
            repo = self._client.get_repo(repo_name)
            repo.delete()
            
            logger.info(f"Repositorio eliminado: {repo_name}")
            return True
            
        except GithubException as e:
            logger.error(f"Error eliminando repositorio: {e}")
            return False
    
    async def create_branch(
        self,
        repo_name: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> Dict[str, Any]:
        """Crea una rama"""
        try:
            repo = self._client.get_repo(repo_name)
            
            # Obtener referencia de la rama base
            source = repo.get_branch(from_branch)
            
            # Crear nueva rama
            ref = repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )
            
            logger.info(f"Rama creada: {branch_name} en {repo_name}")
            
            return {
                'branch': branch_name,
                'ref': ref.ref,
                'sha': ref.object.sha
            }
            
        except GithubException as e:
            logger.error(f"Error creando rama: {e}")
            raise
    
    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main"
    ) -> Dict[str, Any]:
        """Crea un pull request"""
        try:
            repo = self._client.get_repo(repo_name)
            
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            logger.info(f"Pull request creado: #{pr.number} en {repo_name}")
            
            return {
                'number': pr.number,
                'title': pr.title,
                'url': pr.html_url,
                'state': pr.state
            }
            
        except GithubException as e:
            logger.error(f"Error creando pull request: {e}")
            raise
    
    async def commit_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        message: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Crea o actualiza un archivo en el repositorio"""
        try:
            repo = self._client.get_repo(repo_name)
            
            # Verificar si el archivo existe
            try:
                existing_file = repo.get_contents(file_path, ref=branch)
                # Actualizar archivo existente
                result = repo.update_file(
                    path=file_path,
                    message=message,
                    content=content,
                    sha=existing_file.sha,
                    branch=branch
                )
                action = "updated"
            except GithubException:
                # Crear nuevo archivo
                result = repo.create_file(
                    path=file_path,
                    message=message,
                    content=content,
                    branch=branch
                )
                action = "created"
            
            logger.info(f"Archivo {action}: {file_path} en {repo_name}/{branch}")
            
            return {
                'path': file_path,
                'action': action,
                'commit_sha': result['commit'].sha
            }
            
        except GithubException as e:
            logger.error(f"Error en commit: {e}")
            raise
    
    async def get_file_content(
        self,
        repo_name: str,
        file_path: str,
        branch: str = "main"
    ) -> str:
        """Obtiene el contenido de un archivo"""
        try:
            repo = self._client.get_repo(repo_name)
            file_content = repo.get_contents(file_path, ref=branch)
            
            # Decodificar contenido base64
            content = base64.b64decode(file_content.content).decode('utf-8')
            
            return content
            
        except GithubException as e:
            logger.error(f"Error obteniendo contenido: {e}")
            raise
    
    async def list_branches(self, repo_name: str) -> List[Dict[str, Any]]:
        """Lista las ramas de un repositorio"""
        try:
            repo = self._client.get_repo(repo_name)
            branches = repo.get_branches()
            
            return [
                {
                    'name': branch.name,
                    'protected': branch.protected,
                    'commit_sha': branch.commit.sha
                }
                for branch in branches
            ]
            
        except GithubException as e:
            logger.error(f"Error listando ramas: {e}")
            return []
    
    async def create_webhook(
        self,
        repo_name: str,
        webhook_url: str,
        events: List[str] = None
    ) -> Dict[str, Any]:
        """Crea un webhook en el repositorio"""
        try:
            repo = self._client.get_repo(repo_name)
            
            config = {
                'url': webhook_url,
                'content_type': 'json'
            }
            
            events = events or ['push', 'pull_request']
            
            hook = repo.create_hook(
                name='web',
                config=config,
                events=events,
                active=True
            )
            
            logger.info(f"Webhook creado en {repo_name}")
            
            return {
                'id': hook.id,
                'url': webhook_url,
                'events': events,
                'active': hook.active
            }
            
        except GithubException as e:
            logger.error(f"Error creando webhook: {e}")
            raise
