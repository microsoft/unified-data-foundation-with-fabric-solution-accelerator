#!/usr/bin/env python3
"""
UDF Environment Setup Module

This module provides Fabric Environment creation and configuration functionality 
for the Unified Data Foundation solution.
"""

import sys
import os
import base64
from typing import Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fabric_api import FabricWorkspaceApiClient, FabricApiError
from helpers.utils import read_file_content


def setup_environment(workspace_client: FabricWorkspaceApiClient, 
                     environment_name: str,
                     description: Optional[str] = None,
                     environment_yml_path: Optional[str] = None,
                     folder_id: Optional[str] = None) -> dict:
    """
    Create or update a Fabric Environment with custom libraries.
    
    Args:
        workspace_client: Authenticated workspace API client
        environment_name: Name of the environment to create
        description: Optional description for the environment
        environment_yml_path: Optional path to environment.yml file with library specifications
        folder_id: Optional folder ID where to create the environment
        
    Returns:
        dict: Environment information if successful
        
    Raises:
        FabricApiError: If creation or update fails
    """
    print(f"🌍 Setting up Fabric environment: '{environment_name}'")
    
    try:
        # Check if environment already exists
        existing_environment = workspace_client.get_environment_by_name(environment_name)
        
        if existing_environment:
            environment_id = existing_environment.get('id')
            print(f"   ℹ️  Environment already exists: {environment_name} ({environment_id})")
            environment = existing_environment
        else:
            # Create new environment
            print(f"   ➕ Creating environment: {environment_name}")
            environment = workspace_client.create_environment(
                environment_name,
                description=description,
                folder_id=folder_id
            )
            environment_id = environment.get('id')
            if not environment_id:
                raise FabricApiError(f"Failed to retrieve environment ID for '{environment_name}'")
            print(f"   ✅ Created environment: {environment_name} ({environment_id})")
        
        # If environment.yml is provided, update the environment with custom libraries
        if environment_yml_path:
            print(f"   📦 Configuring custom libraries from: {environment_yml_path}")
            
            # Read environment.yml content
            try:
                environment_yml_content = read_file_content(environment_yml_path)
                print(f"   ✅ Successfully read environment.yml")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not read environment.yml: {e}")
                print(f"   ℹ️  Environment created without custom libraries")
                return environment
            
            # Encode as base64
            environment_yml_base64 = base64.b64encode(
                environment_yml_content.encode('utf-8')
            ).decode('utf-8')
            
            # Update environment with libraries
            print(f"   🔄 Updating environment with custom libraries...")
            try:
                workspace_client.update_environment_libraries(
                    environment_id,
                    environment_yml_base64
                )
                print(f"   ✅ Successfully configured custom libraries")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not update environment libraries: {e}")
                print(f"   ℹ️  Environment created but library update failed")
        
        return environment
        
    except FabricApiError as e:
        print(f"❌ Failed to setup environment '{environment_name}': {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error setting up environment '{environment_name}': {e}")
        raise FabricApiError(f"Error setting up environment: {e}")
