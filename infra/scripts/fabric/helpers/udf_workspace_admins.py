#!/usr/bin/env python3
"""
UDF Workspace Administrators Setup Module

This module provides functionality to add administrators to a Fabric workspace
for the Unified Data Foundation solution.
"""

import sys
import os
from typing import Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fabric_api import FabricApiError
from helpers.utils import is_valid_guid


def detect_principal_type(admin_identifier, graph_client=None):
    """
    Detect the principal type for a given admin identifier.
    
    Args:
        admin_identifier: User principal name (UPN), object ID, or service principal ID
        graph_client: Optional Graph API client for resolution
        
    Returns:
        tuple: (principal_type, object_id) or (None, None) if detection fails
    """
    if not admin_identifier:
        return None, None
    
    # Check if it's a GUID (object ID or service principal ID)
    if is_valid_guid(admin_identifier):
        # Try to determine if it's a user or service principal
        if graph_client:
            try:
                # Try as user first
                user = graph_client.get_user_by_id(admin_identifier)
                if user:
                    return "User", admin_identifier
                
                # Try as service principal
                sp = graph_client.get_service_principal_by_id(admin_identifier)
                if sp:
                    return "ServicePrincipal", admin_identifier
            except Exception:
                pass
        
        # Default to User if Graph API is not available
        return "User", admin_identifier
    
    # Assume it's a UPN and resolve via Graph API
    if graph_client:
        try:
            user = graph_client.get_user_by_upn(admin_identifier)
            if user:
                return "User", user['id']
        except Exception as e:
            print(f"   ⚠️  Could not resolve UPN '{admin_identifier}': {e}")
            return None, None
    
    return None, None


def get_existing_admin_principals(fabric_client, workspace_id):
    """
    Get existing workspace administrator principals.
    
    Args:
        fabric_client: Authenticated Fabric API client
        workspace_id: ID of the workspace
        
    Returns:
        dict: Dictionary mapping principal identifiers to role information
    """
    try:
        role_assignments = fabric_client.get_workspace_role_assignments(workspace_id)
        existing_principals = {}
        
        for assignment in role_assignments.get('value', []):
            if assignment.get('role') == 'Admin':
                principal = assignment.get('principal', {})
                principal_id = principal.get('id')
                principal_type = principal.get('type')
                
                if principal_id:
                    existing_principals[principal_id] = {
                        'type': principal_type,
                        'displayName': principal.get('displayName')
                    }
        
        return existing_principals
    except Exception as e:
        print(f"   ⚠️  Could not retrieve existing admins: {e}")
        return {}


def add_workspace_admin(fabric_client, workspace_id, admin_identifier, existing_principals, graph_client):
    """
    Add a workspace administrator by UPN or object ID with Graph API resolution.
    
    Args:
        fabric_client: Authenticated Fabric API client
        workspace_id: ID of the workspace
        admin_identifier: UPN or object ID of the admin to add
        existing_principals: Dictionary of existing admin principals
        graph_client: Graph API client for resolution
        
    Returns:
        tuple: (success: bool, skipped: bool)
    """
    try:
        # Detect principal type and get object ID
        principal_type, object_id = detect_principal_type(admin_identifier, graph_client)
        
        if not object_id or not principal_type:
            print(f"   ❌ Could not resolve admin identifier: {admin_identifier}")
            return False, False
        
        # Check if already an admin
        if object_id in existing_principals:
            print(f"   ℹ️  Already an admin: {admin_identifier} ({object_id})")
            return True, True
        
        # Add as workspace admin
        print(f"   ➕ Adding admin: {admin_identifier} ({principal_type})")
        fabric_client.add_workspace_role_assignment(
            workspace_id=workspace_id,
            principal_id=object_id,
            principal_type=principal_type,
            role='Admin'
        )
        print(f"   ✅ Successfully added admin: {admin_identifier}")
        
        # Update existing principals cache
        existing_principals[object_id] = {'type': principal_type}
        return True, False
        
    except FabricApiError as e:
        print(f"   ❌ Failed to add admin '{admin_identifier}': {e}")
        return False, False
    except Exception as e:
        print(f"   ❌ Unexpected error adding admin '{admin_identifier}': {e}")
        return False, False


def add_workspace_admin_by_object_id(fabric_client, workspace_id, object_id, existing_principals):
    """
    Add a workspace administrator by object ID with fallback logic.
    
    Args:
        fabric_client: Authenticated Fabric API client
        workspace_id: ID of the workspace
        object_id: Object ID of the admin to add
        existing_principals: Dictionary of existing admin principals
        
    Returns:
        tuple: (success: bool, skipped: bool)
    """
    try:
        # Check if already an admin
        if object_id in existing_principals:
            print(f"   ℹ️  Already an admin: {object_id}")
            return True, True
        
        # Try adding as User first
        print(f"   ➕ Adding admin (User): {object_id}")
        try:
            fabric_client.add_workspace_role_assignment(
                workspace_id=workspace_id,
                principal_id=object_id,
                principal_type='User',
                role='Admin'
            )
            print(f"   ✅ Successfully added admin as User: {object_id}")
            existing_principals[object_id] = {'type': 'User'}
            return True, False
        except FabricApiError as e:
            if e.status_code == 400:
                # Try as ServicePrincipal
                print(f"   🔄 Retrying as ServicePrincipal: {object_id}")
                fabric_client.add_workspace_role_assignment(
                    workspace_id=workspace_id,
                    principal_id=object_id,
                    principal_type='ServicePrincipal',
                    role='Admin'
                )
                print(f"   ✅ Successfully added admin as ServicePrincipal: {object_id}")
                existing_principals[object_id] = {'type': 'ServicePrincipal'}
                return True, False
            else:
                raise
        
    except FabricApiError as e:
        print(f"   ❌ Failed to add admin '{object_id}': {e}")
        return False, False
    except Exception as e:
        print(f"   ❌ Unexpected error adding admin '{object_id}': {e}")
        return False, False


def setup_workspace_administrators(workspace_client, 
                                   fabric_admins: list = None,
                                   fabric_admins_by_object_id: list = None,
                                   fabric_client = None,
                                   graph_client = None) -> dict:
    """
    Add administrators to a Fabric workspace.
    
    Args:
        workspace_client: Workspace-specific Fabric API client
        fabric_admins: Optional list of admin UPNs or object IDs to add (resolved via Graph API)
        fabric_admins_by_object_id: Optional list of admin object IDs to add (fallback logic)
        fabric_client: Optional main Fabric API client (for workspace operations)
        graph_client: Optional Graph API client (for UPN resolution)
        
    Returns:
        dict: Summary of admin assignments (added, skipped)
    """
    print(f"👥 Setting up workspace administrators")
    
    workspace_id = workspace_client.workspace_id
    
    # Initialize counters
    admin_assignments_added = 0
    admin_assignments_skipped = 0
    
    # Get existing admin principals
    existing_admin_principals = get_existing_admin_principals(
        fabric_client or workspace_client, 
        workspace_id
    )
    
    # Phase 1: Process fabric_admins (UPNs and object IDs with Graph API resolution)
    if fabric_admins:
        print(f"   Processing admins (with Graph API resolution)...")
        for admin in fabric_admins:
            success, skipped = add_workspace_admin(
                fabric_client or workspace_client,
                workspace_id,
                admin,
                existing_admin_principals,
                graph_client
            )
            if success:
                if skipped:
                    admin_assignments_skipped += 1
                else:
                    admin_assignments_added += 1
    
    # Phase 2: Process fabric_admins_by_object_id (Object IDs with fallback logic)
    if fabric_admins_by_object_id:
        print(f"   Processing admins by object ID (with fallback logic)...")
        for object_id in fabric_admins_by_object_id:
            success, skipped = add_workspace_admin_by_object_id(
                fabric_client or workspace_client,
                workspace_id,
                object_id,
                existing_admin_principals
            )
            if success:
                if skipped:
                    admin_assignments_skipped += 1
                else:
                    admin_assignments_added += 1
    
    # Summary
    print(f"   ✅ Admin setup complete:")
    print(f"      Added: {admin_assignments_added}")
    print(f"      Skipped (already admin): {admin_assignments_skipped}")
    
    return {
        'added': admin_assignments_added,
        'skipped': admin_assignments_skipped
    }
