@description('Specifies the location for resources.')
param location string
param scriptUri string // Full absolute https URI the script to be run.
param fabricWorkspaceId string // Workspace ID for the Fabric resources
param identity string // Fully qualified resource ID for the managed identity.
param enableDeploymentScript bool = false

// Create Azure Container Instance that downloads the script (defined as scriptUri) as /tmp/deploy.sh and run it.
resource create_fabric_resources 'Microsoft.ContainerInstance/containerGroups@2021-09-01' = if (enableDeploymentScript) {
  name: 'create-fabric-resources-${uniqueString(deployment().name)}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity}': {}
    }
  }
  properties: {
    containers: [
      {
        name: 'fabric-deployer'
        properties: {
          image: 'mcr.microsoft.com/azure-cli:2.55.0'
          resources: {
            requests: {
              cpu: 1
              memoryInGB: 1
            }
          }
          command: [
            'bash'
            '-lc'
            'set -euo pipefail; curl -fsSL "${scriptUri}" -o /tmp/deploy.sh; chmod +x /tmp/deploy.sh; /tmp/deploy.sh "${fabricWorkspaceId}"'
          ]
        }
      }
    ]
    restartPolicy: 'Never'
    osType: 'Linux'
  }
}
