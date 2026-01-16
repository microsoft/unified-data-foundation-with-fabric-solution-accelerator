#!/usr/bin/env python3
"""
UDF Folder Setup Module

This module provides folder structure creation functionality 
for the Unified Data Foundation solution.
"""

import sys
import os
from typing import Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fabric_api import FabricWorkspaceApiClient, FabricApiError


def create_fabric_directory_structure(workspace_client: FabricWorkspaceApiClient, 
                                     folder_path: str, 
                                     existing_folder_map: dict) -> str:
    """
    Create a nested folder structure in Fabric workspace.
    
    Args:
        workspace_client: Authenticated workspace API client
        folder_path: Path of folders to create (e.g., 'notebooks/bronze_to_silver')
        existing_folder_map: Dictionary mapping existing folder paths to IDs
        
    Returns:
        str: ID of the final folder in the path
        
    Raises:
        FabricApiError: If folder creation fails
    """
    # Split the path into parts
    path_parts = folder_path.split('/')
    current_path = ''
    parent_id = None
    
    # Create each folder in the path
    for i, part in enumerate(path_parts):
        # Build current path
        if current_path:
            current_path = f"{current_path}/{part}"
        else:
            current_path = part
        
        # Check if folder already exists
        if current_path in existing_folder_map:
            parent_id = existing_folder_map[current_path]
            continue
        
        # Create folder
        folder = workspace_client.create_folder(part, parent_id)
        folder_id = folder.get('id')
        
        if not folder_id:
            raise FabricApiError(f"Failed to create folder: {current_path}")
        
        # Update maps
        existing_folder_map[current_path] = folder_id
        parent_id = folder_id
    
    return parent_id


def setup_folder_structure(workspace_client: FabricWorkspaceApiClient, 
                          folder_paths: list) -> dict:
    """
    Create folder structure in Fabric workspace.
    
    Args:
        workspace_client: Authenticated workspace API client
        folder_paths: List of folder paths to create
        
    Returns:
        dict: Dictionary mapping folder paths to folder IDs
        
    Raises:
        FabricApiError: If folder creation fails
    """
    print(f"📁 Setting up folder structure")
    
    # Get existing folders
    print(f"   Retrieving existing folders...")
    existing_folders = workspace_client.list_folders()
    
    # Build folder path mapping
    folder_map = {}
    for folder in existing_folders:
        folder_name = folder.get('displayName')
        folder_id = folder.get('id')
        if folder_name and folder_id:
            folder_map[folder_name] = folder_id
    
    print(f"   Found {len(folder_map)} existing folders")
    
    # Create each folder path
    created_count = 0
    skipped_count = 0
    
    for folder_path in folder_paths:
        if folder_path in folder_map:
            print(f"   ℹ️  Folder already exists: {folder_path}")
            skipped_count += 1
        else:
            print(f"   ➕ Creating folder: {folder_path}")
            folder_id = create_fabric_directory_structure(
                workspace_client, 
                folder_path, 
                folder_map
            )
            print(f"   ✅ Created folder: {folder_path} ({folder_id})")
            created_count += 1
    
    print(f"   ✅ Folder setup complete:")
    print(f"      Created: {created_count}")
    print(f"      Skipped (already exists): {skipped_count}")
    
    return folder_map
