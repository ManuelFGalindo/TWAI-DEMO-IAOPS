# Configuración de Despliegue a Azure

Para que el workflow de GitHub Actions desplegué correctamente a Azure App Service, es necesario configurar las credenciales de Azure.

## 1. Obtener Credenciales de Azure

### Opción A: Usar Azure CLI (Recomendado)

```bash
az ad sp create-for-rbac --name "iaops-deployment" \
  --role contributor \
  --scopes /subscriptions/{subscription-id} \
  --json-auth
```

Reemplaza `{subscription-id}` con tu subscription ID de Azure.

Esto retornará un objeto JSON como:
```json
{
  "clientId": "xxx",
  "clientSecret": "xxx",
  "subscriptionId": "xxx",
  "tenantId": "xxx"
}
```

### Opción B: Usar Azure Portal

1. Ve a Azure Portal → Microsoft Entra ID → App registrations
2. Create new registration
3. Ve a "Certificates & secrets"
4. Crea un nuevo client secret
5. Anota: clientId, clientSecret, tenantId, subscriptionId

## 2. Guardar en GitHub Secrets

En tu repositorio de GitHub:

1. Ve a **Settings** → **Secrets and variables** → **Actions**
2. Crea un nuevo secret llamado `AZURE_CREDENTIALS` con el contenido JSON completo:
   ```json
   {"clientId":"...", "clientSecret":"...", "subscriptionId":"...", "tenantId":"..."}
   ```

   O crea secretos individuales:
   - `AZURE_CLIENT_ID`
   - `AZURE_CLIENT_SECRET`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`

## 3. Actualizar Workflow

El workflow actual (``.github/workflows/deploy.yml`) necesita agregar estos pasos de autenticación:

```yaml
- name: Azure Login
  uses: azure/login@v1
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}
    # O alternativa:
    # client-id: ${{ secrets.AZURE_CLIENT_ID }}
    # tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    # subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

- name: Deploy to App Service
  run: |
    az webapp deployment source config-zip \
      -g ${{ steps.parse.outputs.resource_group }} \
      -n ${{ steps.parse.outputs.resource_name }} \
      --src app.zip
```

## 4. Permisos Necesarios

El Service Principal necesita permisos:
- **Contributor** en el recurso de App Service
- **Reader** en el Resource Group (para listar recursos)

## 5. Flujo Completo de Despliegue

```
Frontend (click "Desplegar")
    ↓
Backend API (/api/v1/deployments/code)
    ↓
CICDDispatcher.dispatch()
    ↓
GitHubActionsHandler:
  1. Crea workflow en .github/workflows/deploy.yml (si no existe)
  2. Dispara el workflow en GitHub
    ↓
GitHub Actions Runner:
  1. Autentica con Azure (Azure Login)
  2. Parsea el Resource ID
  3. Construye el artifact (npm build, etc.)
  4. Despliega a Azure (az webapp deploy)
    ↓
Azure App Service:
  - Código actualizado
  - Aplicación redeployada
```

## 6. Debugging

Si el workflow falla:

1. **Ve a GitHub Actions** en tu repositorio
2. Verifica el último workflow run
3. Expansiona cada step para ver logs detallados
4. Busca errores en:
   - `Azure Login` - check if AZURE_CREDENTIALS is correct
   - `Deploy to App Service` - check if resource exists and naming is correct

## 7. Variables de Entorno en App Service

El App Service también puede necesitar variables de entorno. Configúralas en:

**Azure Portal** → **App Service** → **Configuration** → **Application settings**

Ejemplo:
- `NODE_ENV=production`
- `API_URL=https://api.example.com`

## 8. Verificar Despliegue Exitoso

Después del workflow:

1. Ve a Azure Portal → App Service → peribank-mobile
2. Verifica: **Deployment slots** → **Deployments**
3. O accede a la URL de la aplicación

## Referencias

- [Azure Login Action](https://github.com/azure/login)
- [Azure App Service Deployment](https://learn.microsoft.com/en-us/azure/app-service/deploy-github-actions)
- [Service Principal RBAC](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure)
