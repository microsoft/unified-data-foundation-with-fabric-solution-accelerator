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
        
        # Create folder (returns folder ID string directly)
        folder_id = workspace_client.create_folder(part, parent_id)
        
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
    
    try:
        # Get existing folders (all folders recursively)
        print(f"   Retrieving existing folders...")
        existing_folders = workspace_client.list_folders(recursive=True, get_all=True)
        
        # Build folder ID mapping and parent mapping
        folder_by_id = {}
        for folder in existing_folders:
            folder_id = folder.get('id')
            if folder_id:
                folder_by_id[folder_id] = folder
        
        # Build full path mapping by traversing parent hierarchy
        folder_map = {}
        for folder in existing_folders:
            folder_id = folder.get('id')
            folder_name = folder.get('displayName')
            parent_id = folder.get('parentFolderId')
            
            if not folder_name or not folder_id:
                continue
            
            # Build full path by traversing parents
            path_parts = [folder_name]
            current_parent_id = parent_id
            
            while current_parent_id and current_parent_id in folder_by_id:
                parent_folder = folder_by_id[current_parent_id]
                parent_name = parent_folder.get('displayName')
                if parent_name:
                    path_parts.insert(0, parent_name)
                current_parent_id = parent_folder.get('parentFolderId')
            
            # Join to create full path
            full_path = '/'.join(path_parts)
            folder_map[full_path] = folder_id
        
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
        
    except FabricApiError as e:
        print(f"❌ Failed to setup folder structure: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error setting up folder structure: {e}")
        raise FabricApiError(f"Error setting up folder structure: {e}")


def main():
    """Main function to create folder structure."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create folder structure in a Microsoft Fabric workspace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a single folder
  python udf_folder.py --workspace-id "12345678-1234-1234-1234-123456789012" --folders "notebooks"
  
  # Create nested folder structure
  python udf_folder.py --workspace-id "12345678-1234-1234-1234-123456789012" --folders "notebooks/bronze_to_silver" "notebooks/silver_to_gold"
        """
    )
    
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="ID of the workspace"
    )
    
    parser.add_argument(
        "--folders",
        nargs="+",
        required=True,
        help="Folder paths to create (e.g., 'parent/child')"
    )
    
    args = parser.parse_args()
    
    try:
        from fabric_api import FabricWorkspaceApiClient, FabricApiError
        
        workspace_client = FabricWorkspaceApiClient(workspace_id=args.workspace_id)
        
        folder_map = setup_folder_structure(
            workspace_client=workspace_client,
            folder_paths=args.folders
        )
        
        print(f"\n🎉 Final Results:")
        print(f"   Workspace ID: {args.workspace_id}")
        print(f"   Folders Created/Retrieved: {len(folder_map)}")
        for path, folder_id in folder_map.items():
            print(f"      - {path} ({folder_id})")
        
    except FabricApiError as e:
        print(f"❌ Fabric API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
