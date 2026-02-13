import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Sparkles, Loader2, Server, Cloud, Code } from 'lucide-react';
// import { ArchitectureRequest, Architecture, Client, DeploymentRequest } from '@/types';
import { ArchitectureRequest, Architecture, Client, DeploymentRequest } from '@/types';
import { architectureService } from '@/services/architectureService';
import { clientService } from '@/services/clientService';
import { deploymentService } from '@/services/deploymentService';
import { Alert } from '@/components/Alert';
import toast from 'react-hot-toast';

export function AIGenerator() {
  const [architecture, setArchitecture] = useState<Architecture | null>(null);
  const [loading, setLoading] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [selectedCloud, setSelectedCloud] = useState<string | null>(null);

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<ArchitectureRequest>();

  const selectedClientId = watch('client_id');
  // @ts-ignore - target_clouds is used dynamically
  const watchedCloud = watch('target_clouds');

  useEffect(() => {
    loadClients();
  }, []);

  useEffect(() => {
    if (selectedClientId && clients.length > 0) {
      const client = clients.find(c => c.id === selectedClientId);
      setSelectedClient(client || null);
      if (client) {
        if (client.tech_profile.clouds.length > 0) {
          setValue('target_clouds' as any, client.tech_profile.clouds[0]);
        }
        if (client.tech_profile.standards.infrastructure) {
          setValue('infrastructure_standard', client.tech_profile.standards.infrastructure);
        }
      }
    }
  }, [selectedClientId, clients, setValue]);

  const loadClients = async () => {
    try {
      const data = await clientService.getAll();
      setClients(data);
    } catch (error) {
      console.error('Error loading clients:', error);
      toast.error('Error al cargar clientes');
    }
  };

  const onSubmit = async (data: any) => {
    if (!selectedClient) return;

    setLoading(true);
    try {
      // Guardar cual nube se seleccionó para el despliegue posterior
      setSelectedCloud(data.target_clouds);

      // Parse requirements from string to JSON if it's a string
      const parsedData = {
        ...data,
        target_clouds: [data.target_clouds], // El backend espera una lista
        infrastructure_standard: selectedClient.tech_profile.standards.infrastructure // Usar el del cliente
      };

      if (typeof data.requirements === 'string') {
        try {
          // If it's an empty string, set to empty dict
          if (!data.requirements || (data.requirements as string).trim() === '') {
            parsedData.requirements = {};
          } else {
            parsedData.requirements = JSON.parse(data.requirements as unknown as string);
          }
        } catch (e) {
          toast.error('Error: El campo Requerimientos debe ser un JSON válido');
          setLoading(false);
          return;
        }
      }

      const result = await architectureService.generate(parsedData);
      setArchitecture(result);
      toast.success('Arquitectura generada exitosamente');
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } }; message?: string };
      const errorMessage = axiosError?.response?.data?.detail || axiosError?.message || 'Error al generar arquitectura';
      toast.error(errorMessage);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeploy = async () => {
    if (!architecture || !selectedClient || !architecture.infrastructure_code) return;

    setDeploying(true);
    try {
      const deployRequest: DeploymentRequest = {
        target: {
          client_id: selectedClient.id,
          cloud_provider: (selectedCloud || selectedClient.tech_profile.clouds[0]) as any,
          region: 'eastus', // Default region
          environment: 'dev',
        },
        infrastructure_code: architecture.infrastructure_code,
        architecture_metadata: architecture.architecture as Record<string, unknown>
      };

      await deploymentService.deploy(deployRequest);
      toast.success(`Despliegue completado exitosamente en ${selectedCloud || 'Azure'}`);
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } }; message?: string };
      let errorMessage = axiosError?.response?.data?.detail || axiosError?.message || 'Error en el despliegue';

      // Parse common Azure errors for better UX
      if (errorMessage.includes("Website with given name") && errorMessage.includes("already exists")) {
        errorMessage = "Error: El nombre del App Service ya está en uso globalmente en Azure. Por favor elige un nombre único y regenera.";
      } else if (errorMessage.includes("dnsPrefix") && (errorMessage.includes("already exists") || errorMessage.includes("invalid"))) {
        errorMessage = "Error: El prefijo DNS del cluster AKS es inválido o ya existe. Intenta con otro nombre.";
      } else if (errorMessage.includes("AuthorizationFailed")) {
        errorMessage = "Error de Permisos: La cuenta no tiene permisos suficientes en la suscripción.";
      } else if (errorMessage.includes("InvalidTemplateDeployment")) {
        // Try to extract inner error if possible, otherwise keep generic
        if (errorMessage.includes("The value of parameter dnsPrefix is invalid")) {
          errorMessage = "Error: El prefijo DNS para AKS es inválido.";
        }
      }

      toast.error(errorMessage, { duration: 5000 });
      console.error('Deployment error:', error);
    } finally {
      setDeploying(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Generador de Arquitecturas con IA</h1>
        <p className="mt-2 text-gray-600">
          La IA genera arquitecturas respetando el perfil tecnológico del cliente
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="space-y-6">
          <div className="card">
            <div className="flex items-center space-x-2 mb-6">
              <Sparkles className="w-6 h-6 text-primary-600" />
              <h2 className="text-xl font-semibold text-gray-900">
                Nueva Arquitectura
              </h2>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="label">Cliente</label>
                  <select
                    className="input"
                    {...register('client_id', { required: 'Cliente es requerido' })}
                  >
                    <option value="">Seleccionar cliente...</option>
                    {clients.map(client => (
                      <option key={client.id} value={client.id}>
                        {client.name}
                      </option>
                    ))}
                  </select>
                  {errors.client_id && (
                    <p className="text-sm text-red-600 mt-1">{errors.client_id.message}</p>
                  )}
                </div>

                {selectedClient && (
                  <div>
                    <label className="label">Nube de Destino</label>
                    <select
                      className="input capitalize"
                      {...register('target_clouds' as any, { required: 'Nube es requerida' })}
                    >
                      {selectedClient.tech_profile.clouds.map(cloud => (
                        <option key={cloud} value={cloud}>
                          {cloud}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {selectedClient && (
                <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 text-sm space-y-2">
                  <div className="flex items-center text-blue-800 font-medium mb-2">
                    <Server className="w-4 h-4 mr-2" />
                    Estándares del Cliente
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-blue-600 block text-xs uppercase tracking-wider">IaC</span>
                      <div className="mt-1">
                        <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs capitalize">
                          {selectedClient.tech_profile.standards.infrastructure.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                    <div>
                      <span className="text-blue-600 block text-xs uppercase tracking-wider">CI/CD</span>
                      <div className="mt-1">
                        <span className="bg-purple-100 text-purple-800 px-2 py-0.5 rounded text-xs capitalize">
                          {selectedClient.tech_profile.standards.cicd.replace('-', ' ')}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div>
                <label className="label">Descripción</label>
                <textarea
                  rows={4}
                  className="input"
                  placeholder="Describe lo que necesitas construir..."
                  {...register('description', { required: 'Descripción es requerida' })}
                />
                {errors.description && (
                  <p className="text-sm text-red-600 mt-1">{errors.description.message}</p>
                )}
              </div>

              <div>
                <label className="label">Requerimientos (JSON)</label>
                <textarea
                  rows={3}
                  className="input font-mono text-sm"
                  placeholder='{"scalability": "high", "availability": "99.9%"}'
                  {...register('requirements')}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary w-full flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Generando...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    <span>Generar Arquitectura</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Result */}
        <div className="card h-fit">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">
            Resultado
          </h2>

          {!architecture && !loading && (
            <Alert
              type="info"
              message="Completa el formulario para generar una arquitectura"
            />
          )}

          {loading && (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
            </div>
          )}

          {architecture && !loading && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  Descripción General
                </h3>
                <p className="text-sm text-gray-600">
                  {typeof architecture.architecture === 'object'
                    ? (architecture.architecture as any).architecture_overview || 'Arquitectura generada'
                    : 'Arquitectura generada'}
                </p>
              </div>

              {(architecture.architecture as any)?.components && (architecture.architecture as any).components.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">
                    Componentes ({(architecture.architecture as any).components.length})
                  </h3>
                  <div className="space-y-2">
                    {(architecture.architecture as any).components.map((component: any, index: number) => (
                      <div
                        key={index}
                        className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                      >
                        <p className="font-medium text-gray-900">{component.name || 'Componente'}</p>
                        {component.cloud_service && (
                          <p className="text-sm text-gray-600">{component.cloud_service}</p>
                        )}
                        {component.description && (
                          <p className="text-xs text-gray-500 mt-1">{component.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {architecture.estimated_cost && (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">
                    Estimación de Costos
                  </h3>
                  <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                    {architecture.estimated_cost.monthly_estimate ? (
                      <>
                        <p className="text-lg font-bold text-green-700">
                          {typeof architecture.estimated_cost.monthly_estimate === 'object'
                            ? `$${(architecture.estimated_cost.monthly_estimate as any).min || 0} - $${(architecture.estimated_cost.monthly_estimate as any).max || 0} /mes`
                            : `$${architecture.estimated_cost.monthly_estimate} /mes`}
                        </p>
                        <p className="text-sm text-green-600">
                          {architecture.estimated_cost.currency || 'USD'}
                        </p>
                      </>
                    ) : (
                      <p className="text-sm text-gray-600">Estimación no disponible</p>
                    )}
                  </div>
                </div>
              )}

              {architecture.recommendations && architecture.recommendations.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">
                    Recomendaciones
                  </h3>
                  <ul className="space-y-1">
                    {architecture.recommendations.map((rec: string, index: number) => (
                      <li key={index} className="text-sm text-gray-600 flex items-start">
                        <span className="text-primary-600 mr-2">•</span>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {architecture.infrastructure_code && (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-sm font-medium text-gray-700">
                      <Code className="w-4 h-4" />
                      <span>Código de Infraestructura</span>
                      {selectedClient && (
                        <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded uppercase">
                          {selectedClient.tech_profile.standards.infrastructure.replace('_', ' ')}
                        </span>
                      )}
                    </div>
                  </div>
                  <pre className="p-4 bg-gray-900 text-gray-100 overflow-x-auto text-sm font-mono leading-relaxed max-h-96">
                    {architecture.infrastructure_code}
                  </pre>

                  {/* Deploy Button */}
                  <div className="bg-gray-50 px-4 py-3 border-t border-gray-200 flex justify-end">
                    <button
                      onClick={handleDeploy}
                      disabled={deploying}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                    >
                      {deploying ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Desplegando...
                        </>
                      ) : (
                        <>
                          <Cloud className="w-4 h-4 mr-2" />
                          Desplegar en {selectedCloud || 'Cloud'}
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Debug: Ver datos raw */}
              <div className="mt-4">
                <details className="text-xs">
                  <summary className="cursor-pointer text-gray-500 hover:text-gray-700">
                    Ver datos completos (debug)
                  </summary>
                  <pre className="mt-2 p-4 bg-gray-50 rounded-lg overflow-x-auto">
                    {JSON.stringify(architecture, null, 2)}
                  </pre>
                </details>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
