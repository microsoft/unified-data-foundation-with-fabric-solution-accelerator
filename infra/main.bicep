metadata name = 'Unified data foundation with Fabric solution accelerator'
metadata description = '''CSA CTO Gold Standard Solution Accelerator for Unified Data Foundation with Fabric.
'''
@minLength(3)
@maxLength(16)
@description('Optional. A friendly string representing the application/solution name to give to all resource names in this deployment. This should be 3-16 characters long.')
param solutionName string = 'udff'

@maxLength(5)
@description('Optional. A unique text value for the solution. This is used to ensure resource names are unique for global resources. Defaults to a 5-character substring of the unique string generated from the subscription ID, resource group name, and solution name.')
param solutionUniqueText string = substring(uniqueString(subscription().id, resourceGroup().name, solutionName), 0, 5)

@minLength(3)
@metadata({ azd: { type: 'location' } })
@description('Optional. Azure region for all services. Defaults to the tenant\' location to avoid usage of Microsoft Fabric multi-geo capabilities.')
param location string = resourceGroup().location

@description('Optional. Enable/Disable usage telemetry for module.')
param enableTelemetry bool = true

@description('Required. An array of user object IDs or service principal object IDs that will be assigned the Fabric Capacity Admin role. This can be used to add additional admins beyond the default admin which is the user assigned managed identity created as part of this deployment.')
param fabricAdminMembers array

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

var solutionSuffix = toLower(trim(replace(
  replace(
    replace(replace(replace(replace('${solutionName}${solutionUniqueText}', '-', ''), '_', ''), '.', ''), '/', ''),
    ' ',
    ''
  ),
  '*',
  ''
)))

var userAssignedIdentityResourceName = 'id-${solutionSuffix}'
module userAssignedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: take('avm.res.managed-identity.user-assigned-identity.${userAssignedIdentityResourceName}', 64)
  params: {
    name: userAssignedIdentityResourceName
    location: location
    enableTelemetry: enableTelemetry
  }
}

var fabricCapacityResourceName = 'fc${solutionSuffix}'
module fabricCapacity 'br/public:avm/res/fabric/capacity:0.1.1' = {
  name: take('avm.res.fabric.capacity.${fabricCapacityResourceName}', 64)
  params: {
    adminMembers: union([userAssignedIdentity.outputs.principalId], fabricAdminMembers)
    name: fabricCapacityResourceName
    location: location
    skuName: skuName
  }
}

// Outputs for AZD
@description('The location the resources were deployed to')
output AZURE_LOCATION string = location

@description('The name of the resource group')
output AZURE_RESOURCE_GROUP string = resourceGroup().name

@description('The name of the Fabric capacity resource')
output AZURE_FABRIC_CAPACITY_NAME string = fabricCapacity.outputs.name
