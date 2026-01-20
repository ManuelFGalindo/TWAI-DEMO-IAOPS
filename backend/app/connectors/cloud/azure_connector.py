"""
Conector para Microsoft Azure
"""
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.resource import ResourceManagementClient
from typing import Dict, Any, List, Optional
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
            self.credential = ClientSecretCredential(
                tenant_id=self.credentials.get('tenant_id'),
                client_id=self.credentials.get('client_id'),
                client_secret=self.credentials.get('client_secret')
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
            resource_type: vms, storage, functions, aks, sql, etc.
        """
        try:
            if resource_type == "vms":
                return await self._list_virtual_machines()
            elif resource_type == "storage":
                return await self._list_storage_accounts()
            elif resource_type == "resource_groups":
                return await self._list_resource_groups()
            else:
                logger.warning(f"Tipo de recurso no soportado: {resource_type}")
                return []
                
        except Exception as e:
            logger.error(f"Error listando recursos {resource_type}: {e}")
            return []
    
    async def _list_virtual_machines(self) -> List[Dict[str, Any]]:
        """Lista máquinas virtuales"""
        compute_client = ComputeManagementClient(
            self.credential,
            self.subscription_id
        )
        
        vms = []
        for vm in compute_client.virtual_machines.list_all():
            vms.append({
                'name': vm.name,
                'location': vm.location,
                'vm_size': vm.hardware_profile.vm_size,
                'provisioning_state': vm.provisioning_state
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
                'name': account.name,
                'location': account.location,
                'kind': account.kind,
                'sku': account.sku.name
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
        Despliega infraestructura usando ARM Templates
        
        Args:
            infrastructure_code: ARM Template (JSON)
            parameters: Parámetros del deployment
        """
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
            logger.error(f"Error desplegando infraestructura: {e}")
            raise
