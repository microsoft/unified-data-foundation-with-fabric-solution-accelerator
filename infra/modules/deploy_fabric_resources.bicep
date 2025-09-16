@description('Specifies the location for resources.')
param location string
param scriptUri string // Full absolute https URI the script to be run.
param fabricWorkspaceId string // Workspace ID for the Fabric resources
param identity string // Fully qualified resource ID for the managed identity.
param enableDeploymentScript bool = false

// Create Azure Container Instance that downloads the script (defined as scriptUri) as /tmp/deploy.sh and run it.
// resource create_fabric_resources 'Microsoft.ContainerInstance/containerGroups@2021-09-01' = if (enableDeploymentScript) {
//   name: 'create-fabric-resources-${uniqueString(deployment().name)}'
//   location: location
//   identity: {
//     type: 'UserAssigned'
//     userAssignedIdentities: {
//       '${identity}': {}
//     }
//   }
//   properties: {
//     containers: [
//       {
//         name: 'fabric-deployer'
//         properties: {
//           image: 'mcr.microsoft.com/azure-cli:2.55.0'
//           resources: {
//             requests: {
//               cpu: 1
//               memoryInGB: 1
//             }
//           }
//           command: [
//             'bash'
//             '-c'
//             'set -euo pipefail; apk add --no-cache curl; curl -fsSL "${scriptUri}" -o /tmp/provision_fabric_items.sh; chmod +x /tmp/provision_fabric_items.sh; /tmp/provision_fabric_items.sh "${fabricWorkspaceId}"'
//           ]
//         }
//       }
//     ]
//     restartPolicy: 'Never'
//     osType: 'Linux'
//   }
// }

resource copy_demo_Data 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  kind:'AzureCLI'
  name: 'copy_demo_Data'
  location: location
  identity:{
    type:'UserAssigned'
    userAssignedIdentities: {
      '${identity}' : {}
    }
  }
  properties: {
    azCliVersion: '2.52.0'
    primaryScriptUri: scriptUri
    arguments: fabricWorkspaceId
    timeout: 'PT1H'
    retentionInterval: 'PT1H'
    cleanupPreference:'OnSuccess'
  }
}
