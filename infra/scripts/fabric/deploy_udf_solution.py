import os
import glob
import time
import sys
import json
import base64
import re
import requests
import uuid
from typing import Optional
from fabric_api import create_fabric_client, create_workspace_fabric_client, FabricApiError, FabricWorkspaceApiClient
from graph_api import create_graph_client, GraphApiError
from powerbi_api import *

####################
# Helper Functions #
####################


def build_folder_path_mapping(folders: list) -> dict:
    """Build a mapping of full folder paths to folder IDs."""
    folder_lookup = {f['id']: f for f in folders}
    path_map = {}

    def build_path(folder_id: str) -> str:
        if folder_id not in folder_lookup:
            return ""

        folder = folder_lookup[folder_id]
        name = folder['displayName']
        parent_id = folder.get('parentFolderId')

        if not parent_id:
            return name

        parent_path = build_path(parent_id)
        return f"{parent_path}/{name}"

    for folder in folders:
        full_path = build_path(folder['id'])
        path_map[full_path] = folder['id']

    return path_map


def create_fabric_directory_structure(workspace_client: FabricWorkspaceApiClient, folder_path: str, existing_folder_map: dict) -> str:
    """
    Create a complete folder hierarchy using workspace client.

    Args:
        workspace_client: Fabric workspace API client instance
        folder_path: Full path separated by forward slashes
        existing_folder_map: Pre-built mapping of folder paths to IDs

    Returns:
        Final folder ID
    """
    # Check if folder already exists
    if folder_path in existing_folder_map:
        return existing_folder_map[folder_path]

    # Split path and create recursively
    path_parts = folder_path.split('/')

    if len(path_parts) == 1:
        # Root folder
        folder_id = workspace_client.create_folder(path_parts[0])
        existing_folder_map[folder_path] = folder_id
        return folder_id
    else:
        # Ensure parent exists
        parent_path = '/'.join(path_parts[:-1])
        parent_id = create_fabric_directory_structure(
            workspace_client, parent_path, existing_folder_map)

        # Create this folder
        folder_name = path_parts[-1]
        folder_id = workspace_client.create_folder(folder_name, parent_id)
        existing_folder_map[folder_path] = folder_id
        return folder_id


def create_lakehouse_directory_structure(file_system_client, lakehouse_root_path: str, folder_path: str) -> None:
    """Create directory structure in a lakehouse for UDFWF data organization."""
    if not folder_path or folder_path == '.':
        return

    full_path = f"{lakehouse_root_path}/{folder_path}".replace('\\', '/')

    try:
        # Check if directory exists
        directory_client = file_system_client.get_directory_client(full_path)
        directory_client.get_directory_properties()
    except Exception:
        try:
            # Create parent directories first
            parent_path = os.path.dirname(folder_path)
            if parent_path and parent_path != '.':
                create_lakehouse_directory_structure(
                    file_system_client, lakehouse_root_path, parent_path)

            # Create the directory
            directory_client = file_system_client.get_directory_client(
                full_path)
            directory_client.create_directory()
            print(f"  ✅ Created directory: {os.path.basename(folder_path)}")
        except Exception as e:
            print(f"❌ ERROR: Failed to create directory {full_path}: {str(e)}")
            print(f"   Solution: Check OneLake connectivity and permissions")
            sys.exit(1)


def is_valid_guid(value):
    """Check if a string is a valid GUID format."""
    import uuid
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def detect_principal_type(admin_identifier, graph_client=None):
    """
    Detect if an identifier is a user or service principal and resolve to object ID.
    
    Args:
        admin_identifier: User UPN, object ID (GUID), or application ID (GUID)
        graph_client: Optional Graph API client (will create one if not provided)
    
    Returns:
        Tuple of (principal_type, object_id, principal_data)
        - principal_type: "User" or "ServicePrincipal" 
        - object_id: The object ID of the principal
        - principal_data: Full principal object from Graph API
        
    Raises:
        ValueError: If identifier cannot be resolved
        GraphApiError: If Graph API calls fail
    """
    try:
        # Create Graph client if not provided
        if graph_client is None:
            graph_client = create_graph_client()
        
        # Use Graph API to resolve the principal
        principal_type, object_id, principal_data = graph_client.resolve_principal(admin_identifier)
        
        return principal_type, object_id, principal_data
        
    except GraphApiError as e:
        # Convert Graph API errors to ValueError for backward compatibility
        raise ValueError(f"Unable to resolve principal '{admin_identifier}': {str(e)}")
    except Exception as e:
        # Fallback to original logic if Graph API is not available
        print(f"  ⚠️ WARNING: Graph API lookup failed for '{admin_identifier}': {str(e)}")
        print(f"     Falling back to basic identifier pattern detection...")
        
        if is_valid_guid(admin_identifier):
            return "ServicePrincipal", admin_identifier, {"id": admin_identifier, "displayName": "Unknown"}
        elif "@" in admin_identifier and "." in admin_identifier:
            return "User", admin_identifier, {"id": admin_identifier, "userPrincipalName": admin_identifier, "displayName": "Unknown"}
        else:
            raise ValueError(
                f"Unable to determine if '{admin_identifier}' is a user UPN or service principal GUID")


def get_existing_admin_principals(fabric_client, workspace_id):
    """Get set of existing admin principal IDs for duplicate checking."""
    try:
        print("  🔍 Checking existing workspace role assignments...")
        assignments = fabric_client.get_workspace_role_assignments(workspace_id, get_all=True)
        
        existing_principals = set()
        admin_count = 0
        
        for assignment in assignments:
            if assignment.get('role') == 'Admin':
                principal = assignment.get('principal', {})
                principal_id = principal.get('id')
                
                if principal_id:
                    existing_principals.add(principal_id.lower())
                    admin_count += 1
                    
                    # Add UPN for users to handle both ID and UPN lookups
                    if principal.get('type') == 'User':
                        upn = principal.get('userDetails', {}).get('userPrincipalName')
                        if upn:
                            existing_principals.add(upn.lower())
        
        print(f"  📊 Found {admin_count} existing workspace administrator(s)")
        return existing_principals
        
    except Exception as e:
        print(f"  ⚠️ WARNING: Could not retrieve existing role assignments: {str(e)}")
        print("     Will proceed but may create duplicates")
        return set()


def add_workspace_admin(fabric_client, workspace_id, admin_identifier, existing_principals, graph_client):
    """Add a single workspace administrator with simplified error handling."""
    # Check if already exists
    if admin_identifier.lower() in existing_principals:
        print(f"  ⏭️ Skipping '{admin_identifier}' - already a workspace administrator")
        return {'status': 'skipped', 'message': 'Already exists'}
    
    try:
        # Try to resolve principal type using Graph API
        principal_type, object_id, principal_data = detect_principal_type(admin_identifier, graph_client)
        
        if object_id.lower() in existing_principals:
            print(f"  ⏭️ Skipping '{admin_identifier}' - already a workspace administrator")
            existing_principals.add(admin_identifier.lower())  # Prevent future duplicates
            return {'status': 'skipped', 'message': 'Already exists (by object ID)'}
        
        display_name = principal_data.get('displayName', 'Unknown')
        print(f"  🔐 Adding {principal_type.lower()} administrator: {admin_identifier} ({display_name})")
        
        # Add role assignment based on type
        if principal_type == "User":
            fabric_client.add_workspace_role_assignment(
                workspace_id=workspace_id,
                principal_id=object_id,
                principal_type=principal_type,
                role="Admin",
                display_name=display_name,
                user_principal_name=principal_data.get('userPrincipalName', admin_identifier)
            )
        else:  # ServicePrincipal
            fabric_client.add_workspace_role_assignment(
                workspace_id=workspace_id,
                principal_id=object_id,
                principal_type=principal_type,
                role="Admin",
                display_name=display_name,
                aad_app_id=principal_data.get('appId')
            )
        
        print(f"  ✅ Successfully added '{admin_identifier}' as workspace administrator")
        existing_principals.add(object_id.lower())
        existing_principals.add(admin_identifier.lower())
        return {'status': 'success', 'message': 'Added successfully'}
        
    except (ValueError, GraphApiError) as e:
        return {'status': 'failed', 'message': f'Principal type detection failed: {str(e)}'}
        
    except FabricApiError as e:
        error_hints = {
            400: "Verify the identifier is correct and the principal exists",
            403: "Ensure you have Admin permissions on this workspace", 
            404: "Check if the principal exists in your Azure AD tenant"
        }
        hint = error_hints.get(e.status_code, "Check API permissions and principal validity")
        return {'status': 'failed', 'message': f'API error ({e.status_code}): {hint}'}
        
    except Exception as e:
        return {'status': 'failed', 'message': f'Unexpected error: {str(e)}'}


def add_workspace_admin_by_object_id(fabric_client, workspace_id, object_id, existing_principals):
    """Add workspace administrator by object ID using fallback logic to try both User and ServicePrincipal types."""
    # Check if already exists
    if object_id.lower() in existing_principals:
        print(f"  ⏭️ Skipping '{object_id}' - already a workspace administrator")
        return {'status': 'skipped', 'message': 'Already exists'}
    
    print(f"  🔐 Adding administrator by Object ID: {object_id}")
    print(f"     Will try both User and ServicePrincipal types...")
    
    # Try both User and ServicePrincipal types
    for principal_type in ["User", "ServicePrincipal"]:
        try:
            print(f"     Trying as {principal_type}...")
            fabric_client.add_workspace_role_assignment(
                workspace_id=workspace_id,
                principal_id=object_id,
                principal_type=principal_type,
                role="Admin"
            )
            print(f"  ✅ Successfully added '{object_id}' as workspace administrator ({principal_type})")
            existing_principals.add(object_id.lower())
            return {'status': 'success', 'message': f'Added as {principal_type}'}
        except FabricApiError as e:
            print(f"     Failed as {principal_type}: API error ({e.status_code})")
            continue
        except Exception as e:
            print(f"     Failed as {principal_type}: {str(e)}")
            continue
    
    return {'status': 'failed', 'message': 'Failed to add as both User and ServicePrincipal types'}


def get_required_env_var(var_name: str) -> str:
    """Get a required environment variable or exit with error.
    
    Args:
        var_name: Name of the environment variable to retrieve
        
    Returns:
        Value of the environment variable
        
    Raises:
        SystemExit: If the environment variable is not set
    """
    value = os.getenv(var_name)
    if not value:
        print(f"❌ Missing environment variable: {var_name}")
        sys.exit(1)
    return value


####################
# Variables set up #
####################

solution_name = "Unified Data Foundation"
script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up three levels from infra/scripts/fabric to repo root
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

##############################
# Environment Variable Setup #
##############################

# Load configuration from environment variables
capacity_name = get_required_env_var("AZURE_FABRIC_CAPACITY_NAME")
solution_suffix = get_required_env_var("AZURE_SOLUTION_SUFFIX")

# Optional environment variables with defaults
workspace_name = os.getenv("AZURE_FABRIC_WORKSPACE_NAME",f"{solution_name} - {solution_suffix}")
fabric_admins_str = os.getenv("AZURE_FABRIC_ADMIN_MEMBERS")
fabric_admins_by_object_id_str = os.getenv("AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID")

# Process admin lists from environment variables
fabric_admins = []
fabric_admins_by_object_id = []

if fabric_admins_str:
    try:
        import json
        fabric_admins = json.loads(fabric_admins_str)
    except json.JSONDecodeError:
        print(f"⚠️ Warning: Failed to parse AZURE_FABRIC_ADMIN_MEMBERS as JSON, treating as empty list")
        fabric_admins = []

if fabric_admins_by_object_id_str:
    try:
        import json
        fabric_admins_by_object_id = json.loads(fabric_admins_by_object_id_str)
    except json.JSONDecodeError:
        print(f"⚠️ Warning: Failed to parse AZURE_FABRIC_ADMIN_MEMBERS_BY_OBJECT_ID as JSON, treating as empty list")
        fabric_admins_by_object_id = []


print(f"🚀 Starting {solution_name} deployment to Microsoft Fabric")
print(f"📋 Target capacity: {capacity_name}")
print(f"📋 Solution suffix: {solution_suffix}")
print(f"📋 Workspace name: {workspace_name} (auto-generated)")
if fabric_admins:
    print(f"📋 Fabric admins: {', '.join(fabric_admins)}")
if fabric_admins_by_object_id:
    print(f"📋 Fabric admins by object ID: {', '.join(fabric_admins_by_object_id)}")
print("-" * 60)

##########################
# Clients authentication #
##########################

print("🔐 Authenticating clients...")
# Initialize Power BI client
try:
    powerbi_client = create_powerbi_client()
    powerbi_client.set_powerbi_auth_token()
    print("✅ Power BI client authenticated successfully")
except Exception as e:
    print(f"❌ ERROR: Failed to authenticate Power BI client")
    print(f"   Details: {str(e)}")
    print("   Solution: Please ensure you are logged in with Azure CLI: az login")
    sys.exit(1)

# Initialize Fabric API client
try:
    fabric_client = create_fabric_client()
    print("✅ Fabric API client authenticated successfully")
except Exception as e:
    print(f"❌ ERROR: Failed to authenticate with Fabric APIs")
    print(f"   Details: {str(e)}")
    print("   Solution: Please ensure you are logged in with Azure CLI: az login")
    sys.exit(1)

# Initialize Graph API client
try:
    graph_client = create_graph_client()
    print("✅ Graph API client authenticated successfully")
except Exception as e:
    print(f"❌ ERROR: Failed to authenticate with Graph APIs")
    print(f"   Details: {str(e)}")
    print("   Solution: Please ensure you are logged in with Azure CLI: az login")
    sys.exit(1)

#############
# Workspace #
#############
# Docs: https://learn.microsoft.com/rest/api/fabric/admin/workspaces

try:
    # Get capacity ID from capacity name
    print(f"🔍 Looking up capacity: '{capacity_name}'")
    capacities = fabric_client.get_capacities()
    capacity = next(
        (c for c in capacities if c['displayName'].lower() == capacity_name.lower()), None)

    if not capacity:
        print(f"❌ ERROR: Capacity '{capacity_name}' not found")
        print("   Available capacities:")
        for cap in capacities:
            print(f"   - {cap['displayName']} (ID: {cap['id']})")
        sys.exit(1)

    capacity_id = capacity['id']
    print(f"✅ Found capacity: '{capacity['displayName']}' (ID: {capacity_id})")
    print(f"   SKU: {capacity.get('sku', 'N/A')}")
    print(f"   State: {capacity.get('state', 'N/A')}")
    print(f"   Region: {capacity.get('region', 'N/A')}")

    # Handle workspace creation or lookup
    # If no workspace name provided, use default name
    if not workspace_name:
        workspace_name = workspace_default_name
        print(
            f"📋 No workspace name provided, using default: '{workspace_name}'")

    # Check if workspace with the name already exists
    print(f"🔍 Looking for existing workspace: '{workspace_name}'")
    workspaces = fabric_client.get_workspaces()
    workspace = next(
        (w for w in workspaces if w['displayName'].lower() == workspace_name.lower()), None)

    if workspace:
        workspace_id = workspace['id']
        print(
            f"✅ Found existing workspace: '{workspace_name}' (ID: {workspace_id})")

        # Assign the existing workspace to the specified capacity
        print(f"🔄 Assigning workspace to capacity: '{capacity_name}'")
        fabric_client.assign_workspace_to_capacity(workspace_id, capacity_id)
        print(f"✅ Workspace assigned to capacity: '{capacity_name}'")
    else:
        # Create new workspace with the specified name
        print(f"🏗️  Creating new workspace: '{workspace_name}'")
        workspace_id = fabric_client.create_workspace(
            workspace_name, capacity_id)
        print(f"✅ Created workspace: '{workspace_name}' (ID: {workspace_id})")

except FabricApiError as e:
    if e.status_code == 401:
        print(f"⚠️ WARNING: Unauthorized access to Fabric APIs. Please review your Fabric permissions and Ensure you have proper Fabric licensing and permissions.")
        print("   📋 Check the following resources:")
        print("   • Fabric licenses: https://learn.microsoft.com/fabric/enterprise/licenses")
        print("   • Identity support: https://learn.microsoft.com/rest/api/fabric/articles/identity-support")
        print("   • Create Entra app with appropriate Fabric permissions: https://learn.microsoft.com/rest/api/fabric/articles/get-started/create-entra-app")
        sys.exit(0)
    elif e.status_code == 404:
        print(f"❌ ERROR: Resource not found")
    elif e.status_code == 403:
        print(f"❌ ERROR: Access denied")
        print("   Solution: Ensure you have appropriate permissions")
    else:
        print(f"❌ ERROR: Fabric API error")
    print(f"   Status Code: {e.status_code}")
    print(f"   Details: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: Unexpected error during workspace setup: {str(e)}")
    sys.exit(1)

# Create workspace-scoped client for all operations
print("🔗 Creating workspace-scoped Fabric client...")
try:
    workspace_fabric_client = create_workspace_fabric_client(workspace_id)
    print("✅ Workspace-scoped client created successfully")
except Exception as e:
    print(f"❌ Failed to create workspace-scoped client: {str(e)}")
    sys.exit(1)

############################
# Workspace administrators #
############################

# Initialize admin tracking variables for final summary
admin_assignments_added = 0
admin_assignments_skipped = 0

# Get existing admin principals for duplicate checking (shared between both processing phases)
existing_admin_principals = get_existing_admin_principals(fabric_client, workspace_id)

# Phase 1: Process fabricAdmins (UPNs and object IDs with Graph API resolution)
if fabric_admins:
    print("👥 Managing workspace administrators (Phase 1: fabricAdmins)")
    
    # Process each administrator with simplified tracking
    results = {'added': 0, 'skipped': 0, 'failed': 0, 'errors': []}
    
    for admin_identifier in fabric_admins:
        result = add_workspace_admin(
            fabric_client, workspace_id, admin_identifier, 
            existing_admin_principals, graph_client
        )
        
        # Update counters based on result
        if result['status'] == 'success':
            results['added'] += 1
        elif result['status'] == 'skipped':
            results['skipped'] += 1
        else:  # failed
            results['failed'] += 1
            results['errors'].append(f"{admin_identifier}: {result['message']}")
            print(f"  ❌ ERROR: Failed to add '{admin_identifier}': {result['message']}")

    # Update global variables for final summary
    admin_assignments_added += results['added']
    admin_assignments_skipped += results['skipped']

    # Print summary
    print(f"  📊 Phase 1 Administrator assignment summary:")
    print(f"     • Added: {results['added']}")
    print(f"     • Skipped (already admin): {results['skipped']}")
    print(f"     • Failed: {results['failed']}")
    print(f"     • Total requested: {len(fabric_admins)}")

    # Show error details if any failures occurred
    if results['errors']:
        print(f"  ⚠️ WARNING: {results['failed']} administrator assignment(s) failed:")
        for error in results['errors'][:3]:  # Show first 3 errors
            print(f"     • {error}")
        if len(results['errors']) > 3:
            print(f"     • ... and {len(results['errors']) - 3} more error(s)")
        print("  📋 Note: Workspace deployment will continue. You can manually add administrators later if needed.")

else:
    print("👥 No fabricAdmins specified - skipping Phase 1 admin assignment")

# Phase 2: Process fabricAdminsByObjectId (Object IDs with fallback logic)
if fabric_admins_by_object_id:
    print("👥 Managing workspace administrators (Phase 2: fabricAdminsByObjectId)")
    
    # Process each object ID with fallback logic
    results_by_id = {'added': 0, 'skipped': 0, 'failed': 0, 'errors': []}
    
    for object_id in fabric_admins_by_object_id:
        result = add_workspace_admin_by_object_id(
            fabric_client, workspace_id, object_id, existing_admin_principals
        )
        
        # Update counters based on result
        if result['status'] == 'success':
            results_by_id['added'] += 1
        elif result['status'] == 'skipped':
            results_by_id['skipped'] += 1
        else:  # failed
            results_by_id['failed'] += 1
            results_by_id['errors'].append(f"{object_id}: {result['message']}")
            print(f"  ❌ ERROR: Failed to add '{object_id}': {result['message']}")

    # Update global variables for final summary
    admin_assignments_added += results_by_id['added']
    admin_assignments_skipped += results_by_id['skipped']

    # Print summary
    print(f"  📊 Phase 2 Administrator assignment summary:")
    print(f"     • Added: {results_by_id['added']}")
    print(f"     • Skipped (already admin): {results_by_id['skipped']}")
    print(f"     • Failed: {results_by_id['failed']}")
    print(f"     • Total requested: {len(fabric_admins_by_object_id)}")

    # Show error details if any failures occurred
    if results_by_id['errors']:
        print(f"  ⚠️ WARNING: {results_by_id['failed']} object ID assignment(s) failed:")
        for error in results_by_id['errors'][:3]:  # Show first 3 errors
            print(f"     • {error}")
        if len(results_by_id['errors']) > 3:
            print(f"     • ... and {len(results_by_id['errors']) - 3} more error(s)")
        print("  📋 Note: Workspace deployment will continue. You can manually add administrators later if needed.")

else:
    print("👥 No fabricAdminsByObjectId specified - skipping Phase 2 admin assignment")

# Final summary message
if not fabric_admins and not fabric_admins_by_object_id:
    print("👥 No workspace administrators specified")
    print("   Note: Use --fabricAdmins for UPNs/identifiers or --fabricAdminsByObjectId for object IDs")


####################
# Folder structure #
####################
# Docs: https://learn.microsoft.com/rest/api/fabric/core/folders

# Prepare variables
fabric_folder_path_lakehouses = 'lakehouses'
fabric_folder_path_notebooks = 'notebooks'
fabric_folder_path_notebooks_bronze_to_silver = 'notebooks/bronze_to_silver'
fabric_folder_path_notebooks_data_management = 'notebooks/data_management'
fabric_folder_path_notebooks_schema = 'notebooks/schema'
fabric_folder_path_notebooks_silver_to_gold = 'notebooks/silver_to_gold'
fabric_folder_path_reports = 'reports'
udfwf_fabric_folders = [
    fabric_folder_path_lakehouses,
    fabric_folder_path_notebooks_bronze_to_silver,
    fabric_folder_path_notebooks_data_management,
    fabric_folder_path_notebooks_schema,
    fabric_folder_path_notebooks_silver_to_gold,
    fabric_folder_path_reports
]

# Create folder structure using workspace client
try:
    print(f"📁 Creating folder structure for '{solution_name}' solution")

    # Get existing folders using workspace client
    existing_folders = workspace_fabric_client.get_folders()
    fabric_folders = build_folder_path_mapping(existing_folders)
    
    # Create hierarchy of folders using workspace client
    for udfwf_folder_path in udfwf_fabric_folders:
        if udfwf_folder_path in fabric_folders:
            print(f"  📁 Folder '{udfwf_folder_path}' already exists")
        else:
            try:
                folder_id = create_fabric_directory_structure(
                    workspace_fabric_client, udfwf_folder_path, fabric_folders)
                print(f"  ✅ Created folder '{udfwf_folder_path}'")
            except Exception as e:
                print(f"❌ ERROR: Failed to create folder '{udfwf_folder_path}': {str(e)}")
                sys.exit(1)

except FabricApiError as e:
    print(f"❌ ERROR: Failed to manage folders: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: Unexpected error managing folders: {str(e)}")
    sys.exit(1)

##############
# Lakehouses #
##############
# Docs: https://learn.microsoft.com/rest/api/fabric/lakehouse/items

# Variables
udfwf_lakehouse_bronze_name = 'maag_bronze'
udfwf_lakehouse_silver_name = 'maag_silver'
udfwf_lakehouse_gold_name = 'maag_gold'
udfwf_lakehouses = {
    udfwf_lakehouse_bronze_name,
    udfwf_lakehouse_silver_name,
    udfwf_lakehouse_gold_name
}
lakehouse_folder_id = fabric_folders.get(fabric_folder_path_lakehouses)
fabric_lakehouses = {}

# Get existing lakehouses and create new ones
print(f"🏠 Setting up lakehouses (Bronze, Silver, Gold)")
try:
    # Get existing lakehouses using workspace client
    print(f"  📋 Checking for existing lakehouses in workspace...")
    
    existing_lakehouses = workspace_fabric_client.get_lakehouses()

    # Build mapping of existing lakehouses by name
    for lakehouse in existing_lakehouses:
        fabric_lakehouses[lakehouse['displayName']] = lakehouse

    print(f"  📊 Found {len(existing_lakehouses)} existing lakehouse(s)")

    # Create UDFWF lakehouses
    for lakehouse_name in udfwf_lakehouses:
        if lakehouse_name in fabric_lakehouses:
            print(f"  🏠 Lakehouse '{lakehouse_name}' already exists")
        else:
            print(f"  🏗️ Creating lakehouse '{lakehouse_name}'...")
            try:
                # Use workspace client
                lakehouse = workspace_fabric_client.create_lakehouse(
                    display_name=lakehouse_name,
                    description=f"UDFWF {lakehouse_name.split('_')[-1].title()} layer lakehouse for data processing",
                    folder_id=lakehouse_folder_id,
                    enable_schemas=True,
                    wait_for_lro=True
                )
                fabric_lakehouses[lakehouse_name] = workspace_fabric_client.get_lakehouse(lakehouse['id'])

                print(f"  ✅ Lakehouse '{lakehouse_name}' created successfully")

            except FabricApiError as e:
                print(f"❌ ERROR: Failed to create lakehouse '{lakehouse_name}': {e}")
                print(f"   Solution: Check workspace permissions and quotas")
                sys.exit(1)
            except Exception as e:
                print(
                    f"❌ ERROR: Unexpected error creating lakehouse '{lakehouse_name}': {str(e)}")
                print(f"   Solution: Verify workspace configuration and try again")
                sys.exit(1)

except FabricApiError as e:
    print(f"❌ ERROR: Failed to manage lakehouses: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: Unexpected error managing lakehouses: {str(e)}")
    sys.exit(1)

#######################
# Lakehouse CSV files #
#######################
# Docs: https://learn.microsoft.com/fabric/onelake/onelake-access-python

# Prepare variables
samples_local_folder_path = os.path.join(repo_root, 'infra', 'data')
bronze_lakehouse = fabric_lakehouses[udfwf_lakehouse_bronze_name]
bronze_lakehouse_onelake_root_path = f"{bronze_lakehouse['displayName']}.Lakehouse/Files"

# Get all CSV files in 'infra/data/samples_fabric'
csv_pattern = os.path.join(samples_local_folder_path, '**', '*.csv')
csv_file_paths = glob.glob(csv_pattern, recursive=True)

# Connect to bronze lakehouse using workspace client
print(f"📊 Uploading sample data to bronze lakehouse")
try:
    # Use workspace client
    udfwf_wfs_client = workspace_fabric_client.get_workspace_file_system_client(workspace_name)
except Exception as e:
    print(f"❌ ERROR: Failed to connect to OneLake: {str(e)}")
    print("   Solution: Ensure you have proper permissions and the workspace is accessible")
    sys.exit(1)

# Create folder structure for CSV files
created_folders = set()

for local_file_path in csv_file_paths:
    # Get relative path from samples folder
    relative_file_path = os.path.relpath(
        local_file_path, samples_local_folder_path)
    bronze_datalake_file_path = os.path.join(
        bronze_lakehouse_onelake_root_path, relative_file_path)
    relative_folder_path = os.path.dirname(relative_file_path)
    bronze_datalake_folder_path = os.path.join(
        bronze_lakehouse_onelake_root_path, relative_folder_path)
    # Create folders in lakehouse
    if relative_folder_path and relative_folder_path != '.' and relative_folder_path not in created_folders:
        try:
            create_lakehouse_directory_structure(
                udfwf_wfs_client, bronze_lakehouse_onelake_root_path, relative_folder_path)
            created_folders.add(relative_folder_path)
        except Exception as e:
            print(
                f"❌ ERROR: Failed to create folder structure '{relative_folder_path}': {str(e)}")
            sys.exit(1)

    # Upload file
    file_name = os.path.basename(local_file_path)
    try:
        bronze_datalake_file_client = udfwf_wfs_client.get_file_client(
            bronze_datalake_file_path)
        with open(local_file_path, "rb") as data:
            bronze_datalake_file_client.upload_data(data, overwrite=True)
        print(f"  ✅ Uploaded '{file_name}' to '{relative_file_path}'")
    except Exception as e:
        print(f"❌ ERROR: Failed to upload file '{file_name}': {str(e)}")
        sys.exit(1)

#############
# Notebooks #
#############
# Docs: https://learn.microsoft.com/rest/api/fabric/notebook/items

# Prepare variables
fabric_notebooks = {}
notebooks_directory = os.path.join(repo_root, 'src', 'fabric', 'notebooks')

# Item structure: {local notebook path: [source lakehouse name, destination lakehouse name, fabric folder path]}
udfwf_notebooks_path_lakehouse_folder = {
    # src\fabric\notebooks
    os.path.join(notebooks_directory, 'run_bronze_to_silver.ipynb'): [None, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks],
    os.path.join(notebooks_directory, 'run_silver_to_gold.ipynb'): [None, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks],

    # src\fabric\notebooks\bronze_to_silver notebooks
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_finance_account.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_finance_invoice.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_finance_payment.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesadb_order.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesadb_orderLine.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesadb_orderPayment.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesfabric_order.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesfabric_orderLine.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_salesfabric_orderPayment.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_customer.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_customeraccount.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_customerRelationshipType.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_customerTradeName.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_location.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_product.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],
    os.path.join(notebooks_directory, 'bronze_to_silver', 'bronze_to_silver_shared_productCategory.ipynb'): [udfwf_lakehouse_bronze_name, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_bronze_to_silver],

    # src\fabric\notebooks\data_management notebooks
    os.path.join(notebooks_directory, 'data_management', 'drop_all_tables_gold.ipynb'): [None, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_data_management],
    os.path.join(notebooks_directory, 'data_management', 'drop_all_tables_silver.ipynb'): [None, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_data_management],
    os.path.join(notebooks_directory, 'data_management', 'trouble_shooting.ipynb'): [None, None, fabric_folder_path_notebooks_data_management],
    os.path.join(notebooks_directory, 'data_management', 'truncate_all_tables_gold.ipynb'): [None, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_data_management],
    os.path.join(notebooks_directory, 'data_management', 'truncate_all_tables_silver.ipynb'): [None, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_data_management],

    # src\fabric\notebooks\schema notebooks
    os.path.join(notebooks_directory, 'schema', 'model_finance_gold.ipynb'): [None, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_salesadb_gold.ipynb'): [None, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_salesfabric_gold.ipynb'): [None, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_shared_gold.ipynb'): [None, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_finance_silver.ipynb'): [None, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_salesadb_silver.ipynb'): [None, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_salesfabric_silver.ipynb'): [None, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_schema],
    os.path.join(notebooks_directory, 'schema', 'model_shared_silver.ipynb'): [None, udfwf_lakehouse_silver_name, fabric_folder_path_notebooks_schema],

    # src\fabric\notebooks\silver_to_gold notebooks
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_finance_account.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_finance_invoice.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_finance_payment.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_sales_order_line.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_sales_order_payment.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_sales_order.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesadb_order.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesadb_orderLine.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesadb_orderPayment.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesfabric_order.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesfabric_orderLine.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_salesfabric_orderPayment.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_customer.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_customeraccount.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_customerRelationshipType.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_customerTradeName.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_location.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_product.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold],
    os.path.join(notebooks_directory, 'silver_to_gold', 'silver_to_gold_shared_productCategory.ipynb'): [udfwf_lakehouse_silver_name, udfwf_lakehouse_gold_name, fabric_folder_path_notebooks_silver_to_gold]
}

# Obtain existing notebooks
print(f"📓 Deploying notebooks to workspace")

# Prepare notebook specifications for batch upload
notebook_specs = []
for notebook_path, (source_lakehouse_name, targeted_lakehouse_name, folder_path) in udfwf_notebooks_path_lakehouse_folder.items():
    notebook_specs.append({
        'path': notebook_path,
        'source_lakehouse': source_lakehouse_name,
        'target_lakehouse': targeted_lakehouse_name,
        'folder_path': folder_path
    })

# Deploy notebooks using optimized batch processing
try:
    # Inline batch_upload_notebooks logic
    # Get existing notebooks using workspace client
    try:
        existing_notebooks = workspace_fabric_client.get_notebooks()
    except Exception as e:
        print(f"❌ ERROR: Failed to get existing notebooks: {str(e)}")
        print("   Solution: Check workspace permissions and connectivity")
        sys.exit(1)

    fabric_notebooks = {}
    upload_jobs = []  # Track LRO jobs for batch monitoring

    for i, spec in enumerate(notebook_specs, 1):
        notebook_path = spec['path']
        source_lakehouse_name = spec.get('source_lakehouse')
        target_lakehouse_name = spec.get('target_lakehouse')
        folder_path = spec['folder_path']

        notebook_name = os.path.basename(notebook_path).replace('.ipynb', '')
        folder_id = fabric_folders.get(folder_path)

        if not folder_id:
            print(
                f"❌ ERROR: Folder not found for path '{folder_path}', cannot deploy '{notebook_name}'")
            print(f"   Solution: Ensure folder structure was created successfully")
            sys.exit(1)

        # Get lakehouse objects
        target_lakehouse = fabric_lakehouses.get(
            target_lakehouse_name) if target_lakehouse_name else None
        source_lakehouse = fabric_lakehouses.get(
            source_lakehouse_name) if source_lakehouse_name else None
        existing_notebook_id = existing_notebooks.get(notebook_name)

        try:
            # Inline upload_notebook logic
            # Read and transform notebook content
            with open(notebook_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Transform notebook content by replacing UDFWF-specific placeholders
            # Replace workspace placeholders
            pattern = r'WORKSPACE_NAME\s*=\s*\\"([^\\"]+)\\"'
            content = re.sub(
                pattern, f'WORKSPACE_ID = \\"{workspace_id}\\"', content)
            content = content.replace('{WORKSPACE_NAME}', '{WORKSPACE_ID}')

            # Replace lakehouse placeholders
            if source_lakehouse:
                pattern = r'SOURCE_LAKEHOUSE_NAME\s*=\s*\\"([^\\"]+)\\"'
                content = re.sub(
                    pattern, f'SOURCE_LAKEHOUSE_ID = \\"{source_lakehouse["id"]}\\"', content)
                content = content.replace(
                    '{SOURCE_LAKEHOUSE_NAME}', '{SOURCE_LAKEHOUSE_ID}')

            # Fix ABFSS paths for UDFWF project structure
            content = content.replace(
                'abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{SOURCE_LAKEHOUSE_ID}.Lakehouse/',
                'abfss://{WORKSPACE_ID}@onelake.dfs.fabric.microsoft.com/{SOURCE_LAKEHOUSE_ID}/'
            )

            notebook_json = json.loads(content)

            # Update notebook metadata with UDFWF lakehouse configuration
            if target_lakehouse:
                # Ensure metadata structure exists
                if 'metadata' not in notebook_json:
                    notebook_json['metadata'] = {}

                if 'dependencies' not in notebook_json['metadata']:
                    notebook_json['metadata']['dependencies'] = {}

                # Set lakehouse configuration
                notebook_json['metadata']['dependencies']['lakehouse'] = {
                    'default_lakehouse': target_lakehouse['id'],
                    'default_lakehouse_name': target_lakehouse['displayName'],
                    'default_lakehouse_workspace_id': target_lakehouse['workspaceId']
                }

            # Prepare API data
            notebook_base64 = base64.b64encode(
                json.dumps(notebook_json).encode('utf-8'))
            notebook_data = {
                "displayName": os.path.basename(notebook_path).replace('.ipynb', ''),
                "definition": {
                    "format": "ipynb",
                    "parts": [{
                        "path": "notebook-content.ipynb",
                        "payload": notebook_base64.decode('utf-8'),
                        "payloadType": "InlineBase64"
                    }]
                },
                "folderId": folder_id
            }

            # Upload or update using workspace client
            if existing_notebook_id:
                print(f"  ✅ Updating notebook '{notebook_name}'")
                response = workspace_fabric_client.update_notebook(
                    existing_notebook_id, notebook_data, wait_for_lro=False)
            else:
                print(f"  ✅ Creating notebook '{notebook_name}'")
                response = workspace_fabric_client.create_notebook(
                    notebook_data, wait_for_lro=False)

            if response.status_code == 202:
                # Track LRO for batch monitoring
                job_monitoring_url = response.headers.get('Location')
                if job_monitoring_url:
                    upload_jobs.append({
                        'notebook_name': notebook_name,
                        'job_url': job_monitoring_url,
                        'start_time': time.time()
                    })
            elif response.ok:
                fabric_notebooks[notebook_name] = response.json().get(
                    'id', 'unknown')
            else:
                print(
                    f"❌ ERROR: Failed to upload '{notebook_name}': {response.text}")
                sys.exit(1)

        except Exception as e:
            print(f"❌ ERROR: Error uploading '{notebook_name}': {str(e)}")
            print(f"   Solution: Check notebook file integrity and workspace permissions")
            sys.exit(1)

    # Check jobs completion
    if upload_jobs:
        print(f"  ⏳ Waiting for {len(upload_jobs)} notebook upload jobs...")
        # Inline wait_for_upload_completion logic
        pending_jobs = upload_jobs.copy()
        start_time = time.time()
        max_wait_time = 600
        check_interval = 5

        while pending_jobs and (time.time() - start_time) < max_wait_time:

            jobs_to_remove = []
            for job in pending_jobs:
                try:
                    # Use the full job URL directly with proper headers
                    response = requests.get(
                        job['job_url'], headers=fabric_client.get_headers())

                    if response.ok:
                        job_result = response.json()
                        notebook_id = job_result.get('id', 'unknown')
                        fabric_notebooks[job['notebook_name']] = notebook_id

                        print(f"    ✅ '{job['notebook_name']}' completed")
                        jobs_to_remove.append(job)

                except Exception as e:
                    # Critical errors during job monitoring should fail the deployment
                    if time.time() - job['start_time'] > max_wait_time:
                        print(
                            f"❌ ERROR: Upload job for '{job['notebook_name']}' failed: {str(e)}")
                        print(
                            f"   Solution: Check workspace performance and retry deployment")
                        sys.exit(1)
                    else:
                        print(
                            f"    ⚠️ Monitoring error for '{job['notebook_name']}': {str(e)}")
                        jobs_to_remove.append(job)

            for job in jobs_to_remove:
                pending_jobs.remove(job)

            if pending_jobs:
                time.sleep(check_interval)

    # Refresh notebooks list
    try:
        final_notebooks = workspace_fabric_client.get_notebooks()
        fabric_notebooks.update(final_notebooks)
    except Exception as e:
        print(f"❌ ERROR: Failed to refresh notebooks list: {str(e)}")
        print(f"   Solution: Check workspace connectivity and permissions")
        sys.exit(1)

    uploaded_count = len([spec for spec in notebook_specs if os.path.basename(
        spec['path']).replace('.ipynb', '') in fabric_notebooks])
    print(
        f"✅ Successfully deployed {uploaded_count}/{len(notebook_specs)} notebooks")

except Exception as e:
    print(f"❌ ERROR: Failed to deploy notebooks: {str(e)}")
    sys.exit(1)

#################
# Notebook Jobs #
#################
# Docs: https://learn.microsoft.com/rest/api/fabric/core/job-scheduler

# Prepare variables
notebooks_to_run = [
    'run_bronze_to_silver',
    'run_silver_to_gold'
]

# Execute notebooks using sequential execution with 20-second monitoring
print(f"🚀 Executing data transformation pipelines sequentially")

execution_results = {}
successful_executions = []
failed_executions = []

# Execute notebooks one by one in sequence
for notebook_name in notebooks_to_run:
    # Check if notebook exists
    if notebook_name not in fabric_notebooks:
        print(f"  ❌ Notebook '{notebook_name}' not found")
        execution_results[notebook_name] = {
            'status': 'NotFound', 'error': 'Notebook not found'}
        failed_executions.append(notebook_name)
        continue

    notebook_id = fabric_notebooks[notebook_name]

    try:
        # Execute the notebook job using workspace client
        result = workspace_fabric_client.schedule_notebook_job(notebook_id)
        execution_results[notebook_name] = result

        # Track success/failure
        if result.get('status') == 'Completed':
            successful_executions.append(notebook_name)
        else:
            failed_executions.append(notebook_name)

    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        execution_results[notebook_name] = {
            'status': 'Failed', 'error': error_msg}
        failed_executions.append(notebook_name)
        print(f"  ❌ Error executing '{notebook_name}': {error_msg}")

    # Add delay between notebook executions (except for last one)
    if notebook_name != notebooks_to_run[-1]:
        print(
            f"    📋 Completed '{notebook_name}', proceeding to next notebook...")

# Final results summary
print(f"\n📊 Execution Summary:")
for notebook_name, result in execution_results.items():
    if result.get('status') == 'Completed':
        duration = result.get('duration', 'unknown')
        print(f"  ✅ '{notebook_name}' completed in {duration}")
    else:
        error = result.get('error', 'Unknown error')
        print(
            f"  ❌ '{notebook_name}' failed: {result.get('status', 'Unknown')} - {error}")

# Exit with error if any notebooks failed (consistent with rest of script)
if failed_executions:
    print(
        f"\n❌ ERROR: {len(failed_executions)} notebook(s) failed to execute successfully")
    print(f"   Failed notebooks: {', '.join(failed_executions)}")
    sys.exit(1)
else:
    print(
        f"✅ All {len(successful_executions)} pipelines executed successfully in sequence")

###################
# PowerBI Reports #
###################
# Docs: https://learn.microsoft.com/rest/api/power-bi/imports

print(f"📊 Deploying Power BI reports")

reports_local_folder_path = os.path.join(repo_root, 'reports')
pbix_pattern = os.path.join(reports_local_folder_path, '**', '*.pbix')
pbix_file_paths = glob.glob(pbix_pattern, recursive=True)
deployed_reports = []  # Track deployed reports for final summary

if not pbix_file_paths:
    print("  ℹ️ No Power BI report files (.pbix) found in reports directory")
else:
    print(f"  📋 Found {len(pbix_file_paths)} Power BI report(s) to deploy")

for pbix_file_path in pbix_file_paths:
    report_file_name = os.path.basename(pbix_file_path)
    report_name = report_file_name.replace('.pbix', '')
    print(f"  📊 Deploying report '{report_name}'")

    try:
        new_report = powerbi_client.new_report(
            report_name=report_name,
            file_path=pbix_file_path,
            conflict_action=ImportConflictHandlerMode.CREATE_OR_OVERWRITE,
            workspace_id=workspace_id,
            subfolder_object_id=fabric_folders[fabric_folder_path_reports],
            timeout=300  # 5 minutes
        )
        report_name = new_report.get('name', 'Unknown')
        report_id = new_report.get('id', 'Unknown')
        # Track deployed report
        deployed_reports.append({'name': report_name, 'id': report_id})
        print(
            f"  ✅ Successfully deployed report '{report_name}' (ID: {report_id})")

        # Get connection details from Gold lakehouse and configure dataset parameters
        print(f"  🔧 Configuring dataset parameters for '{report_name}'...")
        dataset = powerbi_client.get_powerbi_dataset(
            workspace_id=workspace_id, dataset_name=report_name)

        # Get Gold lakehouse details and check SQL endpoint status
        try:
            gold_lakehouse = workspace_fabric_client.get_lakehouse(
                lakehouse_id=fabric_lakehouses[udfwf_lakehouse_gold_name]['id'])
            sql_endpoint_provisioning_status = gold_lakehouse[
                'properties']['sqlEndpointProperties']['provisioningStatus']
            print(
                f"    📋 SQL endpoint status: {sql_endpoint_provisioning_status}")

            if sql_endpoint_provisioning_status == 'Success':
                # SQL endpoint is ready - proceed with dataset parameter updates
                sql_endpoint = gold_lakehouse['properties']['sqlEndpointProperties']['connectionString']
                database_name = udfwf_lakehouse_gold_name

                print(f"    📋 Updating dataset parameters:")
                print(f"      • SQL Endpoint: {sql_endpoint}")
                print(f"      • Database: {database_name}")

                # TODO: PowerBI limitation: parameters change only allowed with user, not service principal
                try:
                    powerbi_client.update_powerbi_dataset_parameters(dataset_id=dataset['id'], parameters=[
                        {"name": "sqlEndpoint", "newValue": sql_endpoint},
                        {"name": "database", "newValue": database_name}
                    ])
                    print(
                        f"  ✅ Dataset parameters updated successfully for '{report_name}'")
                except Exception as param_error:
                    # Check for specific API access error
                    if "HTTP 403" in str(param_error):
                        print(
                            f"  ⚠️ WARNING: Cannot update dataset parameters automatically for '{report_name}'")
                        print(
                            f"      Reason: API access restricted for service principal: {str(param_error)}")
                        print(f"      Manual action required:")
                        print(
                            f"  📋 Continuing deployment without dataset parameter updates...")
                    else:
                        # Re-raise other types of errors
                        raise param_error
            else:
                # Handle non-success status
                print(
                    f"  ❌ ERROR: SQL endpoint not ready (status: {sql_endpoint_provisioning_status})")
                print(
                    f"     Manual intervention required: Wait for SQL endpoint provisioning to complete and re-run script")
                sys.exit(1)

        except Exception as e:
            print(
                f"❌ ERROR: Failed to configure dataset parameters for '{report_name}': {str(e)}")
            print(f"   Solution: Check lakehouse availability and Power BI permissions")
            sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Failed to deploy report '{report_name}': {str(e)}")
        print(
            f"   Solution: Verify the .pbix file is valid and you have upload permissions")
        sys.exit(1)


##################
# End of program #
##################

print("-" * 60)
print(f"🎉 {solution_name} deployment completed successfully!")
print(f"✅ Workspace: {workspace_name}")
print(
    f"✅ Workspace URL: https://app.fabric.microsoft.com/groups/{workspace_id}")
if admin_assignments_added > 0:
    print(
        f"✅ Workspace Administrators: {admin_assignments_added} added successfully")
    if admin_assignments_skipped > 0:
        print(
            f"   📋 Note: {admin_assignments_skipped} administrator(s) were already assigned")
print(f"✅ Lakehouses: {len(udfwf_lakehouses)} created (Bronze, Silver, Gold)")
print(
    f"✅ Notebooks: {uploaded_count}/{len(notebook_specs)} deployed with batch processing")
print(f"✅ Sample data: {len(csv_file_paths)} files uploaded")
print(
    f"✅ Pipelines: {len(successful_executions)} executed successfully with optimized monitoring")
print(f"✅ Power BI Reports: {len(deployed_reports)} deployed")
if deployed_reports:
    for report in deployed_reports:
        print(f"   📊 {report['name']} (ID: {report['id']})")
print("-" * 60)
