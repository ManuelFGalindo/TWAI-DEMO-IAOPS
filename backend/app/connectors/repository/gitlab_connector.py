"""
Conector para GitLab
"""
import gitlab
from typing import Dict, Any, List, Optional
from app.connectors.repository.base import BaseRepositoryConnector
from app.core.logging import logger


class GitLabConnector(BaseRepositoryConnector):
    """Conector para GitLab"""
    
    def __init__(self, credentials: Dict[str, Any], organization: Optional[str] = None):
        super().__init__(credentials, organization)
        self.gitlab_url = credentials.get('url', 'https://gitlab.com')
        
    async def connect(self) -> bool:
        """Establece conexión con GitLab"""
        try:
            token = self.credentials.get('token')
            self._client = gitlab.Gitlab(self.gitlab_url, private_token=token)
            self._client.auth()
            
            user = self._client.user
            logger.info(f"Conectado a GitLab - User: {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error conectando a GitLab: {e}")
            return False
    
    async def validate_credentials(self) -> bool:
        """Valida las credenciales de GitLab"""
        return await self.connect()
    
    async def list_repositories(self) -> List[Dict[str, Any]]:
        """Lista repositorios (proyectos)"""
        try:
            if self.organization:
                group = self._client.groups.get(self.organization)
                projects = group.projects.list(all=True)
            else:
                projects = self._client.projects.list(owned=True, all=True)
            
            return [
                {
                    'name': p.name,
                    'full_name': p.path_with_namespace,
                    'description': p.description,
                    'url': p.web_url,
                    'default_branch': p.default_branch
                }
                for p in projects
            ]
            
        except Exception as e:
            logger.error(f"Error listando repositorios: {e}")
            return []
    
    async def create_repository(self, name: str, description: Optional[str] = None, private: bool = True) -> Dict[str, Any]:
        """Crea un repositorio"""
        try:
            project_data = {
                'name': name,
                'description': description or '',
                'visibility': 'private' if private else 'public',
                'initialize_with_readme': True
            }
            
            if self.organization:
                group = self._client.groups.get(self.organization)
                project_data['namespace_id'] = group.id
            
            project = self._client.projects.create(project_data)
            
            return {
                'name': project.name,
                'full_name': project.path_with_namespace,
                'url': project.web_url
            }
            
        except Exception as e:
            logger.error(f"Error creando repositorio: {e}")
            raise
    
    async def delete_repository(self, repo_name: str) -> bool:
        """Elimina un repositorio"""
        try:
            project = self._client.projects.get(repo_name)
            project.delete()
            return True
        except Exception as e:
            logger.error(f"Error eliminando repositorio: {e}")
            return False
    
    async def create_branch(self, repo_name: str, branch_name: str, from_branch: str = "main") -> Dict[str, Any]:
        """Crea una rama"""
        try:
            project = self._client.projects.get(repo_name)
            branch = project.branches.create({'branch': branch_name, 'ref': from_branch})
            
            return {'branch': branch.name, 'commit': branch.commit['id']}
        except Exception as e:
            logger.error(f"Error creando rama: {e}")
            raise
    
    async def create_pull_request(self, repo_name: str, title: str, body: str, head_branch: str, base_branch: str = "main") -> Dict[str, Any]:
        """Crea un merge request"""
        try:
            project = self._client.projects.get(repo_name)
            mr = project.mergerequests.create({
                'source_branch': head_branch,
                'target_branch': base_branch,
                'title': title,
                'description': body
            })
            
            return {'number': mr.iid, 'title': mr.title, 'url': mr.web_url, 'state': mr.state}
        except Exception as e:
            logger.error(f"Error creando merge request: {e}")
            raise
    
    async def commit_file(self, repo_name: str, file_path: str, content: str, message: str, branch: str = "main") -> Dict[str, Any]:
        """Crea o actualiza un archivo"""
        try:
            project = self._client.projects.get(repo_name)
            
            data = {
                'branch': branch,
                'commit_message': message,
                'actions': [
                    {
                        'action': 'create',
                        'file_path': file_path,
                        'content': content
                    }
                ]
            }
            
            commit = project.commits.create(data)
            
            return {'path': file_path, 'commit_sha': commit.id}
        except Exception as e:
            logger.error(f"Error en commit: {e}")
            raise
    
    async def get_file_content(self, repo_name: str, file_path: str, branch: str = "main") -> str:
        """Obtiene el contenido de un archivo"""
        try:
            project = self._client.projects.get(repo_name)
            file = project.files.get(file_path=file_path, ref=branch)
            
            import base64
            return base64.b64decode(file.content).decode('utf-8')
        except Exception as e:
            logger.error(f"Error obteniendo contenido: {e}")
            raise
