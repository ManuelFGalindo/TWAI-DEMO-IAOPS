"""
Conector para Microsoft Azure
"""
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.resource import ResourceManagementClient
from typing import Dict, Any, List, Optional
import subprocess
import os
import tempfile
from app.connectors.cloud.base import BaseCloudConnector
from app.core.logging import logger


class AzureConnector(BaseCloudConnector):
    """
    Conector para Microsoft Azure
    
    Soporta: VMs, Storage Accounts, Functions, AKS, Azure SQL, etc.
    """
    
    def __init__(self, credentials: Dict[str, Any], region: Optional[str] = "eastus"):
        super().__init__(credentials, region)
        self.credential = None
        self.subscription_id = credentials.get('subscription_id')
        
    async def connect(self) -> bool:
        """Establece conexión con Azure"""
        try:
            tenant_id = self.credentials.get('tenant_id', '')
            client_id = self.credentials.get('client_id', '')
            client_secret = self.credentials.get('client_secret', '')
            
            if not client_id or not client_secret:
                logger.info("Azure Connect: No credentials provided, attempting DefaultAzureCredential")
                self.credential = DefaultAzureCredential()
            else:
                logger.info(f"Azure Connect: Tenant={tenant_id[:4]}...{tenant_id[-4:] if len(tenant_id) > 8 else ''}, Client={client_id[:4]}...{client_id[-4:] if len(client_id) > 8 else ''}")
                logger.debug(f"Azure Secret Check: Start={client_secret[:3]}, End={client_secret[-3:] if len(client_secret) > 6 else ''}, Length={len(client_secret)}")
                
                self.credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
            
            # Test connection
            resource_client = ResourceManagementClient(
                self.credential,
                self.subscription_id
            )
            
            # List resource groups to validate
            list(resource_client.resource_groups.list())
            
            logger.info(f"Conectado a Azure - Subscription: {self.subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error conectando a Azure: {e}")
            return False
    
    async def validate_credentials(self) -> bool:
        """Valida las credenciales de Azure"""
        try:
            if not self.credential:
                await self.connect()
            
            resource_client = ResourceManagementClient(
                self.credential,
                self.subscription_id
            )
            list(resource_client.resource_groups.list())
            return True
            
        except Exception as e:
            logger.error(f"Credenciales Azure inválidas: {e}")
            return False
    
    async def list_resources(self, resource_type: str) -> List[Dict[str, Any]]:
        """
        Lista recursos de Azure
        
        Args:
            resource_type: vms, storage, functions, aks, sql, app_services, containers, etc.
        """
        try:
            if resource_type == "vms":
                return await self._list_virtual_machines()
            elif resource_type == "storage":
                return await self._list_storage_accounts()
            elif resource_type == "resource_groups":
                return await self._list_resource_groups()
            elif resource_type == "app_services":
                return await self._list_app_services()
            elif resource_type == "functions":
                return await self._list_functions()
            elif resource_type == "containers":
                return await self._list_container_instances()
            elif resource_type == "aks":
                return await self._list_kubernetes_clusters()
            else:
                logger.warning(f"Tipo de recurso no soportado: {resource_type}")
                return []
                
        except Exception as e:
            logger.error(f"Error listando recursos {resource_type}: {e}")
            return []
    
    async def _list_virtual_machines(self) -> List[Dict[str, Any]]:
        """Lista máquinas virtuales con estado enriquecido"""
        compute_client = ComputeManagementClient(
            self.credential,
            self.subscription_id
        )
        
        vms = []
        for vm in compute_client.virtual_machines.list_all():
            # Simplificamos para no saturar con llamadas instance_view en el listado masivo
            # pero mapeamos provisioning_state a status
            status = 'unknown'
            if vm.provisioning_state.lower() == 'succeeded':
                status = 'running' # Asumimos running si está succeeded para el listado rápido
            elif vm.provisioning_state.lower() == 'deleting':
                status = 'stopped'
                
            vms.append({
                'id': vm.id,
                'name': vm.name,
                'type': 'virtual_machine',
                'location': vm.location,
                'vm_size': vm.hardware_profile.vm_size,
                'provisioning_state': vm.provisioning_state,
                'status': status,
                'behavior': {
                    'power_state': 'Consulting...',
                    'last_modified': None
                }
            })
        
        return vms
    
    async def _list_storage_accounts(self) -> List[Dict[str, Any]]:
        """Lista cuentas de storage"""
        storage_client = StorageManagementClient(
            self.credential,
            self.subscription_id
        )
        
        accounts = []
        for account in storage_client.storage_accounts.list():
            accounts.append({
                'id': account.id,
                'name': account.name,
                'type': 'storage_account',
                'location': account.location,
                'kind': account.kind,
                'sku': account.sku.name,
                'status': 'active' if account.provisioning_state.lower() == 'succeeded' else 'pending'
            })
        
        return accounts
    
    async def _list_resource_groups(self) -> List[Dict[str, Any]]:
        """Lista grupos de recursos"""
        resource_client = ResourceManagementClient(
            self.credential,
            self.subscription_id
        )
        
        groups = []
        for group in resource_client.resource_groups.list():
            groups.append({
                'name': group.name,
                'location': group.location,
                'provisioning_state': group.properties.provisioning_state
            })
        
        return groups

    async def _list_app_services(self) -> List[Dict[str, Any]]:
        """Lista App Services (Web Apps)"""
        try:
            from azure.mgmt.web import WebSiteManagementClient
            
            web_client = WebSiteManagementClient(
                self.credential,
                self.subscription_id
            )
            
            apps = []
            for app in web_client.web_apps.list():
                apps.append({
                    'id': app.id,
                    'name': app.name,
                    'type': 'app_service',
                    'location': app.location,
                    'state': app.state,
                    'default_host_name': app.default_host_name,
                    'kind': app.kind,
                    'enabled': app.enabled
                })
            
            return apps
        except Exception as e:
            logger.error(f"Error listing App Services: {e}")
            return []

    async def _list_functions(self) -> List[Dict[str, Any]]:
        """Lista Azure Functions"""
        try:
            from azure.mgmt.web import WebSiteManagementClient
            
            web_client = WebSiteManagementClient(
                self.credential,
                self.subscription_id
            )
            
            functions = []
            for app in web_client.web_apps.list():
                # Azure Functions son Web Apps con kind='functionapp'
                if app.kind and 'functionapp' in app.kind.lower():
                    functions.append({
                        'id': app.id,
                        'name': app.name,
                        'type': 'function_app',
                        'location': app.location,
                        'state': app.state,
                        'default_host_name': app.default_host_name,
                        'kind': app.kind,
                        'enabled': app.enabled
                    })
            
            return functions
        except Exception as e:
            logger.error(f"Error listing Azure Functions: {e}")
            return []

    async def _list_container_instances(self) -> List[Dict[str, Any]]:
        """Lista Azure Container Instances"""
        try:
            from azure.mgmt.containerinstance import ContainerInstanceManagementClient
            
            container_client = ContainerInstanceManagementClient(
                self.credential,
                self.subscription_id
            )
            
            containers = []
            for container_group in container_client.container_groups.list():
                containers.append({
                    'id': container_group.id,
                    'name': container_group.name,
                    'type': 'container_instance',
                    'location': container_group.location,
                    'provisioning_state': container_group.provisioning_state,
                    'os_type': container_group.os_type,
                    'restart_policy': container_group.restart_policy,
                    'ip_address': container_group.ip_address.ip if container_group.ip_address else None
                })
            
            return containers
        except Exception as e:
            logger.error(f"Error listing Container Instances: {e}")
            return []

    async def _list_kubernetes_clusters(self) -> List[Dict[str, Any]]:
        """Lista Azure Kubernetes Service (AKS) clusters"""
        try:
            from azure.mgmt.containerservice import ContainerServiceClient
            
            aks_client = ContainerServiceClient(
                self.credential,
                self.subscription_id
            )
            
            clusters = []
            for cluster in aks_client.managed_clusters.list():
                clusters.append({
                    'id': cluster.id,
                    'name': cluster.name,
                    'type': 'kubernetes_cluster',
                    'location': cluster.location,
                    'provisioning_state': cluster.provisioning_state,
                    'kubernetes_version': cluster.kubernetes_version,
                    'node_resource_group': cluster.node_resource_group,
                    'fqdn': cluster.fqdn
                })
            
            return clusters
        except Exception as e:
            logger.error(f"Error listing AKS clusters: {e}")
            return []
    
    async def create_resource(
        self,
        resource_type: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crea un recurso en Azure"""
        try:
            if resource_type == "vm":
                return await self._create_virtual_machine(config)
            elif resource_type == "storage":
                return await self._create_storage_account(config)
            elif resource_type == "resource_group":
                return await self._create_resource_group(config)
            else:
                raise ValueError(f"Tipo de recurso no soportado: {resource_type}")
                
        except Exception as e:
            logger.error(f"Error creando recurso {resource_type}: {e}")
            raise
    
    async def _create_resource_group(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un grupo de recursos"""
        resource_client = ResourceManagementClient(
            self.credential,
            self.subscription_id
        )
        
        rg_name = config['name']
        location = config.get('location', self.region)
        
        result = resource_client.resource_groups.create_or_update(
            rg_name,
            {'location': location, 'tags': config.get('tags', {})}
        )
        
        return {
            'name': result.name,
            'location': result.location,
            'id': result.id
        }
    
    async def _create_virtual_machine(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una máquina virtual"""
        compute_client = ComputeManagementClient(
            self.credential,
            self.subscription_id
        )
        
        # Este es un ejemplo simplificado
        # En producción requiere más configuración (networking, etc.)
        
        vm_parameters = {
            'location': config.get('location', self.region),
            'hardware_profile': {
                'vm_size': config.get('vm_size', 'Standard_B1s')
            },
            'storage_profile': {
                'image_reference': config.get('image_reference', {
                    'publisher': 'Canonical',
                    'offer': 'UbuntuServer',
                    'sku': '18.04-LTS',
                    'version': 'latest'
                })
            },
            'os_profile': {
                'computer_name': config['vm_name'],
                'admin_username': config['admin_username'],
                'admin_password': config['admin_password']
            },
            'network_profile': {
                'network_interfaces': config['network_interfaces']
            }
        }
        
        async_vm_creation = compute_client.virtual_machines.begin_create_or_update(
            config['resource_group'],
            config['vm_name'],
            vm_parameters
        )
        
        logger.info(f"Creando VM: {config['vm_name']}")
        
        return {
            'name': config['vm_name'],
            'resource_group': config['resource_group'],
            'status': 'creating'
        }
    
    async def _create_storage_account(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una cuenta de storage"""
        storage_client = StorageManagementClient(
            self.credential,
            self.subscription_id
        )
        
        storage_params = {
            'sku': {'name': config.get('sku', 'Standard_LRS')},
            'kind': config.get('kind', 'StorageV2'),
            'location': config.get('location', self.region)
        }
        
        async_storage_creation = storage_client.storage_accounts.begin_create(
            config['resource_group'],
            config['account_name'],
            storage_params
        )
        
        logger.info(f"Creando Storage Account: {config['account_name']}")
        
        return {
            'name': config['account_name'],
            'resource_group': config['resource_group'],
            'status': 'creating'
        }
    
    async def delete_resource(
        self,
        resource_type: str,
        resource_id: str
    ) -> bool:
        """Elimina un recurso de Azure"""
        try:
            resource_group, resource_name = resource_id.split('/')
            
            if resource_type == "vm":
                compute_client = ComputeManagementClient(
                    self.credential,
                    self.subscription_id
                )
                compute_client.virtual_machines.begin_delete(
                    resource_group,
                    resource_name
                )
            elif resource_type == "storage":
                storage_client = StorageManagementClient(
                    self.credential,
                    self.subscription_id
                )
                storage_client.storage_accounts.delete(
                    resource_group,
                    resource_name
                )
            else:
                raise ValueError(f"Tipo de recurso no soportado: {resource_type}")
            
            logger.info(f"Recurso {resource_type}/{resource_id} eliminado")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando recurso: {e}")
            return False
    
    async def get_resource_status(
        self,
        resource_type: str,
        resource_id: str
    ) -> Dict[str, Any]:
        """Obtiene el estado de un recurso"""
        try:
            resource_group, resource_name = resource_id.split('/')
            
            if resource_type == "vm":
                compute_client = ComputeManagementClient(
                    self.credential,
                    self.subscription_id
                )
                vm = compute_client.virtual_machines.get(
                    resource_group,
                    resource_name
                )
                return {
                    'name': vm.name,
                    'provisioning_state': vm.provisioning_state,
                    'location': vm.location
                }
            else:
                return {'status': 'unknown'}
                
        except Exception as e:
            logger.error(f"Error obteniendo estado: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def deploy_infrastructure(
        self,
        infrastructure_code: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Despliega infraestructura usando ARM Templates o Bicep via CLI
        
        Args:
            infrastructure_code: ARM Template (JSON) o Bicep
            parameters: Parámetros del deployment
        """
        # Intentar determinar si es Bicep (si no es JSON válido o tiene extensión .bicep en metadatos)
        is_bicep = False
        try:
            import json
            json.loads(infrastructure_code)
        except json.JSONDecodeError:
            is_bicep = True
            
        if is_bicep or parameters.get('use_cli', True):
            return await self._deploy_with_cli(infrastructure_code, parameters, is_bicep)

        # Fallback a SDK para JSON puro si no se fuerza CLI
        try:
            resource_client = ResourceManagementClient(
                self.credential,
                self.subscription_id
            )
            
            deployment_name = parameters.get('deployment_name', 'iaops-deployment')
            resource_group = parameters.get('resource_group', 'iaops-rg')
            
            import json
            template = json.loads(infrastructure_code)
            
            deployment_properties = {
                'mode': 'Incremental',
                'template': template,
                'parameters': parameters.get('template_parameters', {})
            }
            
            # Crear RG si no existe
            resource_client.resource_groups.create_or_update(
                resource_group,
                {'location': parameters.get('location', self.region)}
            )
            
            deployment_async = resource_client.deployments.begin_create_or_update(
                resource_group,
                deployment_name,
                {'properties': deployment_properties}
            )
            
            logger.info(f"ARM Template deployment iniciado: {deployment_name}")
            
            return {
                'deployment_name': deployment_name,
                'resource_group': resource_group,
                'status': 'creating'
            }
            
        except Exception as e:
            logger.error(f"Error desplegando infraestructura SDK: {e}")
            raise

    async def _deploy_with_cli(
        self,
        code: str,
        parameters: Dict[str, Any],
        is_bicep: bool
    ) -> Dict[str, Any]:
        """Despliega usando Azure CLI"""
        import subprocess
        import os
        import tempfile
        
        deployment_name = parameters.get('deployment_name', 'iaops-deploy-cli')
        resource_group = parameters.get('resource_group', 'iaops-rg')
        location = parameters.get('location', self.region)
        
        try:
            # 1. Login
            client_id = self.credentials.get('client_id')
            client_secret = self.credentials.get('client_secret')
            tenant_id = self.credentials.get('tenant_id')

            if client_id and client_secret:
                logger.info(f"Iniciando login con Azure CLI (Service Principal: {client_id[:4]}...)...")
                subprocess.run([
                    "az", "login", "--service-principal",
                    "-u", client_id,
                    "--password", client_secret,
                    "--tenant", tenant_id
                ], check=True, capture_output=True)
            else:
                logger.info("Iniciando login con Azure CLI (Managed Identity/Default)...")
                subprocess.run([
                    "az", "login", "--identity"
                ], check=True, capture_output=True)
            
            subprocess.run([
                "az", "account", "set", "--subscription", self.subscription_id
            ], check=True, capture_output=True)
            
            # 2. Crear Resource Group
            logger.info(f"Creando Resource Group: {resource_group}")
            subprocess.run([
                "az", "group", "create",
                "--name", resource_group,
                "--location", location
            ], check=True, capture_output=True)
            
            # 3. Guardar archivo
            suffix = ".bicep" if is_bicep else ".json"
            with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            
            # 4. Desplegar
            logger.info(f"Ejecutando deployment: {deployment_name}")
            cmd = [
                "az", "deployment", "group", "create",
                "--name", deployment_name,
                "--resource-group", resource_group,
                "--template-file", tmp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            os.unlink(tmp_path)
            
            if result.returncode != 0:
                raise Exception(f"Azure CLI Error: {result.stderr}")
            
            return {
                'deployment_name': deployment_name,
                'resource_group': resource_group,
                'status': 'success',
                'output': result.stdout
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error ejecutando comando CLI: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            raise Exception(f"Deployment failed: {e}")
        except Exception as e:
            logger.error(f"Error en deployment CLI: {e}")
            raise
