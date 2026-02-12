# QA Test Cases: azd up with Existing Resources

This document provides test cases for validating the `azd up` deployment with existing Azure/Fabric resources.

## Prerequisites

- Azure CLI installed and authenticated
- Azure Developer CLI (`azd`) installed
- Access to an Azure subscription with Fabric capacity
- PowerShell terminal

---

## Test Case 1: Fresh Deployment (Baseline)

**Objective:** Deploy the solution from scratch without any existing resources.

### Steps

1. Open a terminal in the repository root folder
2. Run the following commands:
   ```powershell
   azd auth login
   az login
   azd up
   ```
3. Follow the prompts to select subscription and location
4. Wait for deployment to complete. It takes 20-25 minutes to complete.

### Expected Result

- ✅ Deployment completes successfully
- ✅ New Fabric capacity is created
- ✅ New Fabric workspace is created
- ✅ All resources are provisioned

### Post-Test Actions

**IMPORTANT:** Note down the following values from the deployment output for subsequent test cases:

| Resource | Value |
|----------|-------|
| Fabric Capacity Name | `__________________` |
| Fabric Workspace Name | `__________________` |

---

## Test Case 2: Both Existing Resources (Capacity + Workspace)

**Objective:** Deploy using BOTH existing Fabric capacity AND existing workspace.

### Prerequisites

- Values from Test Case 1
- To ensure deployment is running, delete reports folder from workspace.

### Steps

1. Set environment variables for existing resources:
   ```powershell
   azd env set AZURE_EXISTING_FABRIC_CAPACITY_NAME "<capacity-name-from-test-1>"
   azd env set FABRIC_WORKSPACE_NAME "<workspace-name-from-test-1>"
   ```

2. Run deployment:
   ```powershell
   azd up
   ```

### Expected Result

- ✅ Deployment completes successfully
- ✅ No new Fabric capacity is created (uses existing)
- ✅ No new Fabric workspace is created (uses existing)
- ✅ Deployment reuses the existing resources
- ✅ No errors about duplicate resources

---

## Test Case 3: Existing Capacity Only

**Objective:** Deploy using existing Fabric capacity but create a NEW workspace.

### Prerequisites

- Fabric capacity name from Test Case 1
- Clean environment (or different environment name)

### Steps

1. Initialize a new environment or clear workspace setting:
   ```powershell
   
   azd env set AZURE_EXISTING_FABRIC_CAPACITY_NAME "<capacity-name-from-test-1>"
   <make sure to clean workspace variable if set>
   # Do NOT set FABRIC_WORKSPACE_NAME
   ```

2. Run deployment:
   ```powershell
   azd up
   ```

### Expected Result

- ✅ Deployment completes successfully
- ✅ Uses existing Fabric capacity (no new capacity created)
- ✅ Creates a NEW Fabric workspace
- ✅ Workspace is linked to the existing capacity

---

## Test Case 4: Existing Workspace Only

**Objective:** Deploy using existing Fabric workspace but create a NEW capacity.

### Prerequisites

- Fabric workspace name from Test Case 1
- Clean environment (or different environment name)

### Steps

1. Initialize a new environment or clear capacity setting:
   ```powershell
      
   azd env set FABRIC_WORKSPACE_NAME "<workspace-name-from-test-1>"
   # Do NOT set AZURE_EXISTING_FABRIC_CAPACITY_NAME
   ```

2. Run deployment:
   ```powershell
   azd up
   ```

### Expected Result

- ✅ Deployment completes successfully
- ✅ Creates a NEW Fabric capacity
- ✅ Uses existing Fabric workspace (no new workspace created)
- ✅ Existing workspace content is preserved

---

## Test Summary Table

| Test Case | Existing Capacity | Existing Workspace | Expected Outcome |
|-----------|-------------------|-------------------|------------------|
| 1 | ❌ No | ❌ No | Creates both new |
| 2 | ✅ Yes | ✅ Yes | Reuses both existing |
| 3 | ✅ Yes | ❌ No | Reuses capacity, creates new workspace |
| 4 | ❌ No | ✅ Yes | Creates capacity, reuses workspace |

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_EXISTING_FABRIC_CAPACITY_NAME` | Name of existing Fabric capacity | `udfwfsa-abc12` |
| `FABRIC_WORKSPACE_NAME` | Name of existing Fabric workspace | `udfwfsa_abc12_ws` |

---

## Troubleshooting

### Common Issues

1. **Deployment fails with "resource already exists"**
   - Ensure the existing resource names are correct
   - Verify you have access permissions to the existing resources

2. **Workspace not found error**
   - Confirm the workspace name matches exactly (case-sensitive)
   - Ensure the workspace was not deleted after Test Case 1

3. **Capacity quota exceeded**
   - Check your subscription's Fabric capacity quota
   - Use existing capacity instead of creating new

### Useful Commands

```powershell
# View current environment settings
azd env get-values

# Clear a specific variable
azd env set AZURE_EXISTING_FABRIC_CAPACITY_NAME ""

# Switch between environments
azd env select <environment-name>

# List all environments
azd env list
```
