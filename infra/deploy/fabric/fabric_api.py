"""
Microsoft Fabric API Client Library

This module provides a pure Python client for interacting with Microsoft Fabric REST APIs.
It focuses on core API operations including authentication, request management, and 
low-level methods for Fabric resources (workspaces, folders, notebooks, items).

This library adheres strictly to Fabric API operations and does not contain business logic
or project-specific transformations. For UDFF-specific functionality, see udff_utils.py.

Core Features:
- Authentication management with Azure CLI credentials
- HTTP request handling with error management
- Long Running Operation (LRO) support
- Workspace, folder, notebook, and item operations
- OneLake file system client integration

Dependencies:
    pip install requests azure-identity azure-storage-file-datalake

Author: Generated for Unified Data Foundation with Fabric (UDFF) project
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import requests
from azure.identity import AzureCliCredential, DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient, FileSystemClient


class FabricApiError(Exception):
    """Custom exception for Fabric API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class FabricApiClient:
    """
    Microsoft Fabric API Client
    
    Provides high-level methods for interacting with Microsoft Fabric REST APIs.
    Handles authentication, error handling, and long-running operations.
    """
    
    def __init__(self, 
                 api_url: str = "https://api.fabric.microsoft.com/v1",
                 resource_url: str = "https://api.fabric.microsoft.com",
                 credential: Optional[Any] = None,
                 timeout_sec: int = 240):
        """
        Initialize the Fabric API client.
        
        Args:
            api_url: Base URL for Fabric API
            resource_url: Resource URL for authentication scope
            credential: Azure credential object (defaults to AzureCliCredential)
            timeout_sec: Default timeout for API requests
        """
        self.api_url = api_url.rstrip('/')
        self.resource_url = resource_url
        self.timeout_sec = timeout_sec
        self._credential = credential or AzureCliCredential()
        self._token = None
        self._token_expiry = None
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """Log message with timestamp."""
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] {level}: {message}")
    
    def _format_duration(self, elapsed_seconds: float) -> str:
        """Format elapsed time consistently in minutes format.
        
        Args:
            elapsed_seconds: Elapsed time in seconds
            
        Returns:
            Formatted duration string (e.g., "5m 30s", "0m 45s")
        """
        minutes = int(elapsed_seconds // 60)
        seconds = int(elapsed_seconds % 60)
        return f"{minutes}m {seconds}s"
    
    def _get_auth_token(self) -> str:
        """
        Get or refresh the authentication token.
        
        Returns:
            Access token string
            
        Raises:
            FabricApiError: If authentication fails
        """
        try:
            # Check if we need to refresh the token
            if not self._token or (self._token_expiry and time.time() > self._token_expiry - 300):
                self._log("Getting authentication token")
                token_response = self._credential.get_token(f"{self.resource_url}/.default")
                self._token = token_response.token
                self._token_expiry = token_response.expires_on if hasattr(token_response, 'expires_on') else None
                self._log("Authentication successful")
            
            return self._token
        except Exception as e:
            raise FabricApiError(f"Authentication failed: {str(e)}")
    
    def _make_request(self,
                     uri: str,
                     method: str = "GET",
                     data: Optional[Union[str, dict]] = None,
                     headers: Optional[Dict[str, str]] = None,
                     timeout: Optional[int] = None,
                     wait_for_lro: bool = True) -> requests.Response:
        """
        Make an HTTP request to the Fabric API.
        
        Args:
            uri: API endpoint URI (relative to base URL)
            method: HTTP method
            data: Request body data
            headers: Additional headers
            timeout: Request timeout
            wait_for_lro: Whether to wait for long running operations to complete
            
        Returns:
            Response object
            
        Raises:
            FabricApiError: If request fails
        """
        url = f"{self.api_url}/{uri.lstrip('/')}"
        
        # Prepare headers
        request_headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Authorization': f'Bearer {self._get_auth_token()}'
        }
        if headers:
            request_headers.update(headers)
        
        # Prepare data
        if isinstance(data, dict):
            data = json.dumps(data)
        
        try:
            self._log(f"Making {method} request to {url}")
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=request_headers,
                data=data,
                timeout=timeout or self.timeout_sec
            )
            
            # Log request ID if available
            request_id = response.headers.get('requestId', 'N/A')
            self._log(f"Request ID: {request_id}")
            
            # Handle Long Running Operations (LRO)
            if response.status_code == 202 and wait_for_lro:
                location = response.headers.get('Location')
                if location:
                    self._log("Long-running operation detected, waiting for completion...")
                    return self._wait_for_lro_completion(location, max_wait_time=300)
                else:
                    return response
            elif response.status_code == 202 and not wait_for_lro:
                self._log("Long-running operation detected, returning 202 response without waiting")
            
            # Check for errors
            if response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f": {error_data['message']}"
                except:
                    error_msg += f": {response.text}"
                
                raise FabricApiError(error_msg, response.status_code, error_data if 'error_data' in locals() else None)
            
            self._log("Request completed successfully")
            return response
            
        except requests.RequestException as e:
            raise FabricApiError(f"Request failed: {str(e)}")
    
    def _wait_for_lro_completion(self, 
                                   job_url: str, 
                                   operation_name: Optional[str] = None,
                                   max_wait_time: int = 300, 
                                   check_interval: Optional[int] = None) -> requests.Response:
        """
        Wait for Long Running Operation to complete.
        
        Args:
            job_url: Full URL for monitoring the operation (including base URL)
            operation_name: Optional name for logging (e.g., notebook name)
            max_wait_time: Maximum time to wait in seconds
            check_interval: Check interval in seconds (defaults to Retry-After header or 5s)
            
        Returns:
            Final response object
        """
        start_time = time.time()
        default_interval = check_interval or 5
        
        # Log operation start
        operation_display = f"'{operation_name}'" if operation_name else "operation"
        self._log(f"Waiting for {operation_display} to complete...")
        
        while (time.time() - start_time) < max_wait_time:
            time.sleep(default_interval)
            
            try:
                # Make direct HTTP request to the job URL
                headers = {'Authorization': f'Bearer {self._get_auth_token()}'}
                response = requests.get(job_url, headers=headers, timeout=self.timeout_sec)
                
                if response.status_code == 200:
                    # For notebook operations, check if the job status indicates completion
                    if operation_name:  # This indicates it's likely a notebook job
                        try:
                            job_data = response.json()
                            job_status = job_data.get('status', 'Completed')
                            
                            # If job is still running, continue polling
                            if job_status in ['InProgress', 'Running', 'Queued', 'NotStarted']:
                                elapsed = time.time() - start_time
                                elapsed_str = self._format_duration(elapsed)
                                self._log(f"{operation_display} is {job_status.lower()}... ({elapsed_str} elapsed)")
                                continue
                            # If job is finished (completed, failed, or cancelled), return response
                            elif job_status in ['Completed', 'Failed', 'Cancelled']:
                                self._log(f"{operation_display} finished with status: {job_status}")
                                return response
                        except (ValueError, KeyError):
                            # No JSON or status field - treat as completed
                            pass
                    
                    self._log(f"{operation_display} completed successfully")
                    return response
                elif response.status_code == 202:
                    self._log(f"{operation_display} still in progress...")
                    # Update check interval from Retry-After header if not explicitly set
                    if not check_interval:
                        default_interval = int(response.headers.get('Retry-After', default_interval))
                    continue
                else:
                    raise FabricApiError(f"{operation_display} failed with status {response.status_code}: {response.text}")
                    
            except requests.RequestException as e:
                raise FabricApiError(f"Error checking {operation_display} status: {str(e)}")
        
        raise FabricApiError(f"{operation_display} timed out after {self._format_duration(max_wait_time)}")
    
    def start_long_running_operation(self,
                                   uri: str,
                                   method: str = "POST",
                                   data: Optional[Union[str, dict]] = None,
                                   headers: Optional[Dict[str, str]] = None,
                                   timeout: Optional[int] = None) -> requests.Response:
        """
        Start a long-running operation without waiting for completion.
        
        Args:
            uri: API endpoint URI (relative to base URL)
            method: HTTP method
            data: Request body data
            headers: Additional headers
            timeout: Request timeout
            
        Returns:
            Response object (typically 202 with Location header)
        """
        return self._make_request(uri, method, data, headers, timeout, wait_for_lro=False)
    
    def get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for API requests.
        
        Returns:
            Dictionary with Authorization header
        """
        return {"Authorization": f"Bearer {self._get_auth_token()}"}
    
    def get_workspace_file_system_client(self, workspace_name: str) -> FileSystemClient:
        """
        Create a Data Lake file system client for a Fabric workspace.
        
        Args:
            workspace_name: Name of the Fabric workspace
            
        Returns:
            FileSystemClient for OneLake operations
        """
        account_url = "https://onelake.dfs.fabric.microsoft.com"
        service_client = DataLakeServiceClient(account_url, credential=self._credential)
        return service_client.get_file_system_client(file_system=workspace_name)
    
    # Workspace operations
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """Get all workspaces accessible to the user."""
        response = self._make_request("workspaces")
        return response.json().get('value', [])
    
    def get_workspace(self, workspace_name: str) -> Dict[str, Any]:
        """
        Get workspace by name.
        
        Args:
            workspace_name: Name of the workspace
            
        Returns:
            Workspace object
            
        Raises:
            FabricApiError: If workspace not found
        """
        workspaces = self.get_workspaces()
        workspace = next((w for w in workspaces if w['displayName'].lower() == workspace_name.lower()), None)
        
        if not workspace:
            raise FabricApiError(f"Workspace '{workspace_name}' not found")
        
        return workspace
    
    def create_workspace(self, name: str, capacity_id: Optional[str] = None) -> str:
        """
        Create a new workspace.
        
        Args:
            name: Workspace name
            capacity_id: Optional capacity ID
            
        Returns:
            Workspace ID
        """
        data = {'displayName': name}
        if capacity_id:
            data['capacityId'] = capacity_id
        
        response = self._make_request("workspaces", method="POST", data=data)
        return response.json()['id']
    
    # Folder operations
    def get_folders(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all folders in a workspace."""
        response = self._make_request(f"workspaces/{workspace_id}/folders")
        return response.json().get('value', [])
    
    def create_folder(self, workspace_id: str, display_name: str, parent_folder_id: Optional[str] = None) -> str:
        """
        Create a folder in the workspace.
        
        Args:
            workspace_id: Target workspace ID
            display_name: Folder name
            parent_folder_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID
        """
        data = {"displayName": display_name}
        if parent_folder_id:
            data["parentFolderId"] = parent_folder_id
        
        response = self._make_request(f"workspaces/{workspace_id}/folders", method="POST", data=data)
        return response.json()['id']
    
    def create_folder_hierarchy(self, workspace_id: str, folder_path: str) -> str:
        """
        Create a complete folder hierarchy.
        
        Args:
            workspace_id: Target workspace ID
            folder_path: Full path separated by forward slashes
            
        Returns:
            Final folder ID
        """
        # Get existing folders and build path mapping
        existing_folders = self.get_folders(workspace_id)
        folder_map = self._build_folder_path_mapping(existing_folders)
        
        # Check if folder already exists
        if folder_path in folder_map:
            self._log(f"Folder '{folder_path}' already exists with ID: {folder_map[folder_path]}")
            return folder_map[folder_path]
        
        # Split path and create recursively
        path_parts = folder_path.split('/')
        
        if len(path_parts) == 1:
            # Root folder
            return self.create_folder(workspace_id, path_parts[0])
        else:
            # Ensure parent exists
            parent_path = '/'.join(path_parts[:-1])
            parent_id = self.create_folder_hierarchy(workspace_id, parent_path)
            
            # Create this folder
            folder_name = path_parts[-1]
            folder_id = self.create_folder(workspace_id, folder_name, parent_id)
            self._log(f"Created folder '{folder_name}' with ID: {folder_id}")
            return folder_id
    
    def _build_folder_path_mapping(self, folders: List[Dict[str, Any]]) -> Dict[str, str]:
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
    
    # Notebook operations
    def get_notebooks(self, workspace_id: str) -> Dict[str, str]:
        """
        Get all notebooks in a workspace.
        
        Returns:
            Dictionary mapping notebook names to IDs
        """
        response = self._make_request(f"workspaces/{workspace_id}/notebooks")
        notebooks = response.json().get('value', [])
        return {notebook['displayName']: notebook['id'] for notebook in notebooks}
    
    def create_notebook(self, workspace_id: str, notebook_data: Dict[str, Any], wait_for_lro: bool = True) -> requests.Response:
        """
        Create a new notebook.
        
        Args:
            workspace_id: Target workspace ID
            notebook_data: Notebook definition data
            wait_for_lro: Whether to wait for long running operations to complete
            
        Returns:
            API response
        """
        return self._make_request(f"workspaces/{workspace_id}/notebooks", method="POST", data=notebook_data, wait_for_lro=wait_for_lro)
    
    def update_notebook(self, workspace_id: str, notebook_id: str, notebook_data: Dict[str, Any], wait_for_lro: bool = True) -> requests.Response:
        """
        Update an existing notebook.
        
        Args:
            workspace_id: Target workspace ID
            notebook_id: Notebook ID to update
            notebook_data: Notebook definition data
            wait_for_lro: Whether to wait for long running operations to complete
            
        Returns:
            API response
        """
        return self._make_request(
            f"workspaces/{workspace_id}/notebooks/{notebook_id}/updateDefinition", 
            method="POST", 
            data=notebook_data,
            wait_for_lro=wait_for_lro
        )
    
    # Item operations
    def get_items(self, workspace_id: str, item_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get items from a workspace.
        
        Args:
            workspace_id: Target workspace ID
            item_type: Optional filter by item type
            
        Returns:
            List of items
        """
        response = self._make_request(f"workspaces/{workspace_id}/items")
        items = response.json().get('value', [])
        
        if item_type:
            items = [item for item in items if item.get('type', '').lower() == item_type.lower()]
        
        return items
    
    # Notebook execution operations
    def schedule_notebook_job(self, workspace_id: str, notebook_id: str) -> Dict[str, Any]:
        """
        Schedule a single notebook job and monitor its completion.
        
        Args:
            workspace_id: Target workspace ID
            notebook_id: Notebook ID to execute
            
        Returns:
            Dictionary with execution results including status, duration, and details
        """
        job_url = f"workspaces/{workspace_id}/items/{notebook_id}/jobs/instances?jobType=RunNotebook"
        start_time = time.time()
        
        self._log(f"Starting notebook execution: {notebook_id}")
        response = self._make_request(job_url, method="POST", wait_for_lro=False)
        
        # Handle immediate completion (HTTP 200)
        if response.status_code == 200:
            job_data = response.json() if response.content else {}
            self._log(f"Notebook {notebook_id} completed immediately (synchronous)")
            return {'status': 'Completed', 'duration': '0m 0s', 'details': job_data}
        
        # Handle Long Running Operation (HTTP 202)
        if response.status_code == 202:
            job_monitoring_url = response.headers.get('location')
            if not job_monitoring_url:
                error_msg = 'No location header in 202 response'
                self._log(f"Failed to start notebook {notebook_id}: {error_msg}", "ERROR")
                return {'status': 'Failed', 'error': error_msg}
            
            # Monitor the long-running operation
            try:
                lro_response = self._wait_for_lro_completion(
                    job_url=job_monitoring_url,
                    operation_name=f"notebook-{notebook_id}",
                    max_wait_time=1800,  # 30 minutes for notebook execution
                    check_interval=20   # 20 seconds between checks
                )
                
                # Calculate duration
                elapsed_time = time.time() - start_time
                duration_str = self._format_duration(elapsed_time)
                
                # Parse response to extract job status
                if lro_response.status_code == 200:
                    try:
                        job_data = lro_response.json()
                        job_status = job_data.get('status', 'Completed')
                        
                        return {
                            'status': job_status,
                            'duration': duration_str,
                            'details': job_data
                        }
                    except (ValueError, KeyError):
                        # Response doesn't have JSON or status field - treat as completed
                        return {
                            'status': 'Completed',
                            'duration': duration_str,
                            'details': {}
                        }
                else:
                    return {
                        'status': 'Failed',
                        'duration': duration_str,
                        'error': f"Unexpected response status: {lro_response.status_code}"
                    }
                    
            except FabricApiError as e:
                elapsed_time = time.time() - start_time
                duration_str = self._format_duration(elapsed_time)
                
                # Determine if it's a timeout or other error
                if "timed out" in str(e):
                    return {
                        'status': 'Timeout',
                        'duration': duration_str,
                        'error': str(e)
                    }
                else:
                    return {
                        'status': 'Failed',
                        'duration': duration_str,
                        'error': str(e)
                    }
        
        # Handle errors (HTTP 4xx/5xx)
        if response.status_code >= 400:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            self._log(f"Failed to start notebook {notebook_id}: {error_msg}", "ERROR")
            return {'status': 'Failed', 'error': error_msg}
        
        # Handle unexpected status codes
        error_msg = f"Unexpected HTTP status {response.status_code}: {response.text}"
        self._log(f"Unexpected response for notebook {notebook_id}: {error_msg}", "ERROR")
        return {'status': 'Failed', 'error': error_msg}


# Convenience functions
def create_fabric_client(credential: Optional[Any] = None) -> FabricApiClient:
    """
    Create a new Fabric API client.
    
    Args:
        credential: Azure credential (defaults to AzureCliCredential)
        
    Returns:
        FabricApiClient instance
    """
    return FabricApiClient(credential=credential)
