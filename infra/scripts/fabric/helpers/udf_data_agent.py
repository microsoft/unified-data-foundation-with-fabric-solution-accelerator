#!/usr/bin/env python3
"""
UDF Data Agent Setup Module

This module provides Data Agent creation and configuration functionality 
for the Unified Data Foundation solution with Lakehouse data sources.
"""

import sys
import os
import json
import base64
from typing import Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fabric_api import FabricWorkspaceApiClient, FabricApiError
from helpers.utils import read_file_content, replace_tokens_in_content


def setup_data_agent_lakehouse(workspace_client: FabricWorkspaceApiClient, 
                               data_agent_name: str,
                               lakehouse_id: str,
                               lakehouse_workspace_id: str,
                               environment_id: str,
                               selected_tables: list,
                               notebook_name: str,
                               notebook_folder_id: Optional[str] = None,
                               data_agent_folder_id: Optional[str] = None) -> dict:
    """
    Create a Data Agent and configure it with a Lakehouse data source via notebook.
    
    Args:
        workspace_client: Authenticated FabricWorkspaceApiClient instance
        data_agent_name: Name of the Data Agent to create
        lakehouse_id: ID of the Lakehouse to connect as data source
        lakehouse_workspace_id: ID of the workspace containing the Lakehouse
        environment_id: ID of the environment for data agent configuration
        selected_tables: List of table names to include in data agent
        notebook_name: Name of the configuration notebook to create
        notebook_folder_id: Optional folder ID where to create the notebook
        data_agent_folder_id: Optional folder ID where to create the data agent
        
    Returns:
        dict: Data Agent information if successful
        
    Raises:
        FabricApiError: If creation fails
    """
    print(f"🤖 Creating Data Agent: '{data_agent_name}'")
    
    try:
        # Check if Data Agent already exists
        existing_agent = workspace_client.get_data_agent_by_name(data_agent_name)
        if existing_agent:
            data_agent = existing_agent
            print(f"   ℹ️  Data Agent '{data_agent_name}' already exists")
        else:
            # Create the Data Agent
            data_agent = workspace_client.create_data_agent(data_agent_name, folder_id=data_agent_folder_id)
            print(f"   ✅ Successfully created Data Agent: {data_agent_name}")
        
        # Get data agent ID and fail if not found
        data_agent_id = data_agent.get('id')
        if not data_agent_id:
            raise FabricApiError(f"Failed to retrieve Data Agent ID for '{data_agent_name}'")
        
        # Calculate repository directory (script is in infra/scripts/fabric/helpers, so go up 4 levels)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_dir))))
        
        # Read configuration files
        print(f"   📖 Reading configuration files from: {repo_dir}")
        
        # Paths to configuration files
        notebook_path = os.path.join(repo_dir, "src", "fabric", "notebooks", "configure_data_agent.ipynb")
        agent_instructions_path = os.path.join(repo_dir, "src", "fabric", "data_agent", "agent_instructions.md")
        data_source_description_path = os.path.join(repo_dir, "src", "fabric", "data_agent", "data_source_description.md")
        data_source_instructions_path = os.path.join(repo_dir, "src", "fabric", "data_agent", "data_source_instructions.md")
        query_examples_path = os.path.join(repo_dir, "src", "fabric", "data_agent", "query_examples.json")
        
        # Read all configuration files
        notebook_content = read_file_content(notebook_path)
        agent_instructions = read_file_content(agent_instructions_path)
        data_source_description = read_file_content(data_source_description_path)
        data_source_instructions = read_file_content(data_source_instructions_path)
        query_examples_json = read_file_content(query_examples_path)
        
        print(f"   ✅ Successfully read all configuration files")
        
        # Parse query examples JSON to Python dict format for replacement
        query_examples_dict = json.loads(query_examples_json)
        query_examples_python = str(query_examples_dict)
        
        # Convert selected tables list to Python string format
        selected_tables_python = str(selected_tables)
        
        # Replace tokens in notebook content
        print(f"   🔄 Replacing configuration tokens...")
        tokens = {
            "__AGENT_ID__": data_agent_id,
            "__LAKEHOUSE_ID__": lakehouse_id,
            "__LAKEHOUSE_WORKSPACE_ID__": lakehouse_workspace_id,
            "__ENVIRONMENT_ID__": environment_id,
            "__WORKSPACE_ID__": workspace_client.workspace_id,
            "__AGENT_INSTRUCTIONS__": agent_instructions,
            "__DATA_SOURCE_INSTRUCTIONS__": data_source_instructions,
            "__DATA_SOURCE_DESCRIPTION__": data_source_description,
            "__QUERY_EXAMPLES__": query_examples_python,
            "__SELECTED_TABLES__": selected_tables_python
        }
        
        configured_notebook_content = replace_tokens_in_content(notebook_content, tokens)
        print(f"   ✅ Successfully replaced configuration tokens")
        
        # Create or update notebook
        print(f"   📓 Creating/updating notebook: '{notebook_name}'")
        
        # Check if notebook already exists
        notebook = workspace_client.get_notebook_by_name(notebook_name)
        
        # Parse and encode notebook content as base64
        notebook_json = json.loads(configured_notebook_content)
        notebook_base64 = base64.b64encode(
            json.dumps(notebook_json).encode('utf-8')
        ).decode('utf-8')
        
        if notebook:
            # Update existing notebook
            notebook_id = notebook.get('id')
            if not notebook_id:
                raise FabricApiError(f"Failed to retrieve notebook ID for existing notebook '{notebook_name}'")
            print(f"   ℹ️  Notebook '{notebook_name}' already exists, updating...")
            workspace_client.update_notebook(notebook_id, notebook_name, notebook_base64, notebook_folder_id)
            print(f"   ✅ Successfully updated notebook: {notebook_name} ({notebook_id})")
        else:
            # Create new notebook
            notebook = workspace_client.create_notebook(notebook_name, notebook_base64, notebook_folder_id)
            notebook_id = notebook.get('id')
            if not notebook_id:
                raise FabricApiError(f"Failed to retrieve notebook ID for created notebook '{notebook_name}'")
            print(f"   ✅ Successfully created notebook: {notebook_name} ({notebook_id})")
        
        # Run the notebook
        print(f"   ▶️  Running configuration notebook...")
        job_result = workspace_client.schedule_notebook_job(notebook_id)
        
        print(f"   📊 Notebook execution completed:")
        print(f"      Status: {job_result.get('status')}")
        print(f"      Duration: {job_result.get('duration')}")
        
        if job_result.get('status') != 'Completed':
            if 'error' in job_result:
                print(f"      Error: {job_result.get('error')}")
            raise FabricApiError(f"Notebook execution failed with status: {job_result.get('status')}")
        
        print(f"   ✅ Data Agent configuration completed successfully!")
        
        return data_agent
        
    except FabricApiError as e:
        print(f"❌ Failed to create/configure Data Agent '{data_agent_name}': {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error creating/configure Data Agent '{data_agent_name}': {e}")
        raise FabricApiError(f"Error creating Data Agent: {e}")
