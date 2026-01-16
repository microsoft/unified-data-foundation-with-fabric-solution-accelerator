#!/usr/bin/env python3
"""
UDF Workspace Setup Module

This module provides workspace creation and capacity assignment functionality 
for the Unified Data Foundation solution.
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fabric_api import FabricApiError


def setup_workspace(fabric_client, capacity_name: str, workspace_name: str) -> str:
    """
    Create or retrieve a Fabric workspace and assign it to a capacity.
    
    Args:
        fabric_client: Authenticated Fabric API client
        capacity_name: Name of the capacity to assign
        workspace_name: Name of the workspace to create
        
    Returns:
        str: Workspace ID
        
    Raises:
        FabricApiError: If workspace creation or capacity assignment fails
        SystemExit: If capacity is not found
    """
    print(f"🏢 Setting up workspace: {workspace_name}")
    
    # Get capacity ID
    print(f"   Looking up capacity: {capacity_name}")
    capacity = fabric_client.get_capacity_by_name(capacity_name)
    
    if not capacity:
        print(f"❌ Error: Capacity '{capacity_name}' not found")
        print(f"   Please ensure the capacity exists and you have access to it.")
        sys.exit(1)
    
    capacity_id = capacity['id']
    print(f"   ✅ Found capacity: {capacity_name} ({capacity_id})")
    
    # Check if workspace already exists
    print(f"   Checking if workspace '{workspace_name}' exists...")
    workspace = fabric_client.get_workspace_by_name(workspace_name)
    
    if workspace:
        workspace_id = workspace['id']
        print(f"   ℹ️  Workspace already exists: {workspace_name} ({workspace_id})")
        
        # Check if workspace is already assigned to the capacity
        current_capacity_id = workspace.get('capacityId')
        if current_capacity_id == capacity_id:
            print(f"   ✅ Workspace already assigned to capacity: {capacity_name}")
        else:
            print(f"   🔄 Assigning workspace to capacity: {capacity_name}")
            fabric_client.assign_workspace_to_capacity(workspace_id, capacity_id)
            print(f"   ✅ Successfully assigned workspace to capacity")
    else:
        # Create new workspace
        print(f"   Creating new workspace: {workspace_name}")
        workspace = fabric_client.create_workspace(workspace_name)
        workspace_id = workspace['id']
        print(f"   ✅ Created workspace: {workspace_name} ({workspace_id})")
        
        # Assign workspace to capacity
        print(f"   🔄 Assigning workspace to capacity: {capacity_name}")
        fabric_client.assign_workspace_to_capacity(workspace_id, capacity_id)
        print(f"   ✅ Successfully assigned workspace to capacity")
    
    return workspace_id
