#!/usr/bin/env python3
"""
UDF Lakehouse Setup Module

This module provides lakehouse creation and data loading functionality 
for the Unified Data Foundation solution.
"""

import sys
import os
import glob
from typing import Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fabric_api import FabricWorkspaceApiClient, FabricApiError


def create_lakehouse_directory_structure(file_system_client, 
                                        lakehouse_root_path: str, 
                                        folder_path: str) -> None:
    """
    Create a nested folder structure in a lakehouse using OneLake API.
    
    Args:
        file_system_client: Azure Data Lake file system client
        lakehouse_root_path: Root path of the lakehouse (e.g., 'MyLakehouse.Lakehouse/Files')
        folder_path: Path of folders to create (e.g., 'bronze/finance')
        
    Raises:
        Exception: If folder creation fails
    """
    # Build full path
    full_path = f"{lakehouse_root_path}/{folder_path}"
    
    # Split into parts and create each level
    parts = folder_path.split('/')
    current_path = lakehouse_root_path
    
    for part in parts:
        current_path = f"{current_path}/{part}"
        
        # Check if directory exists
        directory_client = file_system_client.get_directory_client(current_path)
        if not directory_client.exists():
            directory_client.create_directory()


def setup_lakehouses(workspace_client: FabricWorkspaceApiClient, 
                    lakehouse_names: set,
                    lakehouse_folder_id: Optional[str] = None) -> dict:
    """
    Create or retrieve lakehouses in a Fabric workspace.
    
    Args:
        workspace_client: Authenticated workspace API client
        lakehouse_names: Set of lakehouse names to create
        lakehouse_folder_id: Optional folder ID where to create lakehouses
        
    Returns:
        dict: Dictionary mapping lakehouse names to lakehouse objects
        
    Raises:
        FabricApiError: If lakehouse creation fails
    """
    print(f"🏠 Setting up lakehouses")
    
    # Get existing lakehouses
    print(f"   Retrieving existing lakehouses...")
    existing_lakehouses = workspace_client.list_lakehouses()
    existing_lakehouse_map = {lh['displayName']: lh for lh in existing_lakehouses}
    
    lakehouses = {}
    created_count = 0
    skipped_count = 0
    
    # Create or retrieve each lakehouse
    for lakehouse_name in lakehouse_names:
        if lakehouse_name in existing_lakehouse_map:
            print(f"   ℹ️  Lakehouse already exists: {lakehouse_name}")
            lakehouses[lakehouse_name] = existing_lakehouse_map[lakehouse_name]
            skipped_count += 1
        else:
            print(f"   ➕ Creating lakehouse: {lakehouse_name}")
            lakehouse = workspace_client.create_lakehouse(
                lakehouse_name,
                folder_id=lakehouse_folder_id
            )
            lakehouses[lakehouse_name] = lakehouse
            print(f"   ✅ Created lakehouse: {lakehouse_name} ({lakehouse['id']})")
            created_count += 1
    
    print(f"   ✅ Lakehouse setup complete:")
    print(f"      Created: {created_count}")
    print(f"      Skipped (already exists): {skipped_count}")
    
    return lakehouses


def load_csv_data_to_lakehouse(workspace_client: FabricWorkspaceApiClient,
                               bronze_lakehouse: dict,
                               csv_folder_path: str) -> dict:
    """
    Load CSV files from local folder to bronze lakehouse.
    
    Args:
        workspace_client: Authenticated workspace API client
        bronze_lakehouse: Bronze lakehouse object with displayName and id
        csv_folder_path: Local path to folder containing CSV files
        
    Returns:
        dict: Summary of upload operation (uploaded, skipped, failed)
        
    Raises:
        Exception: If upload fails
    """
    print(f"📊 Uploading sample data to bronze lakehouse")
    
    # Get lakehouse root path
    bronze_lakehouse_name = bronze_lakehouse['displayName']
    bronze_lakehouse_onelake_root_path = f"{bronze_lakehouse_name}.Lakehouse/Files"
    
    # Get all CSV files
    csv_pattern = os.path.join(csv_folder_path, '**', '*.csv')
    csv_file_paths = glob.glob(csv_pattern, recursive=True)
    
    if not csv_file_paths:
        print(f"   ⚠️  No CSV files found in {csv_folder_path}")
        return {'uploaded': 0, 'skipped': 0, 'failed': 0}
    
    print(f"   Found {len(csv_file_paths)} CSV files to upload")
    
    # Connect to lakehouse
    print(f"   Connecting to OneLake for lakehouse: {bronze_lakehouse_name}")
    file_system_client = workspace_client.get_lakehouse_file_system_client(bronze_lakehouse_name)
    
    # Track created folders to avoid recreating
    created_folders = set()
    uploaded_count = 0
    skipped_count = 0
    failed_count = 0
    
    # Upload each CSV file
    for local_file_path in csv_file_paths:
        try:
            # Get relative path from csv_folder_path
            relative_path = os.path.relpath(local_file_path, csv_folder_path)
            
            # Extract folder path and file name
            folder_path = os.path.dirname(relative_path)
            file_name = os.path.basename(relative_path)
            
            # Convert Windows path separators to forward slashes
            folder_path = folder_path.replace('\\', '/')
            
            # Create folder structure if needed
            if folder_path and folder_path != '.' and folder_path not in created_folders:
                create_lakehouse_directory_structure(
                    file_system_client,
                    bronze_lakehouse_onelake_root_path,
                    folder_path
                )
                created_folders.add(folder_path)
            
            # Build target path in lakehouse
            if folder_path and folder_path != '.':
                target_path = f"{bronze_lakehouse_onelake_root_path}/{folder_path}/{file_name}"
            else:
                target_path = f"{bronze_lakehouse_onelake_root_path}/{file_name}"
            
            # Check if file already exists
            file_client = file_system_client.get_file_client(target_path)
            if file_client.exists():
                print(f"   ℹ️  File already exists: {relative_path}")
                skipped_count += 1
                continue
            
            # Upload file
            print(f"   ⬆️  Uploading: {relative_path}")
            with open(local_file_path, 'rb') as data:
                file_client.upload_data(data, overwrite=True)
            
            uploaded_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to upload {relative_path}: {e}")
            failed_count += 1
    
    print(f"   ✅ Data upload complete:")
    print(f"      Uploaded: {uploaded_count}")
    print(f"      Skipped (already exists): {skipped_count}")
    if failed_count > 0:
        print(f"      Failed: {failed_count}")
    
    return {
        'uploaded': uploaded_count,
        'skipped': skipped_count,
        'failed': failed_count
    }
