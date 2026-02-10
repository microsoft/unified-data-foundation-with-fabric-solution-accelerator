metadata name = 'Unified data foundation with Fabric solution accelerator'
metadata description = '''CSA CTO Gold Standard Solution Accelerator for Unified Data Foundation with Fabric.
'''
@minLength(1)
@maxLength(20)
@description('Optional. A friendly string representing the application/solution name to give to all resource names in this deployment. This should be 3-16 characters long.')
param solutionName string = 'udfwfsa'

@maxLength(5)
@description('Optional. A unique text value for the solution. This is used to ensure resource names are unique for global resources. Defaults to a 5-character substring of the unique string generated from the subscription ID, resource group name, and solution name.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

@minLength(3)
@metadata({ azd: { type: 'location' } })
@description('Optional. Azure region for all services. Defaults to the tenant\' location to avoid usage of Microsoft Fabric multi-geo capabilities.')
param location string = resourceGroup().location

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Optional. An array of user object IDs or service principal object IDs that will be assigned the Fabric Capacity Admin role. This can be used to add additional admins beyond the default admin which is the user assigned managed identity created as part of this deployment.')
param fabricAdminMembers array = []

@allowed([
  'F2'
  'F4'
  'F8'
  'F16'
  'F32'
  'F64'
  'F128'
  'F256'
  'F512'
  'F1024'
  'F2048'
])
@description('Optional. SKU tier of the Fabric resource.')
param skuName string = 'F2'

@description('Optional. Name of an existing Fabric capacity to use. If empty, a new capacity will be created.')
param existingFabricCapacityName string = ''

@description('Optional. Name of an existing Fabric workspace to use. If empty, a new workspace will be created during post-deployment.')
param existingFabricWorkspaceName string = ''

var useExistingFabricCapacity = !empty(existingFabricCapacityName)
var useExistingFabricWorkspace = !empty(existingFabricWorkspaceName)

var solutionSuffix = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))

// ============================================================================
// FABRIC CAPACITY - Create new or reference existing
// ============================================================================

var fabricCapacityResourceName = useExistingFabricCapacity ? existingFabricCapacityName : 'fc${solutionSuffix}'
var fabricCapacityDefaultAdmins = [deployer().objectId]
var fabricTotalAdminMembers = union(fabricCapacityDefaultAdmins, fabricAdminMembers)

// Create new Fabric capacity (if no existing specified)
module newFabricCapacity 'br/public:avm/res/fabric/capacity:0.1.1' = if (!useExistingFabricCapacity) {
  name: take('avm.res.fabric.capacity.${fabricCapacityResourceName}', 64)
  params: {
    name: fabricCapacityResourceName
    location: location
    enableTelemetry: enableTelemetry
    skuName: skuName
    adminMembers: fabricTotalAdminMembers
  }
}

// Resolved capacity name (either existing or newly created)
var resolvedFabricCapacityName = useExistingFabricCapacity ? existingFabricCapacityName : newFabricCapacity.outputs.name

// ============================================================================
// FABRIC WORKSPACE - Use existing or create new (handled in post-deployment)
// ============================================================================

var resolvedFabricWorkspaceName = useExistingFabricWorkspace ? existingFabricWorkspaceName : ''

// ============================================================================
// OUTPUTS
// ============================================================================

@description('The location the resources were deployed to')
output AZURE_LOCATION string = location

@description('The name of the resource group')
output AZURE_RESOURCE_GROUP string = resourceGroup().name

@description('The name of the Fabric capacity resource')
output AZURE_FABRIC_CAPACITY_NAME string = resolvedFabricCapacityName

@description('Whether an existing Fabric capacity was used')
output AZURE_FABRIC_CAPACITY_IS_EXISTING bool = useExistingFabricCapacity

@description('The identities added as Fabric Capacity Admin members')
output AZURE_FABRIC_CAPACITY_ADMINISTRATORS array = fabricTotalAdminMembers

@description('The name of the Fabric workspace (if existing was specified)')
output AZURE_FABRIC_WORKSPACE_NAME string = resolvedFabricWorkspaceName

@description('Whether an existing Fabric workspace was used')
output AZURE_FABRIC_WORKSPACE_IS_EXISTING bool = useExistingFabricWorkspace

@description('The unique solution suffix of the deployed resources')
output SOLUTION_SUFFIX string = solutionSuffix
