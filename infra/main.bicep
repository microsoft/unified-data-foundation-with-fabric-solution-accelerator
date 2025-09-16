metadata name = 'Unified data foundation with Fabric solution accelerator'
metadata description = '''CSA CTO Gold Standard Solution Accelerator for Unified Data Foundation with Fabric.
'''

@minLength(3)
@maxLength(16)
@description('Required. A unique application/solution name for all resources in this deployment. This should be 3-16 characters long.')
param solutionName string

@maxLength(5)
@description('Optional. A unique token for the solution. This is used to ensure resource names are unique for global resources. Defaults to a 5-character substring of the unique string generated from the subscription ID, resource group name, and solution name.')
param solutionUniqueToken string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

@minLength(3)
@metadata({ azd: { type: 'location' } })
@description('Optional. Azure region for all services. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Optional. Specifies the resource tags for all the resources. Tag "azd-env-name" is automatically added to all resources.')
param tags object = {}

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = false

@description('Required. Fabric Workspace ID for the deployment of the solution accelerator.')
param fabricWorkspaceId string = '4fa9ecad-28d2-493e-8f51-08b6a238251d'

@description('Optional. Enable running the deploymentScript from the ARM template. Default is true to run the Python deployment script automatically.')
param enableDeploymentScript bool = true

var allTags = union(
  {
    'azd-env-name': solutionName
  },
  tags
)

var resourcesName = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueToken}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))


var abbrs = loadJsonContent('./abbreviations.json')

@description('Optional created by user name')
param createdBy string = empty(deployer().userPrincipalName) ? '' : split(deployer().userPrincipalName, '@')[0]


// Use a test URL to test code before the code is published to a Public GitHub repository for production use.
// Need to push the code to this public repository to test deployment code. 
// var testBaseURL = 'https://raw.githubusercontent.com/DocGailZhou/TestScripts/main/'

// This is the production URL for the solution accelerator code repository. Currently in private mode. 
// Once the code is published to a public repository, this URL can be used for production deployments.
// var baseURL = 'https://raw.githubusercontent.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator/main/'
var baseURL = 'https://raw.githubusercontent.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator/pipeline-workflow/'


// ========== Resource Group Tag ========== //
resource resourceGroupTags 'Microsoft.Resources/tags@2021-04-01' = {
  name: 'default'
  properties: {
    tags: {
      ...allTags
      TemplateName: 'UDF-Fabric-MAAG'
      CreatedBy: createdBy
      SecurityControl: 'Ignore'
    }
  }
}


module appIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: take('identity-app-${resourcesName}-deployment', 64)
  params: {
    name: '${abbrs.security.managedIdentity}${resourcesName}'
    location: location
    tags: allTags
    enableTelemetry: enableTelemetry
  }
}

#disable-next-line no-deployments-resources
resource avmTelemetry 'Microsoft.Resources/deployments@2024-03-01' = if (enableTelemetry) {
  name: take(
    '46d3xbcp.ptn.sa-unifieddatafoundation.${replace('-..--..-', '.', '-')}.${substring(uniqueString(deployment().name, location), 0, 4)}',
    64
  )
  properties: {
    mode: 'Incremental'
    template: {
      '$schema': 'https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#'
      contentVersion: '1.0.0.0'
      resources: []
      outputs: {
        telemetry: {
          type: 'String'
          value: 'For more information, see https://aka.ms/avm/TelemetryInfo'
        }
      }
    }
  }
}

module deployFabricResources './modules/deploy_fabric_resources.bicep' = {
  name: 'main_deploy_fabric_resourcesscript'
  scope: resourceGroup()
  params: {
    location: location
    identity: appIdentity.outputs.resourceId
    scriptUri: '${baseURL}infra/deploy/fabric/provision_fabric_items.sh'
    baseUrl: baseURL
    fabricWorkspaceId: fabricWorkspaceId
    enableDeploymentScript: enableDeploymentScript
  }
}

// Outputs for AZD
@description('The location the resources were deployed to')
output AZURE_LOCATION string = location

@description('The name of the resource group')
output AZURE_RESOURCE_GROUP string = resourceGroup().name

@description('The managed identity client ID')
output AZURE_CLIENT_ID string = appIdentity.outputs.clientId

@description('The fabric workspace ID used in deployment')
output FABRIC_WORKSPACE_ID string = fabricWorkspaceId
