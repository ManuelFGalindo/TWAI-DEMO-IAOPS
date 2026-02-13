import { api } from './api';

import { DeploymentRequest } from '@/types';

export interface CodeDeploymentRequest {
  client_id: string;
  repo_url: string;
  branch: string;
  resource_id: string;
  resource_type: string;
  environment: string;
}

export const deploymentService = {
  // Desplegar infraestructura
  async deploy(request: DeploymentRequest): Promise<any> {
    const response = await api.post('/deployments/deploy', request);
    return response.data;
  },

  // Desplegar código desde repositorio a recurso cloud
  async deployCode(request: CodeDeploymentRequest): Promise<any> {
    const response = await api.post('/deployments/code', request);
    return response.data;
  },

  // Obtener historial de despliegues
  async getHistory(clientId: string): Promise<any[]> {
    const response = await api.get(`/deployments/history/${clientId}`);
    return response.data;
  }
};
