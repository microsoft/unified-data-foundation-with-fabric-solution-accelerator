"""
Unit tests for fabric_api.py

Tests for FabricApiClient class and helper functions.
"""

import json
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import requests

from fabric_api import FabricApiClient, FabricApiError


class TestFabricApiError(unittest.TestCase):
    """Test cases for FabricApiError exception class"""
    
    def test_error_with_message_only(self):
        """Test error with message only"""
        error = FabricApiError("Test error message")
        self.assertEqual(str(error), "Test error message")
        self.assertIsNone(error.status_code)
        self.assertIsNone(error.response_data)
    
    def test_error_with_status_code(self):
        """Test error with status code"""
        error = FabricApiError("Test error", status_code=404)
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 404)
        self.assertIsNone(error.response_data)
    
    def test_error_with_all_params(self):
        """Test error with all parameters"""
        response_data = {"error": {"code": "NotFound", "message": "Resource not found"}}
        error = FabricApiError("Test error", status_code=404, response_data=response_data)
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.response_data, response_data)


class TestFabricApiClientInit(unittest.TestCase):
    """Test cases for FabricApiClient initialization"""
    
    @patch('fabric_api.AzureCliCredential')
    def test_default_initialization(self, mock_credential):
        """Test default initialization"""
        client = FabricApiClient()
        self.assertEqual(client.api_url, "https://api.fabric.microsoft.com/v1")
        self.assertEqual(client.resource_url, "https://api.fabric.microsoft.com")
        self.assertEqual(client.timeout_sec, 240)
        mock_credential.assert_called_once()
    
    @patch('fabric_api.AzureCliCredential')
    def test_custom_initialization(self, mock_credential):
        """Test custom initialization"""
        custom_credential = Mock()
        client = FabricApiClient(
            api_url="https://custom.api.com/v2/",
            resource_url="https://custom.api.com",
            credential=custom_credential,
            timeout_sec=120
        )
        self.assertEqual(client.api_url, "https://custom.api.com/v2")
        self.assertEqual(client.resource_url, "https://custom.api.com")
        self.assertEqual(client.timeout_sec, 120)
        self.assertEqual(client._credential, custom_credential)
        mock_credential.assert_not_called()


class TestFabricApiClientHelpers(unittest.TestCase):
    """Test cases for FabricApiClient helper methods"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential):
        """Set up test fixtures"""
        self.mock_credential = mock_credential
        self.client = FabricApiClient()
    
    def test_log_outputs_message(self):
        """Test that _log outputs message with timestamp"""
        with patch('builtins.print') as mock_print:
            self.client._log("Test message")
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            self.assertIn("INFO", call_args)
            self.assertIn("Test message", call_args)
    
    def test_log_with_level(self):
        """Test _log with custom level"""
        with patch('builtins.print') as mock_print:
            self.client._log("Test warning", level="WARNING")
            call_args = mock_print.call_args[0][0]
            self.assertIn("WARNING", call_args)
            self.assertIn("Test warning", call_args)
    
    def test_format_duration_seconds_only(self):
        """Test _format_duration with seconds only"""
        result = self.client._format_duration(45)
        self.assertEqual(result, "0m 45s")
    
    def test_format_duration_minutes_and_seconds(self):
        """Test _format_duration with minutes and seconds"""
        result = self.client._format_duration(150)
        self.assertEqual(result, "2m 30s")
    
    def test_format_duration_large_value(self):
        """Test _format_duration with large value"""
        result = self.client._format_duration(3661)
        self.assertEqual(result, "61m 1s")


class TestFabricApiClientAuth(unittest.TestCase):
    """Test cases for FabricApiClient authentication"""
    
    def test_get_auth_token_success(self):
        """Test successful token retrieval"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        mock_credential.get_token.return_value = mock_token
        
        with patch('fabric_api.AzureCliCredential', return_value=mock_credential):
            client = FabricApiClient()
            token = client._get_auth_token()
            
            self.assertEqual(token, "test_token")
            mock_credential.get_token.assert_called_once_with("https://api.fabric.microsoft.com/.default")
    
    def test_get_auth_token_caches_token(self):
        """Test that token is cached on subsequent calls"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        mock_credential.get_token.return_value = mock_token
        
        with patch('fabric_api.AzureCliCredential', return_value=mock_credential):
            client = FabricApiClient()
            token1 = client._get_auth_token()
            token2 = client._get_auth_token()
            
            self.assertEqual(token1, token2)
            # get_token should only be called once due to caching
            self.assertEqual(mock_credential.get_token.call_count, 1)
    
    def test_get_auth_token_failure(self):
        """Test token retrieval failure"""
        mock_credential = Mock()
        mock_credential.get_token.side_effect = Exception("Auth failed")
        
        with patch('fabric_api.AzureCliCredential', return_value=mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client._get_auth_token()
            
            self.assertIn("Authentication failed", str(context.exception))


class TestFabricApiClientMakeRequest(unittest.TestCase):
    """Test cases for FabricApiClient._make_request method"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
    
    @patch('fabric_api.requests.request')
    def test_make_request_get_success(self, mock_request):
        """Test successful GET request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            response = client._make_request("workspaces")
            
            self.assertEqual(response.status_code, 200)
            mock_request.assert_called_once()
    
    @patch('fabric_api.requests.request')
    def test_make_request_post_with_data(self, mock_request):
        """Test POST request with JSON data"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {"id": "new-id"}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            data = {"displayName": "Test Workspace"}
            response = client._make_request("workspaces", method="POST", data=data)
            
            self.assertEqual(response.status_code, 201)
            call_args = mock_request.call_args
            self.assertEqual(call_args[1]['method'], 'POST')
            self.assertEqual(call_args[1]['data'], json.dumps(data))
    
    @patch('fabric_api.requests.request')
    def test_make_request_rate_limiting(self, mock_request):
        """Test rate limiting handling with retry"""
        # First call returns 429, second call succeeds
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'requestId': '12345', 'Retry-After': '1'}
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {'requestId': '12346'}
        success_response.json.return_value = {"data": "success"}
        
        mock_request.side_effect = [rate_limit_response, success_response]
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            with patch('fabric_api.time.sleep'):  # Speed up test
                client = FabricApiClient()
                response = client._make_request("workspaces")
                
                self.assertEqual(response.status_code, 200)
                self.assertEqual(mock_request.call_count, 2)
    
    @patch('fabric_api.requests.request')
    def test_make_request_max_retries_exceeded(self, mock_request):
        """Test max retries exceeded for rate limiting"""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'requestId': '12345', 'Retry-After': '1'}
        
        mock_request.return_value = rate_limit_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            with patch('fabric_api.time.sleep'):  # Speed up test
                client = FabricApiClient()
                with self.assertRaises(FabricApiError) as context:
                    client._make_request("workspaces", max_retries=2)
                
                self.assertIn("Maximum retries", str(context.exception))
    
    @patch('fabric_api.requests.request')
    def test_make_request_error_response(self, mock_request):
        """Test error response handling"""
        error_response = Mock()
        error_response.status_code = 404
        error_response.headers = {'requestId': '12345'}
        error_response.json.return_value = {"error": {"message": "Resource not found"}}
        mock_request.return_value = error_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client._make_request("workspaces/invalid-id")
            
            self.assertEqual(context.exception.status_code, 404)
    
    @patch('fabric_api.requests.request')
    def test_make_request_timeout(self, mock_request):
        """Test timeout handling"""
        mock_request.side_effect = requests.Timeout("Request timed out")
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client._make_request("workspaces")
            
            self.assertIn("timed out", str(context.exception))
    
    @patch('fabric_api.requests.request')
    def test_make_request_connection_error(self, mock_request):
        """Test connection error handling"""
        mock_request.side_effect = requests.ConnectionError("Connection failed")
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client._make_request("workspaces")
            
            self.assertIn("Connection error", str(context.exception))


class TestFabricApiClientWorkspaceOperations(unittest.TestCase):
    """Test cases for workspace operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
    
    @patch('fabric_api.requests.request')
    def test_get_workspaces(self, mock_request):
        """Test getting all workspaces"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "ws1", "displayName": "Workspace 1"},
                {"id": "ws2", "displayName": "Workspace 2"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            workspaces = client.get_workspaces()
            
            self.assertEqual(len(workspaces), 2)
            self.assertEqual(workspaces[0]["displayName"], "Workspace 1")
    
    @patch('fabric_api.requests.request')
    def test_get_workspace_by_name(self, mock_request):
        """Test getting workspace by name"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "ws1", "displayName": "Workspace 1"},
                {"id": "ws2", "displayName": "Workspace 2"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            workspace = client.get_workspace("Workspace 1")
            
            self.assertEqual(workspace["id"], "ws1")
            self.assertEqual(workspace["displayName"], "Workspace 1")
    
    @patch('fabric_api.requests.request')
    def test_get_workspace_case_insensitive(self, mock_request):
        """Test getting workspace by name is case insensitive"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "ws1", "displayName": "My Workspace"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            workspace = client.get_workspace("my workspace")
            
            self.assertEqual(workspace["id"], "ws1")
    
    @patch('fabric_api.requests.request')
    def test_get_workspace_not_found(self, mock_request):
        """Test getting workspace that doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {"value": []}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client.get_workspace("NonExistent")
            
            self.assertIn("not found", str(context.exception))
    
    @patch('fabric_api.requests.request')
    def test_create_workspace(self, mock_request):
        """Test creating a workspace"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {"id": "new-workspace-id"}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            workspace_id = client.create_workspace("New Workspace")
            
            self.assertEqual(workspace_id, "new-workspace-id")
    
    @patch('fabric_api.requests.request')
    def test_create_workspace_with_capacity(self, mock_request):
        """Test creating a workspace with capacity"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {"id": "new-workspace-id"}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            workspace_id = client.create_workspace("New Workspace", capacity_id="cap-id")
            
            self.assertEqual(workspace_id, "new-workspace-id")
            call_args = mock_request.call_args
            data = json.loads(call_args[1]['data'])
            self.assertEqual(data['capacityId'], 'cap-id')
    
    @patch('fabric_api.requests.request')
    def test_delete_workspace(self, mock_request):
        """Test deleting a workspace"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            # Should not raise
            client.delete_workspace("workspace-id")
            
            call_args = mock_request.call_args
            self.assertIn("workspaces/workspace-id", call_args[1]['url'])
            self.assertEqual(call_args[1]['method'], 'DELETE')


class TestFabricApiClientCapacityOperations(unittest.TestCase):
    """Test cases for capacity operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
    
    @patch('fabric_api.requests.request')
    def test_get_capacities(self, mock_request):
        """Test getting all capacities"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "cap1", "displayName": "Capacity 1", "sku": "F2", "state": "Active"},
                {"id": "cap2", "displayName": "Capacity 2", "sku": "F4", "state": "Paused"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            capacities = client.get_capacities()
            
            self.assertEqual(len(capacities), 2)
            self.assertEqual(capacities[0]["sku"], "F2")


class TestFabricApiClientRoleAssignments(unittest.TestCase):
    """Test cases for workspace role assignment operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
    
    @patch('fabric_api.requests.request')
    def test_add_workspace_role_assignment_user(self, mock_request):
        """Test adding a user role assignment"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "id": "assignment-id",
            "role": "Admin",
            "principal": {"id": "user-id", "type": "User"}
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            result = client.add_workspace_role_assignment(
                workspace_id="ws-id",
                principal_id="user-id",
                principal_type="User",
                role="Admin",
                display_name="Test User",
                user_principal_name="user@contoso.com"
            )
            
            self.assertEqual(result["role"], "Admin")
    
    def test_add_workspace_role_assignment_invalid_principal_type(self):
        """Test adding role assignment with invalid principal type"""
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client.add_workspace_role_assignment(
                    workspace_id="ws-id",
                    principal_id="user-id",
                    principal_type="InvalidType",
                    role="Admin"
                )
            
            self.assertIn("Invalid principal_type", str(context.exception))
    
    def test_add_workspace_role_assignment_invalid_role(self):
        """Test adding role assignment with invalid role"""
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client.add_workspace_role_assignment(
                    workspace_id="ws-id",
                    principal_id="user-id",
                    principal_type="User",
                    role="InvalidRole"
                )
            
            self.assertIn("Invalid role", str(context.exception))
    
    @patch('fabric_api.requests.request')
    def test_get_workspace_role_assignments(self, mock_request):
        """Test getting workspace role assignments"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "assign1", "role": "Admin", "principal": {"id": "user1", "type": "User"}},
                {"id": "assign2", "role": "Member", "principal": {"id": "user2", "type": "User"}}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            assignments = client.get_workspace_role_assignments("ws-id")
            
            self.assertEqual(len(assignments), 2)
            self.assertEqual(assignments[0]["role"], "Admin")


class TestFabricApiClientFolderOperations(unittest.TestCase):
    """Test cases for folder operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
    
    @patch('fabric_api.requests.request')
    def test_get_folders(self, mock_request):
        """Test getting folders in workspace"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "folder1", "displayName": "Folder 1"},
                {"id": "folder2", "displayName": "Folder 2", "parentFolderId": "folder1"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            folders = client.get_folders("ws-id")
            
            self.assertEqual(len(folders), 2)
            self.assertEqual(folders[0]["displayName"], "Folder 1")


class TestFabricApiClientNotebookMethods(unittest.TestCase):
    """Test cases for notebook-related methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.request')
    def test_get_notebooks(self, mock_request):
        """Test getting all notebooks from workspace"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "nb1", "displayName": "Notebook 1"},
                {"id": "nb2", "displayName": "Notebook 2"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            notebooks = client.get_notebooks("ws-id")
            
            self.assertEqual(len(notebooks), 2)
            self.assertEqual(notebooks["Notebook 1"], "nb1")
            self.assertEqual(notebooks["Notebook 2"], "nb2")

    @patch('fabric_api.requests.request')
    def test_get_notebooks_empty(self, mock_request):
        """Test getting notebooks when none exist"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {"value": []}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            notebooks = client.get_notebooks("ws-id")
            
            self.assertEqual(notebooks, {})


class TestFabricApiClientItemMethods(unittest.TestCase):
    """Test cases for item-related methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.request')
    def test_get_items(self, mock_request):
        """Test getting all items from workspace"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "item1", "displayName": "Item 1", "type": "Notebook"},
                {"id": "item2", "displayName": "Item 2", "type": "Lakehouse"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            items = client.get_items("ws-id")
            
            self.assertEqual(len(items), 2)

    @patch('fabric_api.requests.request')
    def test_get_items_with_type_filter(self, mock_request):
        """Test getting items with type filter"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "item1", "displayName": "Item 1", "type": "Notebook"},
                {"id": "item2", "displayName": "Item 2", "type": "Lakehouse"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            items = client.get_items("ws-id", item_type="Notebook")
            
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["type"], "Notebook")


class TestFabricApiClientLakehouseMethods(unittest.TestCase):
    """Test cases for lakehouse-related methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.request')
    def test_get_lakehouses(self, mock_request):
        """Test getting all lakehouses from workspace"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "lh1", "displayName": "Lakehouse 1"},
                {"id": "lh2", "displayName": "Lakehouse 2"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            lakehouses = client.get_lakehouses("ws-id")
            
            self.assertEqual(len(lakehouses), 2)


class TestFabricApiClientFolderCreation(unittest.TestCase):
    """Test cases for folder creation operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.request')
    def test_create_folder_success(self, mock_request):
        """Test creating a folder successfully"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "id": "folder-id",
            "displayName": "NewFolder"
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            result = client.create_folder("ws-id", "NewFolder")
            
            # create_folder returns just the ID
            self.assertEqual(result, "folder-id")

    @patch('fabric_api.requests.request')
    def test_create_folder_with_parent(self, mock_request):
        """Test creating a nested folder"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "id": "subfolder-id",
            "displayName": "SubFolder",
            "parentFolderId": "parent-folder-id"
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            result = client.create_folder("ws-id", "SubFolder", parent_folder_id="parent-folder-id")
            
            # create_folder returns just the ID
            self.assertEqual(result, "subfolder-id")


class TestFabricApiClientLROHandling(unittest.TestCase):
    """Test cases for Long Running Operation handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.get')
    @patch('fabric_api.requests.request')
    @patch('fabric_api.time.sleep')
    def test_make_request_202_with_lro(self, mock_sleep, mock_request, mock_get):
        """Test 202 response with LRO handling"""
        # Initial request returns 202 with Location
        mock_202_response = Mock()
        mock_202_response.status_code = 202
        mock_202_response.headers = {
            'requestId': '12345',
            'Location': 'https://api.fabric.microsoft.com/v1/operations/op-123'
        }
        mock_request.return_value = mock_202_response
        
        # LRO poll returns 200 (completed)
        mock_lro_response = Mock()
        mock_lro_response.status_code = 200
        mock_lro_response.json.return_value = {"status": "Completed"}
        mock_get.return_value = mock_lro_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            response = client._make_request("workspaces", method="POST", data={}, wait_for_lro=True)
            
            self.assertEqual(response.status_code, 200)

    @patch('fabric_api.requests.request')
    def test_make_request_202_without_lro_wait(self, mock_request):
        """Test 202 response without waiting for LRO"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {
            'requestId': '12345',
            'Location': 'https://api.fabric.microsoft.com/v1/operations/op-123'
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            response = client._make_request("workspaces", method="POST", data={}, wait_for_lro=False)
            
            self.assertEqual(response.status_code, 202)

    @patch('fabric_api.requests.request')
    def test_make_request_202_no_location_header(self, mock_request):
        """Test 202 response without Location header"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {'requestId': '12345'}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            response = client._make_request("workspaces", method="POST", data={}, wait_for_lro=True)
            
            # Returns the original 202 response when no location header (logs warning)
            self.assertEqual(response.status_code, 202)

    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_wait_for_lro_in_progress_then_complete(self, mock_sleep, mock_get):
        """Test LRO polling with in-progress then complete status"""
        # First call returns in-progress, second returns completed
        in_progress_response = Mock()
        in_progress_response.status_code = 200
        in_progress_response.json.return_value = {"status": "InProgress"}
        
        completed_response = Mock()
        completed_response.status_code = 200
        completed_response.json.return_value = {"status": "Completed"}
        
        mock_get.side_effect = [in_progress_response, completed_response]
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            response = client._wait_for_lro_completion(
                job_url="https://api.fabric.microsoft.com/v1/operations/op-123",
                operation_name="test-operation",
                max_wait_time=60,
                check_interval=1
            )
            
            self.assertEqual(response.json()["status"], "Completed")

    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_wait_for_lro_failed_status(self, mock_sleep, mock_get):
        """Test LRO polling with failed status"""
        failed_response = Mock()
        failed_response.status_code = 200
        failed_response.json.return_value = {"status": "Failed"}
        
        mock_get.return_value = failed_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            response = client._wait_for_lro_completion(
                job_url="https://api.fabric.microsoft.com/v1/operations/op-123",
                operation_name="test-operation",
                max_wait_time=60,
                check_interval=1
            )
            
            self.assertEqual(response.json()["status"], "Failed")

    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_wait_for_lro_timeout(self, mock_sleep, mock_get):
        """Test LRO polling timeout"""
        in_progress_response = Mock()
        in_progress_response.status_code = 202
        in_progress_response.headers = {'Retry-After': '1'}
        
        mock_get.return_value = in_progress_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client._wait_for_lro_completion(
                    job_url="https://api.fabric.microsoft.com/v1/operations/op-123",
                    operation_name="test-operation",
                    max_wait_time=1,  # Very short timeout
                    check_interval=1
                )
            
            self.assertIn("timed out", str(context.exception))

    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_wait_for_lro_error_status_code(self, mock_sleep, mock_get):
        """Test LRO polling with error status code"""
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        
        mock_get.return_value = error_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client._wait_for_lro_completion(
                    job_url="https://api.fabric.microsoft.com/v1/operations/op-123",
                    max_wait_time=60,
                    check_interval=1
                )
            
            self.assertIn("500", str(context.exception))

    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_wait_for_lro_request_exception(self, mock_sleep, mock_get):
        """Test LRO polling with request exception"""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client._wait_for_lro_completion(
                    job_url="https://api.fabric.microsoft.com/v1/operations/op-123",
                    max_wait_time=60,
                    check_interval=1
                )
            
            self.assertIn("Error checking", str(context.exception))


class TestFabricApiClientErrorHandling(unittest.TestCase):
    """Test cases for error handling scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.request')
    def test_make_request_error_with_json_error_field(self, mock_request):
        """Test error response with JSON error field"""
        error_response = Mock()
        error_response.status_code = 400
        error_response.headers = {'requestId': '12345'}
        error_response.json.return_value = {
            "error": {
                "code": "BadRequest",
                "message": "Invalid request parameters"
            }
        }
        mock_request.return_value = error_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client._make_request("workspaces")
            
            self.assertIn("Invalid request parameters", str(context.exception))

    @patch('fabric_api.requests.request')
    def test_make_request_error_with_invalid_json(self, mock_request):
        """Test error response with invalid JSON"""
        error_response = Mock()
        error_response.status_code = 500
        error_response.headers = {'requestId': '12345'}
        error_response.json.side_effect = ValueError("Invalid JSON")
        error_response.text = "Internal Server Error"
        mock_request.return_value = error_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client._make_request("workspaces")
            
            self.assertIn("Internal Server Error", str(context.exception))

    @patch('fabric_api.requests.request')
    def test_make_request_rate_limit_with_http_date(self, mock_request):
        """Test rate limiting with HTTP date retry-after header"""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'requestId': '12345', 'Retry-After': 'invalid-date'}
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {'requestId': '12346'}
        success_response.json.return_value = {"data": "success"}
        
        mock_request.side_effect = [rate_limit_response, success_response]
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            with patch('fabric_api.time.sleep'):
                client = FabricApiClient()
                response = client._make_request("workspaces")
                
                self.assertEqual(response.status_code, 200)

    @patch('fabric_api.requests.request')
    def test_make_request_general_request_exception(self, mock_request):
        """Test general request exception"""
        mock_request.side_effect = requests.RequestException("Unknown error")
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client._make_request("workspaces")
            
            self.assertIn("Request failed", str(context.exception))


class TestFabricApiClientLakehouseOperations(unittest.TestCase):
    """Test cases for lakehouse operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.request')
    def test_get_lakehouse(self, mock_request):
        """Test getting specific lakehouse by ID"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "id": "lh-123",
            "displayName": "MyLakehouse",
            "type": "Lakehouse"
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            lakehouse = client.get_lakehouse("ws-id", "lh-123")
            
            self.assertEqual(lakehouse["displayName"], "MyLakehouse")

    @patch('fabric_api.requests.request')
    def test_get_lakehouse_by_name(self, mock_request):
        """Test getting lakehouse by name"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "lh-1", "displayName": "Lakehouse1"},
                {"id": "lh-2", "displayName": "MyLakehouse"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            lakehouse = client.get_lakehouse_by_name("ws-id", "MyLakehouse")
            
            self.assertEqual(lakehouse["id"], "lh-2")

    @patch('fabric_api.requests.request')
    def test_get_lakehouse_by_name_case_insensitive(self, mock_request):
        """Test getting lakehouse by name is case insensitive"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "lh-1", "displayName": "MyLakehouse"}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            lakehouse = client.get_lakehouse_by_name("ws-id", "mylakehouse")
            
            self.assertEqual(lakehouse["id"], "lh-1")

    @patch('fabric_api.requests.request')
    def test_get_lakehouse_by_name_not_found(self, mock_request):
        """Test getting lakehouse by name when not found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {"value": []}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client.get_lakehouse_by_name("ws-id", "NonExistent")
            
            self.assertIn("not found", str(context.exception))

    @patch('fabric_api.requests.request')
    def test_create_lakehouse(self, mock_request):
        """Test creating a lakehouse"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "id": "new-lh-id",
            "displayName": "NewLakehouse",
            "type": "Lakehouse"
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            lakehouse = client.create_lakehouse("ws-id", "NewLakehouse")
            
            self.assertEqual(lakehouse["id"], "new-lh-id")

    @patch('fabric_api.requests.request')
    def test_create_lakehouse_with_options(self, mock_request):
        """Test creating lakehouse with description and folder"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "id": "new-lh-id",
            "displayName": "NewLakehouse",
            "description": "Test description"
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            lakehouse = client.create_lakehouse(
                "ws-id", 
                "NewLakehouse",
                description="Test description",
                folder_id="folder-123",
                enable_schemas=True
            )
            
            self.assertEqual(lakehouse["description"], "Test description")

    @patch('fabric_api.requests.request')
    def test_create_lakehouse_unexpected_status(self, mock_request):
        """Test creating lakehouse with unexpected status code"""
        mock_response = Mock()
        mock_response.status_code = 204  # Unexpected
        mock_response.headers = {'requestId': '12345'}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client.create_lakehouse("ws-id", "NewLakehouse")
            
            self.assertIn("Unexpected response status", str(context.exception))

    @patch('fabric_api.requests.request')
    def test_update_lakehouse(self, mock_request):
        """Test updating a lakehouse"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "id": "lh-123",
            "displayName": "UpdatedName"
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            lakehouse = client.update_lakehouse("ws-id", "lh-123", display_name="UpdatedName")
            
            self.assertEqual(lakehouse["displayName"], "UpdatedName")

    def test_update_lakehouse_no_params(self):
        """Test updating lakehouse without any parameters"""
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client.update_lakehouse("ws-id", "lh-123")
            
            self.assertIn("At least one property", str(context.exception))


class TestFabricApiClientNotebookOperations(unittest.TestCase):
    """Test cases for notebook create/update operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.request')
    def test_create_notebook(self, mock_request):
        """Test creating a notebook"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {"id": "nb-123"}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            response = client.create_notebook("ws-id", {"displayName": "NewNotebook"})
            
            self.assertEqual(response.status_code, 201)

    @patch('fabric_api.requests.request')
    def test_update_notebook(self, mock_request):
        """Test updating a notebook"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            response = client.update_notebook("ws-id", "nb-123", {"content": "updated"})
            
            self.assertEqual(response.status_code, 200)


class TestFabricApiClientScheduleNotebookJob(unittest.TestCase):
    """Test cases for schedule_notebook_job"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.request')
    def test_schedule_notebook_job_immediate_completion(self, mock_request):
        """Test notebook job that completes immediately (HTTP 200)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.content = b'{"status": "Completed"}'
        mock_response.json.return_value = {"status": "Completed"}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            result = client.schedule_notebook_job("ws-id", "nb-123")
            
            self.assertEqual(result["status"], "Completed")
            self.assertEqual(result["duration"], "0m 0s")

    @patch('fabric_api.requests.get')
    @patch('fabric_api.requests.request')
    @patch('fabric_api.time.sleep')
    def test_schedule_notebook_job_with_lro(self, mock_sleep, mock_request, mock_get):
        """Test notebook job with LRO (HTTP 202)"""
        # Initial request returns 202
        mock_202_response = Mock()
        mock_202_response.status_code = 202
        mock_202_response.headers = {
            'requestId': '12345',
            'location': 'https://api.fabric.microsoft.com/v1/operations/job-123'
        }
        mock_request.return_value = mock_202_response
        
        # LRO poll returns completed
        mock_lro_response = Mock()
        mock_lro_response.status_code = 200
        mock_lro_response.json.return_value = {"status": "Completed"}
        mock_get.return_value = mock_lro_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            result = client.schedule_notebook_job("ws-id", "nb-123")
            
            self.assertEqual(result["status"], "Completed")

    @patch('fabric_api.requests.request')
    def test_schedule_notebook_job_no_location_header(self, mock_request):
        """Test notebook job 202 without location header"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {'requestId': '12345'}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            result = client.schedule_notebook_job("ws-id", "nb-123")
            
            self.assertEqual(result["status"], "Failed")
            self.assertIn("No location header", result["error"])

    @patch('fabric_api.requests.request')
    def test_schedule_notebook_job_error_response(self, mock_request):
        """Test notebook job with error response"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'requestId': '12345'}
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {"error": {"message": "Bad Request"}}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            # The _make_request will raise FabricApiError for 400 status
            with self.assertRaises(FabricApiError):
                client.schedule_notebook_job("ws-id", "nb-123")

    @patch('fabric_api.requests.request')
    def test_schedule_notebook_job_unexpected_status(self, mock_request):
        """Test notebook job with unexpected status code (like 204)"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.headers = {'requestId': '12345'}
        mock_response.text = "No Content"
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            result = client.schedule_notebook_job("ws-id", "nb-123")
            
            self.assertEqual(result["status"], "Failed")
            self.assertIn("Unexpected", result["error"])

    @patch('fabric_api.requests.get')
    @patch('fabric_api.requests.request')
    @patch('fabric_api.time.sleep')
    def test_schedule_notebook_job_lro_timeout(self, mock_sleep, mock_request, mock_get):
        """Test notebook job LRO timeout"""
        # Initial request returns 202
        mock_202_response = Mock()
        mock_202_response.status_code = 202
        mock_202_response.headers = {
            'requestId': '12345',
            'location': 'https://api.fabric.microsoft.com/v1/operations/job-123'
        }
        mock_request.return_value = mock_202_response
        
        # LRO poll keeps returning 202 (never completes)
        mock_lro_response = Mock()
        mock_lro_response.status_code = 202
        mock_lro_response.headers = {'Retry-After': '1'}
        mock_get.return_value = mock_lro_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            with patch.object(FabricApiClient, '_wait_for_lro_completion', 
                            side_effect=FabricApiError("operation timed out")):
                client = FabricApiClient()
                result = client.schedule_notebook_job("ws-id", "nb-123")
                
                self.assertEqual(result["status"], "Timeout")

    @patch('fabric_api.requests.get')
    @patch('fabric_api.requests.request')
    @patch('fabric_api.time.sleep')
    def test_schedule_notebook_job_lro_failure(self, mock_sleep, mock_request, mock_get):
        """Test notebook job LRO failure"""
        # Initial request returns 202
        mock_202_response = Mock()
        mock_202_response.status_code = 202
        mock_202_response.headers = {
            'requestId': '12345',
            'location': 'https://api.fabric.microsoft.com/v1/operations/job-123'
        }
        mock_request.return_value = mock_202_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            with patch.object(FabricApiClient, '_wait_for_lro_completion', 
                            side_effect=FabricApiError("operation failed")):
                client = FabricApiClient()
                result = client.schedule_notebook_job("ws-id", "nb-123")
                
                self.assertEqual(result["status"], "Failed")

    @patch('fabric_api.requests.get')
    @patch('fabric_api.requests.request')
    @patch('fabric_api.time.sleep')
    def test_schedule_notebook_job_lro_non_200_response(self, mock_sleep, mock_request, mock_get):
        """Test notebook job LRO with non-200 final response"""
        # Initial request returns 202
        mock_202_response = Mock()
        mock_202_response.status_code = 202
        mock_202_response.headers = {
            'requestId': '12345',
            'location': 'https://api.fabric.microsoft.com/v1/operations/job-123'
        }
        mock_request.return_value = mock_202_response
        
        # LRO poll returns non-200
        mock_lro_response = Mock()
        mock_lro_response.status_code = 500
        mock_get.return_value = mock_lro_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            with patch.object(FabricApiClient, '_wait_for_lro_completion', return_value=mock_lro_response):
                client = FabricApiClient()
                result = client.schedule_notebook_job("ws-id", "nb-123")
                
                self.assertEqual(result["status"], "Failed")


class TestFabricApiClientCapacityAssignment(unittest.TestCase):
    """Test cases for capacity assignment operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.request')
    def test_assign_workspace_to_capacity(self, mock_request):
        """Test assigning workspace to capacity"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            # Should not raise
            client.assign_workspace_to_capacity("ws-id", "cap-id")

    @patch('fabric_api.requests.request')
    def test_assign_workspace_to_capacity_202(self, mock_request):
        """Test assigning workspace to capacity with 202 response"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {'requestId': '12345'}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            # Should not raise
            client.assign_workspace_to_capacity("ws-id", "cap-id")

    @patch('fabric_api.requests.request')
    def test_assign_workspace_to_capacity_failure(self, mock_request):
        """Test assigning workspace to capacity failure"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {"error": {"message": "Invalid capacity"}}
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError):
                client.assign_workspace_to_capacity("ws-id", "invalid-cap")


class TestFabricApiClientRoleAssignmentAdvanced(unittest.TestCase):
    """Advanced test cases for role assignment operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token

    @patch('fabric_api.requests.request')
    def test_add_service_principal_role_assignment(self, mock_request):
        """Test adding service principal role assignment"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "id": "assignment-id",
            "role": "Contributor",
            "principal": {"id": "sp-id", "type": "ServicePrincipal"}
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            result = client.add_workspace_role_assignment(
                workspace_id="ws-id",
                principal_id="sp-id",
                principal_type="ServicePrincipal",
                role="Contributor",
                aad_app_id="app-id"
            )
            
            self.assertEqual(result["role"], "Contributor")

    @patch('fabric_api.requests.request')
    def test_add_group_role_assignment(self, mock_request):
        """Test adding group role assignment"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "id": "assignment-id",
            "role": "Member",
            "principal": {"id": "group-id", "type": "Group"}
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            result = client.add_workspace_role_assignment(
                workspace_id="ws-id",
                principal_id="group-id",
                principal_type="Group",
                role="Member",
                group_type="SecurityGroup"
            )
            
            self.assertEqual(result["role"], "Member")

    def test_add_role_assignment_invalid_group_type(self):
        """Test adding role assignment with invalid group type"""
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError) as context:
                client.add_workspace_role_assignment(
                    workspace_id="ws-id",
                    principal_id="group-id",
                    principal_type="Group",
                    role="Member",
                    group_type="InvalidGroupType"
                )
            
            self.assertIn("Invalid group_type", str(context.exception))

    @patch('fabric_api.requests.request')
    def test_get_role_assignments_with_pagination(self, mock_request):
        """Test getting role assignments with pagination"""
        # First page response
        first_page = Mock()
        first_page.status_code = 200
        first_page.headers = {'requestId': '12345'}
        first_page.json.return_value = {
            "value": [{"id": "assign1", "role": "Admin"}],
            "continuationToken": "token123"
        }
        
        # Second page response
        second_page = Mock()
        second_page.status_code = 200
        second_page.headers = {'requestId': '12346'}
        second_page.json.return_value = {
            "value": [{"id": "assign2", "role": "Member"}]
        }
        
        mock_request.side_effect = [first_page, second_page]
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            assignments = client.get_workspace_role_assignments("ws-id", get_all=True)
            
            self.assertEqual(len(assignments), 2)

    @patch('fabric_api.requests.request')
    def test_get_role_assignments_pagination_failure(self, mock_request):
        """Test getting role assignments with pagination failure"""
        # First page response
        first_page = Mock()
        first_page.status_code = 200
        first_page.headers = {'requestId': '12345'}
        first_page.json.return_value = {
            "value": [{"id": "assign1", "role": "Admin"}],
            "continuationToken": "token123"
        }
        
        # Second page fails
        second_page = Mock()
        second_page.status_code = 500
        second_page.headers = {'requestId': '12346'}
        second_page.json.return_value = {"error": {"message": "Server error"}}
        
        mock_request.side_effect = [first_page, second_page]
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            with self.assertRaises(FabricApiError):
                client.get_workspace_role_assignments("ws-id", get_all=True)

    @patch('fabric_api.requests.request')
    def test_get_role_assignments_raw_response(self, mock_request):
        """Test getting role assignments without get_all"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [{"id": "assign1"}],
            "continuationToken": "token123"
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            response = client.get_workspace_role_assignments("ws-id", get_all=False)
            
            self.assertIn("continuationToken", response)

    @patch('fabric_api.requests.request')
    def test_get_role_assignment_by_principal_found(self, mock_request):
        """Test getting role assignment by principal when found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "assign1", "role": "Admin", "principal": {"id": "user1"}},
                {"id": "assign2", "role": "Member", "principal": {"id": "user2"}}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            assignment = client.get_workspace_role_assignment_by_principal("ws-id", "user2")
            
            self.assertEqual(assignment["role"], "Member")

    @patch('fabric_api.requests.request')
    def test_get_role_assignment_by_principal_not_found(self, mock_request):
        """Test getting role assignment by principal when not found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': '12345'}
        mock_response.json.return_value = {
            "value": [
                {"id": "assign1", "role": "Admin", "principal": {"id": "user1"}}
            ]
        }
        mock_request.return_value = mock_response
        
        with patch('fabric_api.AzureCliCredential', return_value=self.mock_credential):
            client = FabricApiClient()
            assignment = client.get_workspace_role_assignment_by_principal("ws-id", "nonexistent")
            
            self.assertIsNone(assignment)


class TestCreateFabricClientFunction(unittest.TestCase):
    """Test cases for create_fabric_client convenience function"""
    
    @patch('fabric_api.AzureCliCredential')
    def test_create_fabric_client_default(self, mock_credential):
        """Test creating fabric client with defaults"""
        from fabric_api import create_fabric_client
        
        client = create_fabric_client()
        
        self.assertIsInstance(client, FabricApiClient)

    def test_create_fabric_client_with_credential(self):
        """Test creating fabric client with custom credential"""
        from fabric_api import create_fabric_client
        
        mock_cred = Mock()
        
        with patch('fabric_api.AzureCliCredential'):
            client = create_fabric_client(credential=mock_cred)
            
            self.assertEqual(client._credential, mock_cred)


if __name__ == "__main__":
    unittest.main()
