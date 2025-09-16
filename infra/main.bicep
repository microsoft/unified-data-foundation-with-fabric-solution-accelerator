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
param fabricWorkspaceId string

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

// ========== Resource Group Tag ========== //
resource resourceGroupTags 'Microsoft.Resources/tags@2021-04-01' = {
  name: 'default'
  properties: {
    tags: {
      ...allTags
      TemplateName: 'MAAG'
      CreatedBy: createdBy
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

// Storage account removed - deployment will not stage files in blob storage

// Use a test URL to test code before the code is published to a Public GitHub repository for production use.
// Need to push the code to this public repository to test deployment code. 
var testBaseURL = 'https://raw.githubusercontent.com/DocGailZhou/TestScripts/main/'

// This is the production URL for the solution accelerator code repository. Currently in private mode. 
// Once the code is published to a public repository, this URL can be used for production deployments.
var baseURL = 'https://raw.githubusercontent.com/microsoft/unified-data-foundation-with-fabric-solution-accelerator/main/'

module deployFabricResources './modules/deploy_fabric_resources.bicep' = {
  name: 'main_deploy_fabric_resourcesscript'
  scope: resourceGroup()
  params: {
    location: location
    identity: appIdentity.outputs.resourceId
    scriptUri: '${testBaseURL}infra/deploy/fabric/provision_fabric_items.sh'
    fabricWorkspaceId: fabricWorkspaceId
    enableDeploymentScript: enableDeploymentScript
  }
}

// storageAccount resource moved above to ensure dependencies and readability
