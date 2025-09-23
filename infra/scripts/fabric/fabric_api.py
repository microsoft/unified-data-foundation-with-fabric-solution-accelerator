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

import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
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
                     wait_for_lro: bool = True,
                     max_retries: int = 3,
                     retry_count: int = 0) -> requests.Response:
        """
        Make an HTTP request to the Fabric API.
        
        Args:
            uri: API endpoint URI (relative to base URL)
            method: HTTP method
            data: Request body data
            headers: Additional headers
            timeout: Request timeout
            wait_for_lro: Whether to wait for long running operations to complete
            max_retries: Maximum number of retries for rate limiting
            retry_count: Current retry count (internal use)
            
        Returns:
            Response object
            
        Raises:
            FabricApiError: If request fails
        """
        if retry_count > max_retries:
            raise FabricApiError(f"Maximum retries ({max_retries}) exceeded for rate limiting")
        
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
            self._log(f"Making {method} request to {url} (attempt {retry_count + 1})")
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
                    return self._wait_for_lro_completion(
                        job_url=location,
                        operation_name=f"{method} {uri}",
                        max_wait_time=1800
                    )
                else:
                    self._log("Long-running operation detected but no Location header found", "WARNING")
                
            elif response.status_code == 202 and not wait_for_lro:
                self._log("Long-running operation detected, returning 202 response without waiting")
            
            elif response.status_code == 429:
                # Handle rate limiting with exponential backoff
                retry_after_header = response.headers.get('Retry-After', '60')
                
                # Parse retry-after header (could be seconds or HTTP date)
                try:
                    retry_after = int(retry_after_header)
                except ValueError:
                    # If it's not a number, assume it's an HTTP date (not implemented here)
                    retry_after = min(60, 2 ** retry_count)  # Exponential backoff with cap
                
                # Cap the retry time to reasonable limits
                retry_after = min(retry_after, 300)  # Max 5 minutes
                
                self._log(f"Rate limit exceeded. Retrying in {retry_after} seconds... (attempt {retry_count + 1}/{max_retries})", "WARNING")
                time.sleep(retry_after)
                
                # Recursive call with retry count
                return self._make_request(uri, method, data, headers, timeout, wait_for_lro, max_retries, retry_count + 1)
            
            # Check for errors
            elif response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                error_data = None
                
                try:
                    error_response = response.json()
                    if 'error' in error_response:
                        error_data = error_response['error']
                        error_msg += f": {error_data.get('message', 'Unknown error')}"
                except (ValueError, json.JSONDecodeError):
                    error_msg += f": {response.text[:500]}"  # Limit error text length
                
                raise FabricApiError(error_msg, response.status_code, error_data)
            
            self._log("Request completed successfully")
            return response
            
        except requests.Timeout as e:
            raise FabricApiError(f"Request timed out after {timeout or self.timeout_sec} seconds: {str(e)}")
        except requests.ConnectionError as e:
            raise FabricApiError(f"Connection error: {str(e)}")
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
    
    # Capacity operations
    def get_capacities(self) -> List[Dict[str, Any]]:
        """
        Get all capacities accessible to the user.
        
        Returns:
            List of capacity objects containing:
            - id: Capacity ID (GUID)
            - displayName: Capacity display name
            - sku: Capacity SKU (e.g., "F2", "F4", "P1", etc.)
            - state: Capacity state ("Active", "Paused", "Suspended", etc.)
            - region: Azure region where capacity is located
            - admins: List of capacity administrators
            - contributors: List of capacity contributors (if any)
            
        Raises:
            FabricApiError: If request fails
            
        Required Scopes:
            Capacity.Read.All or Capacity.ReadWrite.All
        """
        self._log("Getting all capacities accessible to user")
        response = self._make_request("capacities")
        capacities = response.json().get('value', [])
        self._log(f"Found {len(capacities)} capacity(ies)")
        return capacities

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
    
    def assign_workspace_to_capacity(self, workspace_id: str, capacity_id: str) -> None:
        """
        Assign a workspace to a capacity.
        
        Args:
            workspace_id: ID of the workspace to assign
            capacity_id: ID of the capacity to assign to
            
        Raises:
            FabricApiError: If assignment fails
            
        Required Scopes:
            Workspace.ReadWrite.All
            
        Reference:
            https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/assign-to-capacity
        """
        self._log(f"Assigning workspace {workspace_id} to capacity {capacity_id}")
        
        data = {"capacityId": capacity_id}
        
        response = self._make_request(
            f"workspaces/{workspace_id}/assignToCapacity", 
            method="POST", 
            data=data
        )
        
        if response.status_code == 200 or response.status_code == 202:
            self._log(f"Successfully assigned workspace to capacity")
        else:
            raise FabricApiError(f"Failed to assign workspace to capacity: {response.status_code}")
    
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
    
    # Lakehouse operations
    def get_lakehouses(self, workspace_id: str) -> List[Dict[str, Any]]:
        """
        Get all lakehouses from a workspace.
        
        Args:
            workspace_id: Target workspace ID
            
        Returns:
            List of lakehouse objects containing:
            - id: Lakehouse ID
            - displayName: Lakehouse display name
            - description: Lakehouse description
            - type: Item type ("Lakehouse")
            - workspaceId: Workspace ID
            - properties: Lakehouse properties including OneLake paths and SQL endpoint
            - folderId: Folder ID (if in a folder)
            - tags: List of applied tags
            
        Raises:
            FabricApiError: If request fails
            
        Required Scopes:
            Workspace.Read.All or Workspace.ReadWrite.All
        """
        self._log(f"Getting lakehouses from workspace {workspace_id}")
        response = self._make_request(f"workspaces/{workspace_id}/lakehouses")
        lakehouses = response.json().get('value', [])
        self._log(f"Found {len(lakehouses)} lakehouse(s)")
        return lakehouses
    
    def get_lakehouse(self, workspace_id: str, lakehouse_id: str) -> Dict[str, Any]:
        """
        Get properties of a specific lakehouse.
        
        Args:
            workspace_id: Target workspace ID
            lakehouse_id: Lakehouse ID
            
        Returns:
            Lakehouse object containing:
            - id: Lakehouse ID
            - displayName: Lakehouse display name
            - description: Lakehouse description
            - type: Item type ("Lakehouse")
            - workspaceId: Workspace ID
            - properties: Lakehouse properties including:
              - oneLakeTablesPath: OneLake path to tables directory
              - oneLakeFilesPath: OneLake path to files directory
              - sqlEndpointProperties: SQL endpoint details (connection string, ID, status)
              - defaultSchema: Default schema (for schema-enabled lakehouses)
            - folderId: Folder ID (if in a folder)
            - tags: List of applied tags
            
        Raises:
            FabricApiError: If lakehouse not found or request fails
            
        Required Scopes:
            Lakehouse.Read.All or Lakehouse.ReadWrite.All or Item.Read.All or Item.ReadWrite.All
        """
        self._log(f"Getting lakehouse {lakehouse_id} from workspace {workspace_id}")
        response = self._make_request(f"workspaces/{workspace_id}/lakehouses/{lakehouse_id}")
        lakehouse = response.json()
        self._log(f"Retrieved lakehouse '{lakehouse.get('displayName', 'Unknown')}'")
        return lakehouse
    
    def get_lakehouse_by_name(self, workspace_id: str, lakehouse_name: str) -> Dict[str, Any]:
        """
        Get lakehouse by display name.
        
        Args:
            workspace_id: Target workspace ID
            lakehouse_name: Display name of the lakehouse
            
        Returns:
            Lakehouse object
            
        Raises:
            FabricApiError: If lakehouse not found or request fails
        """
        lakehouses = self.get_lakehouses(workspace_id)
        lakehouse = next((lh for lh in lakehouses if lh['displayName'].lower() == lakehouse_name.lower()), None)
        
        if not lakehouse:
            raise FabricApiError(f"Lakehouse '{lakehouse_name}' not found in workspace {workspace_id}")
        
        return lakehouse
    
    def create_lakehouse(self, 
                        workspace_id: str, 
                        display_name: str,
                        description: Optional[str] = None,
                        folder_id: Optional[str] = None,
                        enable_schemas: bool = True,
                        wait_for_lro: bool = True) -> Dict[str, Any]:
        """
        Create a new lakehouse in the specified workspace.
        
        Args:
            workspace_id: Target workspace ID
            display_name: Lakehouse display name
            description: Optional lakehouse description (max 256 characters)
            folder_id: Optional folder ID (if None, created in workspace root)
            enable_schemas: Whether to enable schemas (default: True)
            wait_for_lro: Whether to wait for long running operations to complete
            
        Returns:
            Lakehouse object containing:
            - id: Lakehouse ID
            - displayName: Lakehouse display name
            - description: Lakehouse description
            - type: Item type ("Lakehouse")
            - workspaceId: Workspace ID
            - folderId: Folder ID (if in a folder)
            
        Raises:
            FabricApiError: If creation fails
            
        Required Scopes:
            Lakehouse.ReadWrite.All or Item.ReadWrite.All
        """
        self._log(f"Creating lakehouse '{display_name}' in workspace {workspace_id}")
        
        # Prepare request data
        lakehouse_data = {
            "displayName": display_name,
            "type": "Lakehouse"
        }
        
        if description:
            lakehouse_data["description"] = description
            
        if folder_id:
            lakehouse_data["folderId"] = folder_id
            
        if enable_schemas:
            lakehouse_data["creationPayload"] = {
                "enableSchemas": True
            }
        
        # Make the API request
        response = self._make_request(
            f"workspaces/{workspace_id}/lakehouses", 
            method="POST", 
            data=lakehouse_data,
            wait_for_lro=wait_for_lro
        )
        
        if response.status_code in [201, 200]:
            lakehouse = response.json()
            self._log(f"Lakehouse '{display_name}' created successfully with ID: {lakehouse.get('id')}")
            return lakehouse
        else:
            raise FabricApiError(f"Unexpected response status: {response.status_code}")
    
    def update_lakehouse(self, 
                        workspace_id: str, 
                        lakehouse_id: str,
                        display_name: Optional[str] = None,
                        description: Optional[str] = None) -> Dict[str, Any]:
        """
        Update properties of an existing lakehouse.
        
        Args:
            workspace_id: Target workspace ID
            lakehouse_id: Lakehouse ID to update
            display_name: New lakehouse display name (optional)
            description: New lakehouse description (optional, max 256 characters)
            
        Returns:
            Updated lakehouse object
            
        Raises:
            FabricApiError: If update fails or lakehouse not found
            
        Required Scopes:
            Lakehouse.ReadWrite.All or Item.ReadWrite.All
        """
        if not display_name and not description:
            raise FabricApiError("At least one property (display_name or description) must be provided for update")
        
        self._log(f"Updating lakehouse {lakehouse_id} in workspace {workspace_id}")
        
        # Prepare request data
        update_data = {}
        if display_name:
            update_data["displayName"] = display_name
        if description:
            update_data["description"] = description
        
        # Make the API request
        response = self._make_request(
            f"workspaces/{workspace_id}/lakehouses/{lakehouse_id}", 
            method="PATCH", 
            data=update_data
        )
        
        lakehouse = response.json()
        self._log(f"Lakehouse updated successfully: '{lakehouse.get('displayName')}'")
        return lakehouse
    
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
