import os
import argparse
import sys
import uuid
from fabric_api import create_fabric_client, FabricApiError
from graph_api import create_graph_client, GraphApiError

####################
# Helper Functions #
####################

def is_valid_guid(value):
    """Check if a string is a valid GUID format."""
    if not value or not isinstance(value, str):
        return False
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
        print(f"    🔍 Checking existing role assignments...")
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
        
        print(f"    📊 Found {admin_count} existing administrator(s)")
        return existing_principals
        
    except Exception as e:
        print(f"    ⚠️ WARNING: Could not retrieve existing role assignments: {str(e)}")
        print("       Will proceed but may create duplicates")
        return set()


def add_workspace_admin(fabric_client, workspace_id, admin_identifier, existing_principals, graph_client):
    """Add a single workspace administrator with simplified error handling."""
    # Check if already exists
    if admin_identifier.lower() in existing_principals:
        print(f"    ⏭️ Skipping '{admin_identifier}' - already a workspace administrator")
        return {'status': 'skipped', 'message': 'Already exists'}
    
    try:
        # Try to resolve principal type using Graph API
        principal_type, object_id, principal_data = detect_principal_type(admin_identifier, graph_client)
        
        if object_id.lower() in existing_principals:
            print(f"    ⏭️ Skipping '{admin_identifier}' - already a workspace administrator")
            existing_principals.add(admin_identifier.lower())  # Prevent future duplicates
            return {'status': 'skipped', 'message': 'Already exists (by object ID)'}
        
        display_name = principal_data.get('displayName', 'Unknown')
        print(f"    🔐 Adding {principal_type.lower()} administrator: {admin_identifier} ({display_name})")
        
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
        
        print(f"    ✅ Successfully added '{admin_identifier}' as workspace administrator")
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
        print(f"    ⏭️ Skipping '{object_id}' - already a workspace administrator")
        return {'status': 'skipped', 'message': 'Already exists'}
    
    print(f"    🔐 Adding administrator by Object ID: {object_id}")
    print(f"       Will try both User and ServicePrincipal types...")
    
    # Try both User and ServicePrincipal types
    for principal_type in ["User", "ServicePrincipal"]:
        try:
            print(f"       Trying as {principal_type}...")
            fabric_client.add_workspace_role_assignment(
                workspace_id=workspace_id,
                principal_id=object_id,
                principal_type=principal_type,
                role="Admin"
            )
            print(f"    ✅ Successfully added '{object_id}' as workspace administrator ({principal_type})")
            existing_principals.add(object_id.lower())
            return {'status': 'success', 'message': f'Added as {principal_type}'}
        except FabricApiError as e:
            print(f"       Failed as {principal_type}: API error ({e.status_code})")
            continue
        except Exception as e:
            print(f"       Failed as {principal_type}: {str(e)}")
            continue
    
    return {'status': 'failed', 'message': 'Failed to add as both User and ServicePrincipal types'}


def process_workspace_admins(fabric_client, workspace, fabric_admins, fabric_admins_by_object_id, graph_client, global_stats):
    """Process admin assignments for a single workspace."""
    workspace_id = workspace['id']
    workspace_name = workspace['displayName']
    
    print(f"  📁 Processing workspace: '{workspace_name}' (ID: {workspace_id})")
    
    # Get existing admin principals for this workspace
    existing_admin_principals = get_existing_admin_principals(fabric_client, workspace_id)
    
    workspace_stats = {'added': 0, 'skipped': 0, 'failed': 0, 'errors': []}
    
    # Phase 1: Process fabricAdmins (UPNs and object IDs with Graph API resolution)
    if fabric_admins:
        print(f"    👥 Adding fabricAdmins...")
        
        for admin_identifier in fabric_admins:
            result = add_workspace_admin(
                fabric_client, workspace_id, admin_identifier, 
                existing_admin_principals, graph_client
            )
            
            # Update counters based on result
            if result['status'] == 'success':
                workspace_stats['added'] += 1
                global_stats['added'] += 1
            elif result['status'] == 'skipped':
                workspace_stats['skipped'] += 1
                global_stats['skipped'] += 1
            else:  # failed
                workspace_stats['failed'] += 1
                global_stats['failed'] += 1
                workspace_stats['errors'].append(f"{admin_identifier}: {result['message']}")
    
    # Phase 2: Process fabricAdminsByObjectId (Object IDs with fallback logic)
    if fabric_admins_by_object_id:
        print(f"    👥 Adding fabricAdminsByObjectId...")
        
        for object_id in fabric_admins_by_object_id:
            result = add_workspace_admin_by_object_id(
                fabric_client, workspace_id, object_id, existing_admin_principals
            )
            
            # Update counters based on result
            if result['status'] == 'success':
                workspace_stats['added'] += 1
                global_stats['added'] += 1
            elif result['status'] == 'skipped':
                workspace_stats['skipped'] += 1
                global_stats['skipped'] += 1
            else:  # failed
                workspace_stats['failed'] += 1
                global_stats['failed'] += 1
                workspace_stats['errors'].append(f"{object_id}: {result['message']}")
    
    # Print workspace summary
    total_requested = len(fabric_admins) + len(fabric_admins_by_object_id)
    print(f"    📊 Workspace summary - Added: {workspace_stats['added']}, Skipped: {workspace_stats['skipped']}, Failed: {workspace_stats['failed']}, Total: {total_requested}")
    
    # Show error details if any failures occurred
    if workspace_stats['errors']:
        print(f"    ⚠️ Errors in this workspace:")
        for error in workspace_stats['errors'][:3]:  # Show first 3 errors
            print(f"       • {error}")
        if len(workspace_stats['errors']) > 3:
            print(f"       • ... and {len(workspace_stats['errors']) - 3} more errors")
    
    print()  # Add spacing between workspaces


##########################
# Command line arguments #
##########################

# Parse command line arguments
parser = argparse.ArgumentParser(
    description='Add administrators to all available Microsoft Fabric workspaces')
parser.add_argument('--fabricAdmins', nargs='*', default=[],
                    help='List of administrators to add to all workspaces. Can include user principal names (UPNs) like user@contoso.com or service principal IDs (GUIDs) like 12345678-1234-1234-1234-123456789012')
parser.add_argument('--fabricAdminsByObjectId', nargs='*', default=[],
                    help='List of object IDs (GUIDs) to add as workspace administrators to all workspaces. These will be tried as both User and ServicePrincipal types. Format: 12345678-1234-1234-1234-123456789012')
args = parser.parse_args()

# Check if at least one admin type is provided
if not args.fabricAdmins and not args.fabricAdminsByObjectId:
    print("❌ ERROR: At least one of --fabricAdmins or --fabricAdminsByObjectId must be provided")
    parser.print_help()
    sys.exit(1)

print(f"🚀 Starting Microsoft Fabric workspace administrators management")
if args.fabricAdmins:
    print(f"📋 Administrators to add: {', '.join(args.fabricAdmins)}")
if args.fabricAdminsByObjectId:
    print(f"📋 Administrators to add by Object ID: {', '.join(args.fabricAdminsByObjectId)}")
print("-" * 80)

fabric_admins = args.fabricAdmins
fabric_admins_by_object_id = args.fabricAdminsByObjectId

##########################
# Clients authentication #
##########################

print("🔐 Authenticating clients...")

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

##########################
# Get all workspaces     #
##########################

print("🔍 Retrieving all available workspaces...")
try:
    workspaces = fabric_client.get_workspaces()
    
    if not workspaces:
        print("⚠️ No workspaces found. You may not have access to any workspaces.")
        sys.exit(0)
    
    print(f"✅ Found {len(workspaces)} workspace(s)")
    for workspace in workspaces:
        print(f"   • {workspace['displayName']} (ID: {workspace['id']})")
    
    print("-" * 80)
    
except FabricApiError as e:
    if e.status_code == 403:
        print(f"❌ ERROR: Access denied when retrieving workspaces")
        print("   Solution: Ensure you have appropriate permissions to list workspaces")
    else:
        print(f"❌ ERROR: Fabric API error")
    print(f"   Status Code: {e.status_code}")
    print(f"   Details: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: Unexpected error retrieving workspaces: {str(e)}")
    sys.exit(1)

##########################
# Process all workspaces #
##########################

print("👥 Processing administrators for all workspaces...")
print()

# Global statistics tracking
global_stats = {'added': 0, 'skipped': 0, 'failed': 0}
processed_workspaces = 0
failed_workspaces = []

for workspace in workspaces:
    try:
        process_workspace_admins(
            fabric_client, workspace, fabric_admins, fabric_admins_by_object_id, 
            graph_client, global_stats
        )
        processed_workspaces += 1
    except Exception as e:
        workspace_name = workspace.get('displayName', 'Unknown')
        workspace_id = workspace.get('id', 'Unknown')
        print(f"  ❌ ERROR: Failed to process workspace '{workspace_name}' (ID: {workspace_id})")
        print(f"     Details: {str(e)}")
        failed_workspaces.append(workspace_name)
        print()

##################
# Final Summary  #
##################

print("-" * 80)
print(f"🎉 Microsoft Fabric workspace administrators management completed!")
print()
print(f"📊 Global Summary:")
print(f"   • Workspaces processed: {processed_workspaces}/{len(workspaces)}")
print(f"   • Total administrators added: {global_stats['added']}")
print(f"   • Total assignments skipped (already admin): {global_stats['skipped']}")
print(f"   • Total assignments failed: {global_stats['failed']}")

if failed_workspaces:
    print(f"\n⚠️ Failed to process {len(failed_workspaces)} workspace(s):")
    for workspace_name in failed_workspaces:
        print(f"   • {workspace_name}")
    print("   Note: Check permissions and workspace access for these workspaces")

if global_stats['failed'] > 0:
    print(f"\n⚠️ Note: {global_stats['failed']} administrator assignment(s) failed across all workspaces")
    print("   Review the individual workspace error details above for troubleshooting")

total_requested = (len(fabric_admins) + len(fabric_admins_by_object_id)) * len(workspaces)
print(f"\n📋 Processing Summary:")
print(f"   • Total requests: {total_requested} ({len(fabric_admins) + len(fabric_admins_by_object_id)} admins × {len(workspaces)} workspaces)")
print(f"   • Success rate: {((global_stats['added'] + global_stats['skipped']) / total_requested * 100):.1f}%" if total_requested > 0 else "   • Success rate: N/A")

print("-" * 80)

# Exit with appropriate code
if failed_workspaces or global_stats['failed'] > 0:
    sys.exit(1)
else:
    print("✅ All operations completed successfully!")
    sys.exit(0)