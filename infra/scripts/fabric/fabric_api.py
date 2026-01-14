"""
Microsoft Fabric API Client Library

This module provides a pure Python client for interacting with Microsoft Fabric REST APIs.
It focuses on core API operations including authentication, request management, and 
low-level methods for Fabric resources (workspaces, folders, notebooks, items).

This library adheres strictly to Fabric API operations and does not contain business logic
or project-specific transformations. For UDFWF-specific functionality, see udfwf_utils.py.

Core Features:
- Authentication management with Azure CLI credentials
- HTTP request handling with error management
- Long Running Operation (LRO) support
- Workspace, folder, notebook, and item operations
- OneLake file system client integration

Dependencies:
    pip install requests azure-identity azure-storage-file-datalake

Author: Generated for Unified Data Foundation with Fabric (UDFWF) project
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
    
    Note: For workspace-specific operations, consider using FabricWorkspaceApiClient
    which provides the same functionality without requiring workspace_id parameters.
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
        icon = ""
        if level == "ERROR":
            icon = "❌"
        elif level == "WARNING":
            icon = "⚠️"
        print(f"{icon} {message}")
    
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
                                   max_wait_time: int = 1800, 
                                   check_interval: Optional[int] = None) -> requests.Response:
        """
        Wait for Long Running Operation to complete.
        
        This method polls the LRO status endpoint until completion, handling both standard
        HTTP status-based LROs (202 → 200) and Fabric-specific job status responses.
        
        Args:
            job_url: Full URL for monitoring the operation (including base URL)
            operation_name: Optional name for logging purposes only (e.g., "notebook creation")
            max_wait_time: Maximum time to wait in seconds (default: 1800 = 30 minutes)
            check_interval: Check interval in seconds (defaults to Retry-After header or 5s)
            
        Returns:
            Final response object with status 200
            
        Raises:
            FabricApiError: If operation fails, times out, or polling encounters errors
        """
        start_time = time.time()
        default_interval = check_interval or 5
        
        # Log operation start
        operation_display = operation_name if operation_name else "operation"
        self._log(f"Waiting for operation '{operation_display}' to complete...")
        
        while (time.time() - start_time) < max_wait_time:
            time.sleep(default_interval)
            
            try:
                # Make direct HTTP request to the job URL
                headers = {'Authorization': f'Bearer {self._get_auth_token()}'}
                response = requests.get(job_url, headers=headers, timeout=self.timeout_sec)
                
                if response.status_code == 200:
                    # Try to parse response and check for job status field
                    # Some Fabric operations (like notebook jobs) return 200 with a status field
                    try:
                        job_data = response.json()
                        
                        # Check if response contains a status field indicating job state
                        if 'status' in job_data:
                            job_status = job_data['status']
                            
                            # If job is still running, continue polling
                            if job_status in ['InProgress', 'Running', 'Queued', 'NotStarted']:
                                elapsed = time.time() - start_time
                                elapsed_str = self._format_duration(elapsed)
                                self._log(f"Operation '{operation_display}' status: '{job_status}' ({elapsed_str} elapsed)")
                                continue
                            
                            # If job failed, raise error with details
                            elif job_status in ['Failed', 'Cancelled']:
                                error_msg = job_data.get('failureReason', {}).get('message', 'Operation failed')
                                error_code = job_data.get('failureReason', {}).get('errorCode', 'Unknown')
                                error_message = f"Operation '{operation_display}' status: '{job_status}': {error_msg} (Code: {error_code})"
                                self._log(error_message, level="ERROR")
                                raise FabricApiError(
                                    error_message,
                                    status_code=None,
                                    response_data=job_data
                                )
                            
                            # If job completed successfully
                            elif job_status == 'Completed':
                                elapsed_str = self._format_duration(time.time() - start_time)
                                self._log(f"Operation '{operation_display}' completed successfully ({elapsed_str})")
                                return response
                            
                            # Unknown status - log warning but treat as completed
                            else:
                                self._log(f"Operation '{operation_display}' returned unknown status '{job_status}', treating as completed", level="WARNING")
                                return response
                        else:
                            # No status field - standard HTTP LRO (200 means complete)
                            elapsed_str = self._format_duration(time.time() - start_time)
                            self._log(f"Operation '{operation_display}' completed successfully ({elapsed_str})")
                            return response
                            
                    except (ValueError, json.JSONDecodeError):
                        # Response is not JSON - treat 200 as successful completion
                        elapsed_str = self._format_duration(time.time() - start_time)
                        self._log(f"Operation '{operation_display}' completed successfully ({elapsed_str})")
                        return response
                
                elif response.status_code == 202:
                    # Standard LRO - still in progress
                    elapsed = time.time() - start_time
                    elapsed_str = self._format_duration(elapsed)
                    self._log(f"Operation '{operation_display}' still in progress ({elapsed_str} elapsed)")
                    
                    # Update check interval from Retry-After header if not explicitly set
                    if not check_interval:
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                default_interval = min(int(retry_after), 60)  # Cap at 60 seconds
                            except ValueError:
                                pass  # Keep current interval if header is not a valid integer
                    continue
                
                elif response.status_code == 404:
                    # Job URL not found - might indicate completion or deletion
                    self._log(f"Operation '{operation_display}' job URL returned 404, operation may have completed", level="WARNING")
                    return response
                
                else:
                    # Unexpected status code
                    error_msg = f"Operation '{operation_display}' failed with HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_msg += f": {error_data['error'].get('message', response.text[:200])}"
                    except:
                        error_msg += f": {response.text[:200]}"
                    
                    self._log(error_msg, level="ERROR")
                    raise FabricApiError(error_msg, status_code=response.status_code)
                    
            except FabricApiError:
                raise
            except requests.RequestException as e:
                error_msg = f"Error polling operation '{operation_display}' status: {str(e)}"
                self._log(error_msg, level="ERROR")
                raise FabricApiError(error_msg)
        
        # Timeout reached
        elapsed_str = self._format_duration(max_wait_time)
        error_msg = f"Operation '{operation_display}' timed out after {elapsed_str}"
        self._log(error_msg, level="ERROR")
        raise FabricApiError(error_msg)
    
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
        
        try:
            response = self._make_request("capacities")
            capacities = response.json().get('value', [])
            self._log(f"Found {len(capacities)} capacity(ies)")
            return capacities
                
        except FabricApiError:
            raise
        except Exception as e:
            raise FabricApiError(f"Failed to get capacities: {str(e)}")

    def get_capacity(self, capacity_name: str) -> Optional[Dict[str, Any]]:
        """
        Get capacity by name.
        
        Args:
            capacity_name: Name of the capacity
            
        Returns:
            Capacity object if found, None otherwise
            
        Raises:
            FabricApiError: If request fails
        """
        capacities = self.get_capacities()
        capacity = next((c for c in capacities if c['displayName'].lower() == capacity_name.lower()), None)
        
        if not capacity:
            self._log(f"Capacity '{capacity_name}' not found")
            return None
        
        return capacity

    # Workspace operations
    def get_workspaces(self) -> List[Dict[str, Any]]:
        """
        Get all workspaces accessible to the user.
        
        Returns:
            List of workspace objects
            
        Raises:
            FabricApiError: If request fails
        """
        try:
            response = self._make_request("workspaces")
            
            if response.status_code == 200:
                workspaces = response.json().get('value', [])
                self._log(f"Found {len(workspaces)} workspaces")
                return workspaces
            else:
                error_msg = f"Failed to get workspaces: HTTP {response.status_code}"
                self._log(error_msg, level="ERROR")
                raise FabricApiError(error_msg)
                
        except FabricApiError:
            raise
        except Exception as e:
            error_msg = f"Error getting workspaces: {e}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)
    
    def get_workspace(self, workspace_name: str) -> Optional[Dict[str, Any]]:
        """
        Get workspace by name.
        
        Args:
            workspace_name: Name of the workspace
            
        Returns:
            Workspace object if found, None otherwise
            
        Raises:
            FabricApiError: If request fails
        """
        workspaces = self.get_workspaces()
        workspace = next((w for w in workspaces if w['displayName'].lower() == workspace_name.lower()), None)
        
        if not workspace:
            self._log(f"Workspace '{workspace_name}' not found")
            return None
        
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
            error_msg = f"Failed to assign workspace to capacity: HTTP {response.status_code}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)
    
    def delete_workspace(self, workspace_id: str) -> Optional[str]:
        """
        Delete a workspace.
        
        Args:
            workspace_id: ID of the workspace to delete
            
        Returns:
            Workspace ID if successfully deleted, None if workspace not found
            
        Raises:
            FabricApiError: If deletion fails due to unexpected error
            
        Required Scopes:
            Workspace.ReadWrite.All
            
        Reference:
            https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/delete-workspace
        """
        try:
            self._log(f"Deleting workspace {workspace_id}")
            
            response = self._make_request(
                f"workspaces/{workspace_id}", 
                method="DELETE"
            )
            
            if response.status_code == 200:
                self._log(f"Successfully deleted workspace")
                return workspace_id
            elif response.status_code == 404:
                self._log(f"Workspace {workspace_id} not found, nothing to delete")
                return None
            else:
                error_msg = f"Failed to delete workspace: HTTP {response.status_code}"
                self._log(error_msg, level="ERROR")
                raise FabricApiError(error_msg)
                
        except FabricApiError:
            raise
        except Exception as e:
            error_msg = f"Error deleting workspace: {e}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)
    
    def add_workspace_role_assignment(self, 
                                    workspace_id: str, 
                                    principal_id: str, 
                                    principal_type: str, 
                                    role: str,
                                    display_name: Optional[str] = None,
                                    user_principal_name: Optional[str] = None,
                                    aad_app_id: Optional[str] = None,
                                    group_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a workspace role assignment to grant permissions to a user, service principal, or group.
        
        Args:
            workspace_id: Target workspace ID
            principal_id: The principal's ID (user object ID, service principal ID, or group ID)
            principal_type: Type of principal ("User", "ServicePrincipal", "Group", "ServicePrincipalProfile", "EntireTenant")
            role: Workspace role ("Admin", "Member", "Contributor", "Viewer")
            display_name: Optional display name of the principal
            user_principal_name: Optional user principal name (required for User type)
            aad_app_id: Optional Azure AD App ID (required for ServicePrincipal type)
            group_type: Optional group type ("SecurityGroup", "DistributionList", "Unknown") for Group type
            
        Returns:
            WorkspaceRoleAssignment object containing:
            - id: Role assignment ID
            - principal: Principal object with ID, type, and details
            - role: Assigned workspace role
            
        Raises:
            FabricApiError: If role assignment fails
            
        Required Scopes:
            Workspace.ReadWrite.All
            
        Reference:
            https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/add-workspace-role-assignment
        """
        valid_principal_types = ["User", "ServicePrincipal", "Group", "ServicePrincipalProfile", "EntireTenant"]
        valid_roles = ["Admin", "Member", "Contributor", "Viewer"]
        valid_group_types = ["SecurityGroup", "DistributionList", "Unknown"]
        
        # Validate inputs
        if principal_type not in valid_principal_types:
            raise FabricApiError(f"Invalid principal_type '{principal_type}'. Must be one of: {valid_principal_types}")
        
        if role not in valid_roles:
            raise FabricApiError(f"Invalid role '{role}'. Must be one of: {valid_roles}")
        
        if group_type and group_type not in valid_group_types:
            raise FabricApiError(f"Invalid group_type '{group_type}'. Must be one of: {valid_group_types}")
        
        self._log(f"Adding {principal_type} role assignment '{role}' for principal {principal_id} to workspace {workspace_id}")
        
        # Build principal object
        principal = {
            "id": principal_id,
            "type": principal_type
        }
        
        # Add optional display name
        if display_name:
            principal["displayName"] = display_name
        
        # Add type-specific details
        if principal_type == "User" and user_principal_name:
            principal["userDetails"] = {
                "userPrincipalName": user_principal_name
            }
        elif principal_type == "ServicePrincipal" and aad_app_id:
            principal["servicePrincipalDetails"] = {
                "aadAppId": aad_app_id
            }
        elif principal_type == "Group" and group_type:
            principal["groupDetails"] = {
                "groupType": group_type
            }
        
        # Build request data
        data = {
            "principal": principal,
            "role": role
        }
        
        # Make the API request
        response = self._make_request(
            f"workspaces/{workspace_id}/roleAssignments", 
            method="POST", 
            data=data
        )
        
        if response.status_code == 201:
            role_assignment = response.json()
            self._log(f"Successfully added {role} role assignment for {principal_type} {principal_id}")
            return role_assignment
        else:
            error_msg = f"Failed to add workspace role assignment: HTTP {response.status_code}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)
    
    def get_workspace_role_assignments(self, 
                                     workspace_id: str,
                                     continuation_token: Optional[str] = None,
                                     get_all: bool = True) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Get workspace role assignments with support for pagination.
        
        Args:
            workspace_id: Target workspace ID
            continuation_token: Optional token for retrieving the next page of results
            get_all: If True, retrieves all role assignments across all pages. 
                    If False, returns the raw API response with pagination info.
            
        Returns:
            If get_all=True: List of WorkspaceRoleAssignment objects
            If get_all=False: Raw API response containing:
            - value: List of WorkspaceRoleAssignment objects
            - continuationToken: Token for next page (if more results exist)
            - continuationUri: URI for next page (if more results exist)
            
            Each WorkspaceRoleAssignment contains:
            - id: Role assignment ID
            - principal: Principal object with ID, type, display name, and type-specific details
            - role: Workspace role ("Admin", "Member", "Contributor", "Viewer")
            
        Raises:
            FabricApiError: If request fails
            
        Required Scopes:
            Workspace.Read.All or Workspace.ReadWrite.All
            
        Reference:
            https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/list-workspace-role-assignments
        """
        self._log(f"Getting workspace role assignments for workspace {workspace_id}")
        
        # Build query parameters
        params = []
        if continuation_token:
            params.append(f"continuationToken={continuation_token}")
        
        query_string = f"?{'&'.join(params)}" if params else ""
        uri = f"workspaces/{workspace_id}/roleAssignments{query_string}"
        
        # Make the API request
        response = self._make_request(uri)
        
        if response.status_code == 200:
            response_data = response.json()
            
            if get_all:
                # Collect all role assignments across all pages
                all_role_assignments = response_data.get('value', [])
                
                # Continue fetching pages if continuation token exists
                while 'continuationToken' in response_data:
                    next_token = response_data['continuationToken']
                    self._log(f"Fetching next page of role assignments (token: {next_token[:20]}...)")
                    
                    next_params = [f"continuationToken={next_token}"]
                    next_query = f"?{'&'.join(next_params)}"
                    next_uri = f"workspaces/{workspace_id}/roleAssignments{next_query}"
                    
                    next_response = self._make_request(next_uri)
                    if next_response.status_code == 200:
                        next_data = next_response.json()
                        all_role_assignments.extend(next_data.get('value', []))
                        response_data = next_data
                    else:
                        error_msg = f"Failed to fetch next page of role assignments: HTTP {next_response.status_code}"
                        self._log(error_msg, level="ERROR")
                        raise FabricApiError(error_msg)
                
                self._log(f"Retrieved {len(all_role_assignments)} total role assignment(s)")
                return all_role_assignments
            else:
                # Return raw response with pagination info
                role_assignments = response_data.get('value', [])
                self._log(f"Retrieved {len(role_assignments)} role assignment(s) in current page")
                return response_data
        else:
            error_msg = f"Failed to get workspace role assignments: HTTP {response.status_code}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)
    
    def get_workspace_role_assignment_by_principal(self, 
                                                  workspace_id: str, 
                                                  principal_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific workspace role assignment by principal ID.
        
        Args:
            workspace_id: Target workspace ID
            principal_id: Principal ID to search for
            
        Returns:
            WorkspaceRoleAssignment object if found, None otherwise
            
        Raises:
            FabricApiError: If request fails
        """
        self._log(f"Searching for role assignment for principal {principal_id} in workspace {workspace_id}")
        
        role_assignments = self.get_workspace_role_assignments(workspace_id, get_all=True)
        
        # Search for the specific principal
        for assignment in role_assignments:
            if assignment.get('principal', {}).get('id') == principal_id:
                self._log(f"Found role assignment: {assignment.get('role')} for principal {principal_id}")
                return assignment
        
        self._log(f"No role assignment found for principal {principal_id}")
        return None

    def create_eventhub_connection(self, name: str, namespace_name: str, event_hub_name: str, shared_access_policy_name: str, shared_access_key: str) -> Optional[Dict[str, Any]]:
        """
        Create an Event Hub connection.
        
        Args:
            name: Connection name
            namespace_name: Event Hub namespace name
            event_hub_name: Event Hub name
            shared_access_policy_name: Shared access policy name
            shared_access_key: Shared access key
            
        Returns:
            Connection object if created successfully
            
        Raises:
            FabricApiError: If connection creation fails
        """
        self._log(f"Creating Event Hub connection '{name}'")
        
        data = {
            "displayName": name,
            "connectionDetails": {
                "type": "EventHub",
                "path": f"{namespace_name}.servicebus.windows.net",
                "eventHubName": event_hub_name,
                "sharedAccessPolicyName": shared_access_policy_name,
                "sharedAccessKey": shared_access_key
            }
        }
        
        response = self._make_request("connections", method="POST", data=data)
        
        if response.status_code == 201:
            connection = response.json()
            self._log(f"Successfully created Event Hub connection '{name}' with ID {connection['id']}")
            return connection
        else:
            error_msg = f"Failed to create Event Hub connection '{name}': HTTP {response.status_code}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)

    def update_eventhub_connection(self, connection_id: str, name: str, namespace_name: str, event_hub_name: str, shared_access_policy_name: str, shared_access_key: str) -> Optional[Dict[str, Any]]:
        """
        Update an existing Event Hub connection.
        
        Args:
            connection_id: Connection ID to update
            name: Connection name
            namespace_name: Event Hub namespace name
            event_hub_name: Event Hub name
            shared_access_policy_name: Shared access policy name
            shared_access_key: Shared access key
            
        Returns:
            Updated connection object if successful
            
        Raises:
            FabricApiError: If connection update fails
        """
        self._log(f"Updating Event Hub connection '{name}' (ID: {connection_id})")
        
        data = {
            "displayName": name,
            "connectionDetails": {
                "type": "EventHub",
                "path": f"{namespace_name}.servicebus.windows.net",
                "eventHubName": event_hub_name,
                "sharedAccessPolicyName": shared_access_policy_name,
                "sharedAccessKey": shared_access_key
            }
        }
        
        response = self._make_request(f"connections/{connection_id}", method="PATCH", data=data)
        
        if response.status_code == 200:
            connection = response.json()
            self._log(f"Successfully updated Event Hub connection '{name}'")
            return connection
        else:
            error_msg = f"Failed to update Event Hub connection '{name}': HTTP {response.status_code}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """
        List all connections.
        
        Returns:
            List of connection objects
            
        Raises:
            FabricApiError: If request fails
        """
        try:
            response = self._make_request("connections")
            
            if response.status_code == 200:
                connections = response.json().get('value', [])
                self._log(f"Found {len(connections)} connection(s)")
                return connections
            else:
                error_msg = f"Failed to list connections: HTTP {response.status_code}"
                self._log(error_msg, level="ERROR")
                raise FabricApiError(error_msg)
                
        except FabricApiError:
            raise
        except Exception as e:
            error_msg = f"Error listing connections: {e}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)
    
    def get_connection(self, connection_id: str) -> Dict[str, Any]:
        """
        Get a specific connection by ID.
        
        Args:
            connection_id: Connection ID
            
        Returns:
            Connection object
            
        Raises:
            FabricApiError: If connection not found or request fails
        """
        try:
            response = self._make_request(f"connections/{connection_id}")
            
            if response.status_code == 200:
                connection = response.json()
                self._log(f"Retrieved connection: {connection_id}")
                return connection
            else:
                error_msg = f"Failed to get connection {connection_id}: HTTP {response.status_code}"
                self._log(error_msg, level="ERROR")
                raise FabricApiError(error_msg)
                
        except FabricApiError:
            raise
        except Exception as e:
            error_msg = f"Error getting connection: {e}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)
    
    def delete_connection(self, connection_id: str) -> Optional[str]:
        """
        Delete a connection.
        
        Args:
            connection_id: Connection ID to delete
            
        Returns:
            Connection ID if successfully deleted, None if not found
            
        Raises:
            FabricApiError: If deletion fails due to unexpected error
        """
        try:
            self._log(f"Deleting connection: {connection_id}")
            
            response = self._make_request(f"connections/{connection_id}", method="DELETE")
            
            if response.status_code == 200:
                self._log(f"Successfully deleted connection: {connection_id}")
                return connection_id
            elif response.status_code == 404:
                self._log(f"Connection {connection_id} not found, nothing to delete")
                return None
            else:
                error_msg = f"Failed to delete connection: HTTP {response.status_code}"
                self._log(error_msg, level="ERROR")
                raise FabricApiError(error_msg)
                
        except FabricApiError:
            raise
        except Exception as e:
            error_msg = f"Error deleting connection: {e}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)

    def list_supported_connection_types(self) -> List[Dict[str, Any]]:
        """
        List all supported connection types.
        
        Returns:
            List of supported connection types
            
        Raises:
            FabricApiError: If request fails
        """
        try:
            response = self._make_request("connections/supportedTypes")
            
            if response.status_code == 200:
                connection_types = response.json().get('value', [])
                self._log(f"Found {len(connection_types)} supported connection type(s)")
                return connection_types
            else:
                error_msg = f"Failed to list supported connection types: HTTP {response.status_code}"
                self._log(error_msg, level="ERROR")
                raise FabricApiError(error_msg)
                
        except FabricApiError:
            raise
        except Exception as e:
            error_msg = f"Error listing supported connection types: {e}"
            self._log(error_msg, level="ERROR")
            raise FabricApiError(error_msg)


class FabricWorkspaceApiClient(FabricApiClient):
    """
    Fabric API client scoped to a specific workspace.
    
    This class inherits from FabricApiClient and provides workspace-specific methods
    without requiring workspace_id as a parameter for each method call.
    """
    
    def __init__(self, 
                 workspace_id: str,
                 api_url: str = "https://api.fabric.microsoft.com/v1",
                 resource_url: str = "https://api.fabric.microsoft.com",
                 credential: Optional[Any] = None,
                 timeout_sec: int = 240):
        """
        Initialize the workspace-scoped Fabric API client.
        
        Args:
            workspace_id: Target workspace ID
            api_url: Base URL for Fabric API
            resource_url: Resource URL for authentication scope
            credential: Azure credential object (defaults to AzureCliCredential)
            timeout_sec: Default timeout for API requests
        """
        super().__init__(api_url, resource_url, credential, timeout_sec)
        self.workspace_id = workspace_id
        self._log(f"Initialized FabricWorkspaceApiClient for workspace {workspace_id}")
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """
        Get information about the current workspace.
        
        Returns:
            Workspace object
        """
        try:
            response = self._make_request(f"workspaces/{self.workspace_id}")
            return response.json()
        except Exception as e:
            self._log(f"Failed to get workspace info: {str(e)}", "ERROR")
            raise FabricApiError(f"Failed to get workspace {self.workspace_id}: {str(e)}")
    
    def get_items(self, item_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get items from the workspace.
        
        Args:
            item_type: Optional filter by item type
            
        Returns:
            List of items
        """
        response = self._make_request(f"workspaces/{self.workspace_id}/items")
        items = response.json().get('value', [])
        
        if item_type:
            items = [item for item in items if item.get('type', '').lower() == item_type.lower()]
        
        return items
    
    def assign_to_capacity(self, capacity_id: str) -> None:
        """Assign the workspace to a capacity."""
        super().assign_workspace_to_capacity(self.workspace_id, capacity_id)
    
    def delete(self) -> Optional[str]:
        """Delete the workspace."""
        return super().delete_workspace(self.workspace_id)
    
    # Folder operations
    def get_folders(self) -> List[Dict[str, Any]]:
        """Get all folders in the workspace."""
        response = self._make_request(f"workspaces/{self.workspace_id}/folders")
        return response.json().get('value', [])
    
    def create_folder(self, display_name: str, parent_folder_id: Optional[str] = None) -> str:
        """
        Create a folder in the workspace.
        
        Args:
            display_name: Folder name
            parent_folder_id: Parent folder ID (None for root)
            
        Returns:
            Folder ID
        """
        data = {"displayName": display_name}
        if parent_folder_id:
            data["parentFolderId"] = parent_folder_id
        
        response = self._make_request(f"workspaces/{self.workspace_id}/folders", method="POST", data=data)
        return response.json()['id']
    
    # Notebook operations
    def get_notebooks(self) -> Dict[str, str]:
        """
        Get all notebooks in the workspace.
        
        Returns:
            Dictionary mapping notebook names to IDs
        """
        response = self._make_request(f"workspaces/{self.workspace_id}/notebooks")
        notebooks = response.json().get('value', [])
        return {notebook['displayName']: notebook['id'] for notebook in notebooks}
    
    def get_notebook(self, notebook_id: str) -> Dict[str, Any]:
        """
        Get properties of a specific notebook.
        
        Args:
            notebook_id: Notebook ID
            
        Returns:
            Notebook object containing:
            - id: Notebook ID (GUID)
            - displayName: Notebook display name
            - description: Notebook description
            - type: Item type ("Notebook")
            - workspaceId: Workspace ID (GUID)
            - properties: Notebook properties
            - folderId: Folder ID (if in a folder)
            - definition: Notebook definition (if requested)
            
        Raises:
            FabricApiError: If notebook not found or request fails
            
        Required Scopes:
            Notebook.Read.All or Notebook.ReadWrite.All or Item.Read.All or Item.ReadWrite.All
            
        Reference:
            https://learn.microsoft.com/en-us/rest/api/fabric/notebook/items/get-notebook
        """
        self._log(f"Getting notebook {notebook_id} from workspace {self.workspace_id}")
        response = self._make_request(f"workspaces/{self.workspace_id}/notebooks/{notebook_id}")
        notebook = response.json()
        self._log(f"Retrieved notebook '{notebook.get('displayName', 'Unknown')}'")
        return notebook
    
    def create_notebook(self, notebook_data: Dict[str, Any], wait_for_lro: bool = True) -> requests.Response:
        """
        Create a new notebook.
        
        Args:
            notebook_data: Notebook definition data
            wait_for_lro: Whether to wait for long running operations to complete
            
        Returns:
            API response
        """
        return self._make_request(f"workspaces/{self.workspace_id}/notebooks", method="POST", data=notebook_data, wait_for_lro=wait_for_lro)
    
    def update_notebook(self, notebook_id: str, notebook_data: Dict[str, Any], wait_for_lro: bool = True) -> requests.Response:
        """
        Update an existing notebook.
        
        Args:
            notebook_id: Notebook ID to update
            notebook_data: Notebook definition data
            wait_for_lro: Whether to wait for long running operations to complete
            
        Returns:
            API response
        """
        return self._make_request(
            f"workspaces/{self.workspace_id}/notebooks/{notebook_id}/updateDefinition", 
            method="POST", 
            data=notebook_data,
            wait_for_lro=wait_for_lro
        )
    
    # Lakehouse operations
    def get_lakehouses(self) -> List[Dict[str, Any]]:
        """
        Get all lakehouses from the workspace.
        
        Returns:
            List of lakehouse objects
        """
        self._log(f"Getting lakehouses from workspace {self.workspace_id}")
        response = self._make_request(f"workspaces/{self.workspace_id}/lakehouses")
        lakehouses = response.json().get('value', [])
        self._log(f"Found {len(lakehouses)} lakehouse(s)")
        return lakehouses
    
    def get_lakehouse(self, lakehouse_id: str) -> Dict[str, Any]:
        """
        Get properties of a specific lakehouse.
        
        Args:
            lakehouse_id: Lakehouse ID
            
        Returns:
            Lakehouse object
        """
        self._log(f"Getting lakehouse {lakehouse_id} from workspace {self.workspace_id}")
        response = self._make_request(f"workspaces/{self.workspace_id}/lakehouses/{lakehouse_id}")
        lakehouse = response.json()
        self._log(f"Retrieved lakehouse '{lakehouse.get('displayName', 'Unknown')}'")
        return lakehouse
    
    def get_lakehouse_by_name(self, lakehouse_name: str) -> Dict[str, Any]:
        """
        Get lakehouse by display name.
        
        Args:
            lakehouse_name: Display name of the lakehouse
            
        Returns:
            Lakehouse object
            
        Raises:
            FabricApiError: If lakehouse not found
        """
        lakehouses = self.get_lakehouses()
        lakehouse = next((lh for lh in lakehouses if lh['displayName'].lower() == lakehouse_name.lower()), None)
        
        if not lakehouse:
            raise FabricApiError(f"Lakehouse '{lakehouse_name}' not found in workspace {self.workspace_id}")
        
        return lakehouse
    
    def create_lakehouse(self, 
                        display_name: str,
                        description: Optional[str] = None,
                        folder_id: Optional[str] = None,
                        enable_schemas: bool = True,
                        wait_for_lro: bool = True) -> Dict[str, Any]:
        """
        Create a new lakehouse in the workspace.
        
        Args:
            display_name: Lakehouse display name
            description: Optional lakehouse description
            folder_id: Optional folder ID
            enable_schemas: Whether to enable schemas
            wait_for_lro: Whether to wait for long running operations to complete
            
        Returns:
            Lakehouse object
        """
        self._log(f"Creating lakehouse '{display_name}' in workspace {self.workspace_id}")
        
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
            f"workspaces/{self.workspace_id}/lakehouses", 
            method="POST", 
            data=lakehouse_data,
            wait_for_lro=wait_for_lro
        )
        
        if response.status_code in [201, 200]:
            lakehouse = response.json()
            self._log(f"Lakehouse '{display_name}' created successfully with ID: {lakehouse.get('id')}")
            return lakehouse
        else:
            raise FabricApiError(f"Failed to create lakehouse '{display_name}': {response.status_code} {response.text}")
    
    def update_lakehouse(self, 
                        lakehouse_id: str,
                        display_name: Optional[str] = None,
                        description: Optional[str] = None) -> Dict[str, Any]:
        """
        Update properties of an existing lakehouse.
        
        Args:
            lakehouse_id: Lakehouse ID to update
            display_name: New lakehouse display name (optional)
            description: New lakehouse description (optional)
            
        Returns:
            Updated lakehouse object
        """
        if not display_name and not description:
            raise FabricApiError("At least one property (display_name or description) must be provided for update")
        
        self._log(f"Updating lakehouse {lakehouse_id} in workspace {self.workspace_id}")
        
        # Prepare request data
        update_data = {}
        if display_name:
            update_data["displayName"] = display_name
        if description:
            update_data["description"] = description
        
        # Make the API request
        response = self._make_request(
            f"workspaces/{self.workspace_id}/lakehouses/{lakehouse_id}", 
            method="PATCH", 
            data=update_data
        )
        
        lakehouse = response.json()
        self._log(f"Lakehouse updated successfully: '{lakehouse.get('displayName')}'")
        return lakehouse
    
    # Notebook execution operations
    def schedule_notebook_job(self, notebook_id: str) -> Dict[str, Any]:
        """
        Schedule a single notebook job and monitor its completion.
        
        Args:
            notebook_id: Notebook ID to execute
            
        Returns:
            Dictionary with execution results including status, duration, and details
        """
        job_url = f"workspaces/{self.workspace_id}/items/{notebook_id}/jobs/instances?jobType=RunNotebook"
        start_time = time.time()

        notebook_name = self.get_notebook(notebook_id).get('displayName', 'Unknown')
        self._log(f"Scheduling execution for notebook '{notebook_name}' (ID: {notebook_id})")
        response = self._make_request(job_url, method="POST", wait_for_lro=False)
        
        # Handle immediate completion (HTTP 200)
        if response.status_code == 200:
            job_data = response.json() if response.content else {}
            duration_str = self._format_duration(time.time() - start_time)
            self._log(f"Notebook '{notebook_name}' (ID: {notebook_id}) completed immediately (synchronous)")
            return {'status': 'Completed', 'duration': duration_str, 'details': job_data}
        
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
                    operation_name=f"Run notebook '{notebook_name}' (ID: {notebook_id})",
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

    # Data Agent operations
    def create_data_agent(self, data_agent_name: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new Data Agent in the workspace. Reference: https://pypi.org/project/fabric-data-agent-sdk/
        
        Args:
            data_agent_name: The name of the Data Agent to be created.
            folder_id: Optional folder ID where to create the data agent
            
        Returns:
            Dictionary with data agent information including:
            - id: Data agent ID (GUID)
            - displayName: Data agent display name
            - type: Item type ("DataAgent")
            - workspaceId: Workspace ID (GUID)
            
        Raises:
            FabricApiError: If creation fails
            
        Required Scopes:
            DataAgent.ReadWrite.All or Item.ReadWrite.All
            
        Required Permissions:
            Contributor workspace role or higher
        """
        try:
            # Validate required parameters
            if not data_agent_name or not data_agent_name.strip():
                raise FabricApiError("data_agent_name is required and cannot be empty")
            
            self._log(f"Creating Data Agent '{data_agent_name}' in workspace {self.workspace_id}")
            
            # Build request payload following the pattern from the original function
            data = {
                "artifactType": "LLMPlugin",
                "displayName": data_agent_name.strip()
            }
            
            # Add optional folder ID
            if folder_id:
                data["folderId"] = folder_id
                self._log(f"Creating Data Agent in folder {folder_id}")
            
            # Make the API request using the dataagents endpoint
            response = self._make_request(
                f"workspaces/{self.workspace_id}/dataagents", 
                method="POST", 
                data=data
            )
            
            # Check response status
            if response.status_code in [200, 201, 202]:
                data_agent = response.json()
                data_agent_id = data_agent.get('id')
                
                # If ID is not returned in response, get it by searching by name
                if not data_agent_id:
                    self._log(f"Data Agent ID not returned in response, searching by name")
                    found_agent = self.get_data_agent_by_name(data_agent_name.strip())
                    if found_agent and found_agent.get('id'):
                        data_agent = found_agent
                        data_agent_id = found_agent['id']
                    else:
                        raise FabricApiError(f"Data Agent '{data_agent_name}' was created but could not be found or retrieved")
                
                self._log(f"Successfully created Data Agent '{data_agent_name}' with ID: {data_agent_id}")
                return data_agent
            else:
                raise FabricApiError(f"Failed to create Data Agent: HTTP {response.status_code}")
                
        except FabricApiError:
            # Re-raise FabricApiError as-is
            raise
        except Exception as e:
            raise FabricApiError(f"Unexpected error creating Data Agent '{data_agent_name}': {str(e)}")
    
    def get_data_agents(self) -> List[Dict[str, Any]]:
        """
        Get all Data Agents in the workspace.
        
        Returns:
            List of data agent objects
            
        Raises:
            FabricApiError: If listing fails
            
        Required Scopes:
            DataAgent.Read.All or Item.Read.All
            
        Required Permissions:
            Viewer workspace role or higher
        """
        try:
            self._log(f"Getting Data Agents in workspace {self.workspace_id}")
            
            # Make the API request to list dataagents
            response = self._make_request(
                f"workspaces/{self.workspace_id}/dataagents", 
                method="GET"
            )
            
            # Check response status
            if response.status_code == 200:
                data_agents = response.json().get('value', [])
                self._log(f"Found {len(data_agents)} Data Agent(s)")
                return data_agents
            else:
                raise FabricApiError(f"Failed to list Data Agents: HTTP {response.status_code}")
                
        except FabricApiError:
            # Re-raise FabricApiError as-is
            raise
        except Exception as e:
            raise FabricApiError(f"Unexpected error listing Data Agents: {str(e)}")

    def get_data_agent_by_name(self, data_agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a Data Agent by name from the workspace.
        
        Args:
            data_agent_name: The name of the Data Agent to find.
            
        Returns:
            Dictionary with data agent information if found, None otherwise
            
        Raises:
            FabricApiError: If listing fails
            
        Required Scopes:
            DataAgent.Read.All or Item.Read.All
            
        Required Permissions:
            Viewer workspace role or higher
        """
        try:
            # Validate required parameters
            if not data_agent_name or not data_agent_name.strip():
                raise FabricApiError("data_agent_name is required and cannot be empty")
            
            self._log(f"Searching for Data Agent '{data_agent_name}' in workspace {self.workspace_id}")
            
            # Get all data agents
            data_agents = self.get_data_agents()
            
            # Find the data agent by name
            for agent in data_agents:
                if agent.get('displayName', '').strip() == data_agent_name.strip():
                    self._log(f"Found Data Agent '{data_agent_name}' with ID: {agent.get('id', 'N/A')}")
                    return agent
            
            self._log(f"Data Agent '{data_agent_name}' not found")
            return None
                
        except FabricApiError:
            # Re-raise FabricApiError as-is
            raise
        except Exception as e:
            raise FabricApiError(f"Unexpected error searching for Data Agent '{data_agent_name}': {str(e)}")

    # Environment operations
    def create_environment(self,
                          display_name: str,
                          description: Optional[str] = None,
                          folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new environment in the workspace.
        
        Args:
            display_name: Display name for the environment
            description: Optional description for the environment
            folder_id: Optional folder ID where to create the environment
            
        Returns:
            Dictionary containing the created environment details
            
        Raises:
            FabricApiError: If creation fails
            
        Required Scopes:
            Environment.ReadWrite.All or Item.ReadWrite.All
            
        Required Permissions:
            Contributor workspace role or higher
        """
        self._log(f"Creating environment '{display_name}' in workspace {self.workspace_id}")
        
        # Build request body
        request_body = {
            "displayName": display_name
        }
        
        if description:
            request_body["description"] = description
            
        if folder_id:
            request_body["folderId"] = folder_id
        
        response = self._make_request(
            uri=f"workspaces/{self.workspace_id}/environments",
            method="POST",
            data=request_body,
            wait_for_lro=True
        )
        
        if response.status_code in [201, 202]:
            self._log(f"Successfully created environment '{display_name}'")
            return response.json()
        else:
            self._log(f"Failed to create environment '{display_name}': {response.status_code} - {response.text}", "ERROR")
            raise FabricApiError(f"Failed to create environment: {response.text}", response.status_code, response.json() if response.content else None)

    def list_environments(self, 
                         continuation_token: Optional[str] = None,
                         get_all: bool = True) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        List environments in the workspace.
        
        Args:
            continuation_token: Optional continuation token for pagination
            get_all: If True, retrieves all environments by handling pagination automatically
            
        Returns:
            Dictionary with environment list and pagination info, or List of all environments if get_all=True
            
        Raises:
            FabricApiError: If request fails
            
        Required Scopes:
            Environment.Read.All or Item.Read.All
            
        Required Permissions:
            Viewer workspace role or higher
        """
        self._log(f"Listing environments in workspace {self.workspace_id}")
        
        if not get_all:
            # Single page request
            uri = f"workspaces/{self.workspace_id}/environments"
            if continuation_token:
                uri += f"?continuationToken={continuation_token}"
                
            response = self._make_request(uri=uri, method="GET", wait_for_lro=False)
            
            if response.status_code == 200:
                result = response.json()
                self._log(f"Successfully retrieved {len(result.get('value', []))} environments")
                return result
            else:
                self._log(f"Failed to list environments: {response.status_code} - {response.text}", "ERROR")
                raise FabricApiError(f"Failed to list environments: {response.text}", response.status_code, response.json() if response.content else None)
        else:
            # Get all environments with automatic pagination
            all_environments = []
            current_token = continuation_token
            
            while True:
                uri = f"workspaces/{self.workspace_id}/environments"
                if current_token:
                    uri += f"?continuationToken={current_token}"
                    
                response = self._make_request(uri=uri, method="GET", wait_for_lro=False)
                
                if response.status_code == 200:
                    result = response.json()
                    environments = result.get('value', [])
                    all_environments.extend(environments)
                    
                    # Check if there are more pages
                    current_token = result.get('continuationToken')
                    if not current_token:
                        break
                else:
                    self._log(f"Failed to list environments: {response.status_code} - {response.text}", "ERROR")
                    raise FabricApiError(f"Failed to list environments: {response.text}", response.status_code, response.json() if response.content else None)
            
            self._log(f"Successfully retrieved {len(all_environments)} environments")
            return all_environments

    def get_environment_by_name(self, environment_name: str) -> Optional[Dict[str, Any]]:
        """
        Get an environment by its display name.
        
        Args:
            environment_name: Display name of the environment to find
            
        Returns:
            Dictionary containing the environment details if found, None otherwise
            
        Raises:
            FabricApiError: If request fails
            
        Required Scopes:
            Environment.Read.All or Item.Read.All
            
        Required Permissions:
            Viewer workspace role or higher
        """
        self._log(f"Getting environment by name: '{environment_name}'")
        
        try:
            environments = self.list_environments(get_all=True)
            
            for env in environments:
                if env.get('displayName') == environment_name:
                    self._log(f"Found environment '{environment_name}' with ID: {env.get('id')}")
                    return env
                    
            self._log(f"Environment '{environment_name}' not found")
            return None
            
        except Exception as e:
            self._log(f"Error getting environment by name '{environment_name}': {str(e)}", "ERROR")
            return None

    def delete_environment(self, environment_id: str) -> bool:
        """
        Delete an environment from the workspace.
        
        Args:
            environment_id: ID of the environment to delete
            
        Returns:
            True if deletion was successful, False otherwise
            
        Raises:
            FabricApiError: If deletion fails
            
        Required Scopes:
            Environment.ReadWrite.All or Item.ReadWrite.All
            
        Required Permissions:
            Write permissions for the environment
        """
        self._log(f"Deleting environment with ID: {environment_id}")
        
        try:
            response = self._make_request(
                uri=f"workspaces/{self.workspace_id}/environments/{environment_id}",
                method="DELETE",
                wait_for_lro=False
            )
            
            if response.status_code == 200:
                self._log(f"Successfully deleted environment {environment_id}")
                return True
            else:
                self._log(f"Failed to delete environment {environment_id}: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self._log(f"Error deleting environment {environment_id}: {str(e)}", "ERROR")
            return False

    def publish_environment(self, environment_id: str) -> Dict[str, Any]:
        """
        Trigger a publish operation for an environment.
        
        Args:
            environment_id: ID of the environment to publish
            
        Returns:
            Dictionary containing the publish operation details
            
        Raises:
            FabricApiError: If publish fails
            
        Required Scopes:
            Environment.ReadWrite.All or Item.ReadWrite.All
            
        Required Permissions:
            Write permissions for the environment
        """
        self._log(f"Publishing environment with ID: {environment_id}")
        
        response = self._make_request(
            uri=f"workspaces/{self.workspace_id}/environments/{environment_id}/staging/publish?beta=false",
            method="POST",
            wait_for_lro=True
        )
        
        if response.status_code in [200, 202]:
            self._log(f"Successfully triggered publish for environment {environment_id}")
            return response.json()
        else:
            self._log(f"Failed to publish environment {environment_id}: {response.status_code} - {response.text}", "ERROR")
            raise FabricApiError(f"Failed to publish environment: {response.text}", response.status_code, response.json() if response.content else None)

    def update_environment_definition(self,
                                     environment_id: str,
                                     environment_yml_base64: Optional[str] = None,
                                     sparkcompute_yml_base64: Optional[str] = None,
                                     platform_base64: Optional[str] = None) -> bool:
        """
        Update the definition of an environment.
        
        Args:
            environment_id: ID of the environment to update
            environment_yml_base64: Optional base64 encoded environment.yml content
            sparkcompute_yml_base64: Optional base64 encoded Sparkcompute.yml content
            platform_base64: Optional base64 encoded .platform content
            
        Returns:
            True if update was successful, False otherwise
            
        Raises:
            FabricApiError: If update fails
            
        Required Scopes:
            Environment.ReadWrite.All or Item.ReadWrite.All
            
        Required Permissions:
            Write permissions for the environment
            
        Note:
            update_metadata is automatically set to True if platform_base64 is provided, False otherwise
        """
        self._log(f"Updating definition for environment {environment_id}")
        
        # Build definition parts
        definition_parts = []
        
        if environment_yml_base64:
            definition_parts.append({
                "path": "Libraries/PublicLibraries/environment.yml",
                "payload": environment_yml_base64,
                "payloadType": "InlineBase64"
            })
            
        if sparkcompute_yml_base64:
            definition_parts.append({
                "path": "Setting/Sparkcompute.yml",
                "payload": sparkcompute_yml_base64,
                "payloadType": "InlineBase64"
            })
            
        if platform_base64:
            definition_parts.append({
                "path": ".platform",
                "payload": platform_base64,
                "payloadType": "InlineBase64"
            })
        
        if not definition_parts:
            self._log("No definition parts provided for update", "ERROR")
            return False
            
        request_body = {
            "definition": {
                "parts": definition_parts
            }
        }
        
        # Auto-determine update_metadata based on platform_base64
        update_metadata = platform_base64 is not None
        
        uri = f"workspaces/{self.workspace_id}/environments/{environment_id}/updateDefinition"
        if update_metadata:
            uri += "?updateMetadata=true"
        
        response = self._make_request(
            uri=uri,
            method="POST",
            data=request_body,
            wait_for_lro=True
        )
        
        if response.status_code in [200, 202]:
            self._log(f"Successfully updated definition for environment {environment_id}")
            return True
        else:
            self._log(f"Failed to update environment definition {environment_id}: {response.status_code} - {response.text}", "ERROR")
            return False


# Convenience functions
def create_fabric_client(credential: Optional[Any] = None) -> FabricApiClient:
    """
    Create a new Fabric API client.
    
    Args:
        credential: Azure credential (defaults to AzureCliCredential)
        
    Returns:
        FabricApiClient instance
        
    Note: For workspace-specific operations, consider using create_workspace_fabric_client()
    which provides cleaner APIs without workspace_id parameters.
    """
    return FabricApiClient(credential=credential)


def create_workspace_fabric_client(workspace_id: str, credential: Optional[Any] = None) -> FabricWorkspaceApiClient:
    """
    Create a new workspace-scoped Fabric API client.
    
    Args:
        workspace_id: Target workspace ID
        credential: Azure credential (defaults to AzureCliCredential)
        
    Returns:
        FabricWorkspaceApiClient instance
    """
    return FabricWorkspaceApiClient(workspace_id, credential=credential)
