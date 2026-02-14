"""
Unit tests for fabric_api.py

Tests for FabricApiClient and FabricWorkspaceApiClient classes.
"""

import json
import time
import unittest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import datetime

import requests

from fabric_api import (
    FabricApiClient, 
    FabricWorkspaceApiClient,
    FabricApiError,
    create_fabric_client,
    create_workspace_fabric_client
)


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
        """Test that _log outputs message"""
        with patch('builtins.print') as mock_print:
            self.client._log("Test message")
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            self.assertIn("Test message", call_args)
    
    def test_log_with_error_level(self):
        """Test _log with ERROR level includes icon"""
        with patch('builtins.print') as mock_print:
            self.client._log("Test error", level="ERROR")
            call_args = mock_print.call_args[0][0]
            self.assertIn("Test error", call_args)
    
    def test_log_with_warning_level(self):
        """Test _log with WARNING level includes icon"""
        with patch('builtins.print') as mock_print:
            self.client._log("Test warning", level="WARNING")
            call_args = mock_print.call_args[0][0]
            self.assertIn("Test warning", call_args)
    
    def test_format_duration_seconds_only(self):
        """Test _format_duration with seconds only"""
        result = self.client._format_duration(45)
        self.assertEqual(result, "0m 45s")
    
    def test_format_duration_minutes_and_seconds(self):
        """Test _format_duration with minutes and seconds"""
        result = self.client._format_duration(125)
        self.assertEqual(result, "2m 5s")
    
    def test_format_duration_exact_minutes(self):
        """Test _format_duration with exact minutes"""
        result = self.client._format_duration(180)
        self.assertEqual(result, "3m 0s")


class TestFabricApiClientAuthentication(unittest.TestCase):
    """Test cases for authentication"""
    
    @patch('fabric_api.AzureCliCredential')
    def test_get_auth_token_success(self, mock_credential_class):
        """Test successful authentication"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token_123"
        mock_token.expires_on = time.time() + 3600
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        client = FabricApiClient()
        token = client._get_auth_token()
        
        self.assertEqual(token, "test_token_123")
        mock_credential.get_token.assert_called_once()
    
    @patch('fabric_api.AzureCliCredential')
    def test_get_auth_token_failure(self, mock_credential_class):
        """Test authentication failure"""
        mock_credential = Mock()
        mock_credential.get_token.side_effect = Exception("Auth failed")
        mock_credential_class.return_value = mock_credential
        
        client = FabricApiClient()
        
        with self.assertRaises(FabricApiError) as context:
            client._get_auth_token()
        
        self.assertIn("Authentication failed", str(context.exception))
    
    @patch('fabric_api.AzureCliCredential')
    def test_get_auth_token_caching(self, mock_credential_class):
        """Test token caching"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "cached_token"
        mock_token.expires_on = time.time() + 3600
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        client = FabricApiClient()
        
        # First call
        token1 = client._get_auth_token()
        # Second call should use cache
        token2 = client._get_auth_token()
        
        self.assertEqual(token1, token2)
        # Should only call get_token once due to caching
        self.assertEqual(mock_credential.get_token.call_count, 1)


class TestFabricApiClientMakeRequest(unittest.TestCase):
    """Test cases for _make_request method"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch('fabric_api.requests.request')
    def test_make_request_success(self, mock_request):
        """Test successful request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': 'test-id'}
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response
        
        response = self.client._make_request("test/endpoint")
        
        self.assertEqual(response.status_code, 200)
        mock_request.assert_called_once()
    
    @patch('fabric_api.requests.request')
    def test_make_request_with_data(self, mock_request):
        """Test request with data"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {'requestId': 'test-id'}
        mock_response.json.return_value = {"id": "new-item"}
        mock_request.return_value = mock_response
        
        response = self.client._make_request(
            "test/endpoint", 
            method="POST", 
            data={"name": "test"}
        )
        
        self.assertEqual(response.status_code, 201)
        call_args = mock_request.call_args
        self.assertEqual(call_args.kwargs['method'], "POST")
    
    @patch('fabric_api.requests.request')
    def test_make_request_error(self, mock_request):
        """Test request with error response"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {'requestId': 'test-id'}
        mock_response.json.return_value = {"error": {"message": "Bad request"}}
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError) as context:
            self.client._make_request("test/endpoint")
        
        self.assertIn("400", str(context.exception))
    
    @patch('fabric_api.requests.request')
    def test_make_request_timeout(self, mock_request):
        """Test request timeout"""
        mock_request.side_effect = requests.Timeout("Connection timed out")
        
        with self.assertRaises(FabricApiError) as context:
            self.client._make_request("test/endpoint")
        
        self.assertIn("timed out", str(context.exception))
    
    @patch('fabric_api.requests.request')
    def test_make_request_connection_error(self, mock_request):
        """Test connection error"""
        mock_request.side_effect = requests.ConnectionError("Connection refused")
        
        with self.assertRaises(FabricApiError) as context:
            self.client._make_request("test/endpoint")
        
        self.assertIn("Connection error", str(context.exception))
    
    @patch('builtins.print')
    @patch('fabric_api.requests.request')
    @patch('fabric_api.time.sleep')
    def test_make_request_rate_limiting(self, mock_sleep, mock_request, mock_print):
        """Test rate limiting handling"""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {'Retry-After': '5', 'requestId': 'test-id'}
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.headers = {'requestId': 'test-id'}
        mock_response_200.json.return_value = {"data": "success"}
        
        mock_request.side_effect = [mock_response_429, mock_response_200]
        
        response = self.client._make_request("test/endpoint")
        
        self.assertEqual(response.status_code, 200)
        mock_sleep.assert_called()


class TestFabricApiClientLRO(unittest.TestCase):
    """Test cases for Long Running Operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_wait_for_lro_completion_success(self, mock_sleep, mock_get):
        """Test LRO completion success"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "Completed", "result": "success"}
        mock_get.return_value = mock_response
        
        response = self.client._wait_for_lro_completion(
            "https://api.fabric.microsoft.com/v1/operations/123",
            operation_name="test operation"
        )
        
        self.assertEqual(response.status_code, 200)
    
    @patch('builtins.print')
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_wait_for_lro_failure(self, mock_sleep, mock_get, mock_print):
        """Test LRO failure"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "Failed", 
            "failureReason": {"message": "Operation failed", "errorCode": "ERR001"}
        }
        mock_get.return_value = mock_response
        
        with self.assertRaises(FabricApiError) as context:
            self.client._wait_for_lro_completion(
                "https://api.fabric.microsoft.com/v1/operations/123",
                operation_name="test operation"
            )
        
        self.assertIn("Failed", str(context.exception))


class TestFabricApiClientCapacities(unittest.TestCase):
    """Test cases for capacity operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_list_capacities_success(self, mock_request):
        """Test listing capacities"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {"id": "cap-1", "displayName": "Capacity1", "sku": "F2"},
                {"id": "cap-2", "displayName": "Capacity2", "sku": "F4"}
            ]
        }
        mock_request.return_value = mock_response
        
        capacities = self.client.list_capacities()
        
        self.assertEqual(len(capacities), 2)
        self.assertEqual(capacities[0]['displayName'], "Capacity1")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_get_capacity_found(self, mock_request):
        """Test getting a capacity by name"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {"id": "cap-1", "displayName": "Capacity1", "sku": "F2"},
                {"id": "cap-2", "displayName": "Capacity2", "sku": "F4"}
            ]
        }
        mock_request.return_value = mock_response
        
        capacity = self.client.get_capacity("Capacity2")
        
        self.assertIsNotNone(capacity)
        self.assertEqual(capacity['id'], "cap-2")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_get_capacity_not_found(self, mock_request):
        """Test getting a capacity that doesn't exist"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {"id": "cap-1", "displayName": "Capacity1", "sku": "F2"}
            ]
        }
        mock_request.return_value = mock_response
        
        capacity = self.client.get_capacity("NonexistentCapacity")
        
        self.assertIsNone(capacity)


class TestFabricApiClientWorkspaces(unittest.TestCase):
    """Test cases for workspace operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_list_workspaces_success(self, mock_request):
        """Test listing workspaces"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "ws-1", "displayName": "Workspace1"},
                {"id": "ws-2", "displayName": "Workspace2"}
            ]
        }
        mock_request.return_value = mock_response
        
        workspaces = self.client.list_workspaces()
        
        self.assertEqual(len(workspaces), 2)
    
    @patch.object(FabricApiClient, '_make_request')
    def test_get_workspace_found(self, mock_request):
        """Test getting a workspace by name"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "ws-1", "displayName": "Workspace1"},
                {"id": "ws-2", "displayName": "Workspace2"}
            ]
        }
        mock_request.return_value = mock_response
        
        workspace = self.client.get_workspace("Workspace1")
        
        self.assertIsNotNone(workspace)
        self.assertEqual(workspace['id'], "ws-1")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_create_workspace_success(self, mock_request):
        """Test creating a workspace"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "new-ws-id"}
        mock_request.return_value = mock_response
        
        ws_id = self.client.create_workspace("NewWorkspace")
        
        self.assertEqual(ws_id, "new-ws-id")
        mock_request.assert_called_once()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_create_workspace_with_capacity(self, mock_request):
        """Test creating a workspace with capacity"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "new-ws-id"}
        mock_request.return_value = mock_response
        
        ws_id = self.client.create_workspace("NewWorkspace", capacity_id="cap-123")
        
        self.assertEqual(ws_id, "new-ws-id")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_assign_workspace_to_capacity_success(self, mock_request):
        """Test assigning workspace to capacity"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        # Should not raise
        self.client.assign_workspace_to_capacity("ws-123", "cap-456")
        mock_request.assert_called_once()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_workspace_success(self, mock_request):
        """Test deleting a workspace"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        result = self.client.delete_workspace("ws-123")
        
        self.assertEqual(result, "ws-123")


class TestFabricApiClientConnections(unittest.TestCase):
    """Test cases for connection operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_create_eventhub_connection_success(self, mock_request):
        """Test creating Event Hub connection"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "conn-123", "displayName": "TestConnection"}
        mock_request.return_value = mock_response
        
        connection = self.client.create_eventhub_connection(
            name="TestConnection",
            namespace_name="test-namespace",
            event_hub_name="test-hub",
            shared_access_policy_name="policy",
            shared_access_key="key123"
        )
        
        self.assertEqual(connection['id'], "conn-123")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_list_connections_success(self, mock_request):
        """Test listing connections"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "conn-1", "displayName": "Connection1"},
                {"id": "conn-2", "displayName": "Connection2"}
            ]
        }
        mock_request.return_value = mock_response
        
        connections = self.client.list_connections()
        
        self.assertEqual(len(connections), 2)
    
    @patch.object(FabricApiClient, '_make_request')
    def test_get_connection_success(self, mock_request):
        """Test getting a connection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "conn-123", "displayName": "TestConnection"}
        mock_request.return_value = mock_response
        
        connection = self.client.get_connection("conn-123")
        
        self.assertEqual(connection['displayName'], "TestConnection")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_connection_success(self, mock_request):
        """Test deleting a connection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        result = self.client.delete_connection("conn-123")
        
        self.assertEqual(result, "conn-123")


class TestFabricApiClientHeaders(unittest.TestCase):
    """Test cases for get_headers method"""
    
    @patch('fabric_api.AzureCliCredential')
    def test_get_headers(self, mock_credential_class):
        """Test get_headers returns auth header"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token_abc"
        mock_token.expires_on = time.time() + 3600
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        client = FabricApiClient()
        headers = client.get_headers()
        
        self.assertIn("Authorization", headers)
        self.assertEqual(headers["Authorization"], "Bearer test_token_abc")


class TestFabricApiClientFileSystemClient(unittest.TestCase):
    """Test cases for file system client"""
    
    @patch('fabric_api.DataLakeServiceClient')
    @patch('fabric_api.AzureCliCredential')
    def test_get_workspace_file_system_client(self, mock_credential_class, mock_datalake_class):
        """Test getting file system client"""
        mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        mock_service_client = Mock()
        mock_fs_client = Mock()
        mock_service_client.get_file_system_client.return_value = mock_fs_client
        mock_datalake_class.return_value = mock_service_client
        
        client = FabricApiClient()
        fs_client = client.get_workspace_file_system_client("TestWorkspace")
        
        self.assertEqual(fs_client, mock_fs_client)
        mock_service_client.get_file_system_client.assert_called_with(file_system="TestWorkspace")


class TestFabricWorkspaceApiClientInit(unittest.TestCase):
    """Test cases for FabricWorkspaceApiClient initialization"""
    
    @patch('fabric_api.AzureCliCredential')
    def test_initialization(self, mock_credential_class):
        """Test workspace client initialization"""
        mock_credential = Mock()
        mock_credential_class.return_value = mock_credential
        
        client = FabricWorkspaceApiClient(workspace_id="ws-123")
        
        self.assertEqual(client.workspace_id, "ws-123")
        self.assertIsNone(client._workspace_info)
    
    @patch('fabric_api.AzureCliCredential')
    def test_initialization_with_custom_params(self, mock_credential_class):
        """Test workspace client initialization with custom params"""
        custom_cred = Mock()
        
        client = FabricWorkspaceApiClient(
            workspace_id="ws-123",
            api_url="https://custom.api.com",
            credential=custom_cred,
            timeout_sec=120
        )
        
        self.assertEqual(client.workspace_id, "ws-123")
        self.assertEqual(client.timeout_sec, 120)
        self.assertEqual(client._credential, custom_cred)


class TestFabricWorkspaceApiClientWorkspaceInfo(unittest.TestCase):
    """Test cases for workspace info operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_get_workspace_info_success(self, mock_request):
        """Test getting workspace info"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "ws-123",
            "displayName": "TestWorkspace",
            "capacityId": "cap-456"
        }
        mock_request.return_value = mock_response
        
        info = self.client.get_workspace_info()
        
        self.assertEqual(info['displayName'], "TestWorkspace")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_get_workspace_info_caching(self, mock_request):
        """Test workspace info caching"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "ws-123",
            "displayName": "TestWorkspace"
        }
        mock_request.return_value = mock_response
        
        # First call
        self.client.get_workspace_info()
        # Second call should use cache
        self.client.get_workspace_info()
        
        # Should only call API once
        self.assertEqual(mock_request.call_count, 1)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_get_workspace_info_refresh(self, mock_request):
        """Test workspace info with refresh"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "ws-123",
            "displayName": "TestWorkspace"
        }
        mock_request.return_value = mock_response
        
        # First call
        self.client.get_workspace_info()
        # Second call with refresh
        self.client.get_workspace_info(refresh=True)
        
        # Should call API twice
        self.assertEqual(mock_request.call_count, 2)


class TestFabricWorkspaceApiClientFolders(unittest.TestCase):
    """Test cases for folder operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_folders_success(self, mock_request):
        """Test listing folders"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "folder-1", "displayName": "Folder1"},
                {"id": "folder-2", "displayName": "Folder2"}
            ]
        }
        mock_request.return_value = mock_response
        
        folders = self.client.list_folders()
        
        self.assertEqual(len(folders), 2)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_folder_success(self, mock_request):
        """Test creating a folder"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "new-folder-id"}
        mock_request.return_value = mock_response
        
        folder_id = self.client.create_folder("NewFolder")
        
        self.assertEqual(folder_id, "new-folder-id")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_folder_with_parent(self, mock_request):
        """Test creating a folder with parent"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "new-folder-id"}
        mock_request.return_value = mock_response
        
        folder_id = self.client.create_folder("NewFolder", parent_folder_id="parent-123")
        
        self.assertEqual(folder_id, "new-folder-id")


class TestFabricWorkspaceApiClientNotebooks(unittest.TestCase):
    """Test cases for notebook operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_notebooks_success(self, mock_request):
        """Test listing notebooks"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "nb-1", "displayName": "Notebook1"},
                {"id": "nb-2", "displayName": "Notebook2"}
            ]
        }
        mock_request.return_value = mock_response
        
        notebooks = self.client.list_notebooks()
        
        self.assertEqual(len(notebooks), 2)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_get_notebook_success(self, mock_request):
        """Test getting a notebook"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "nb-123",
            "displayName": "TestNotebook",
            "type": "Notebook"
        }
        mock_request.return_value = mock_response
        
        notebook = self.client.get_notebook("nb-123")
        
        self.assertEqual(notebook['displayName'], "TestNotebook")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_notebook_success(self, mock_request):
        """Test creating a notebook"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": "new-nb-id"}'
        mock_response.json.return_value = {"id": "new-nb-id"}
        mock_request.return_value = mock_response
        
        result = self.client.create_notebook(
            notebook_name="NewNotebook",
            notebook_data_base64="base64content"
        )
        
        self.assertEqual(result['id'], "new-nb-id")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_update_notebook_success(self, mock_request):
        """Test updating a notebook"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response
        
        result = self.client.update_notebook(
            notebook_id="nb-123",
            notebook_data_base64="updated_base64content"
        )
        
        self.assertIsNotNone(result)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_get_notebook_by_name_found(self, mock_request):
        """Test getting notebook by name when found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "nb-1", "displayName": "Notebook1"},
                {"id": "nb-2", "displayName": "Notebook2"}
            ]
        }
        mock_request.return_value = mock_response
        
        notebook = self.client.get_notebook_by_name("Notebook2")
        
        self.assertIsNotNone(notebook)
        self.assertEqual(notebook['id'], "nb-2")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_get_notebook_by_name_not_found(self, mock_request):
        """Test getting notebook by name when not found"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "nb-1", "displayName": "Notebook1"}
            ]
        }
        mock_request.return_value = mock_response
        
        notebook = self.client.get_notebook_by_name("NonexistentNotebook")
        
        self.assertIsNone(notebook)


class TestFabricWorkspaceApiClientLakehouses(unittest.TestCase):
    """Test cases for lakehouse operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_lakehouses_success(self, mock_request):
        """Test listing lakehouses"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {"id": "lh-1", "displayName": "Lakehouse1"},
                {"id": "lh-2", "displayName": "Lakehouse2"}
            ]
        }
        mock_request.return_value = mock_response
        
        lakehouses = self.client.list_lakehouses()
        
        self.assertEqual(len(lakehouses), 2)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_get_lakehouse_success(self, mock_request):
        """Test getting a lakehouse"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "lh-123",
            "displayName": "TestLakehouse"
        }
        mock_request.return_value = mock_response
        
        lakehouse = self.client.get_lakehouse("lh-123")
        
        self.assertEqual(lakehouse['displayName'], "TestLakehouse")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_get_lakehouse_by_name_found(self, mock_request):
        """Test getting lakehouse by name"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {"id": "lh-1", "displayName": "Lakehouse1"},
                {"id": "lh-2", "displayName": "Lakehouse2"}
            ]
        }
        mock_request.return_value = mock_response
        
        lakehouse = self.client.get_lakehouse_by_name("Lakehouse2")
        
        self.assertEqual(lakehouse['id'], "lh-2")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_get_lakehouse_by_name_not_found(self, mock_request):
        """Test getting lakehouse by name when not found"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {"id": "lh-1", "displayName": "Lakehouse1"}
            ]
        }
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.get_lakehouse_by_name("NonexistentLakehouse")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_lakehouse_success(self, mock_request):
        """Test creating a lakehouse"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "new-lh-id", "displayName": "NewLakehouse"}
        mock_request.return_value = mock_response
        
        lakehouse = self.client.create_lakehouse("NewLakehouse")
        
        self.assertEqual(lakehouse['id'], "new-lh-id")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_update_lakehouse_success(self, mock_request):
        """Test updating a lakehouse"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "lh-123", "displayName": "UpdatedLakehouse"}
        mock_request.return_value = mock_response
        
        lakehouse = self.client.update_lakehouse("lh-123", display_name="UpdatedLakehouse")
        
        self.assertEqual(lakehouse['displayName'], "UpdatedLakehouse")
    
    def test_update_lakehouse_no_params(self):
        """Test updating lakehouse with no params raises error"""
        with self.assertRaises(FabricApiError):
            self.client.update_lakehouse("lh-123")


class TestFabricWorkspaceApiClientNotebookJobs(unittest.TestCase):
    """Test cases for notebook job operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    @patch.object(FabricWorkspaceApiClient, 'get_notebook')
    def test_schedule_notebook_job_immediate_success(self, mock_get_notebook, mock_request):
        """Test scheduling notebook job with immediate completion"""
        mock_get_notebook.return_value = {
            "id": "nb-123",
            "displayName": "TestNotebook"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response
        
        result = self.client.schedule_notebook_job("nb-123")
        
        self.assertEqual(result['status'], 'Completed')
    
    @patch.object(FabricWorkspaceApiClient, 'get_notebook')
    def test_schedule_notebook_job_not_found(self, mock_get_notebook):
        """Test scheduling job for non-existent notebook"""
        mock_get_notebook.return_value = None
        
        with self.assertRaises(FabricApiError):
            self.client.schedule_notebook_job("nb-nonexistent")


class TestFabricWorkspaceApiClientDataAgents(unittest.TestCase):
    """Test cases for data agent operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_data_agent_success(self, mock_request):
        """Test creating a data agent"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "agent-123", "displayName": "TestAgent"}
        mock_request.return_value = mock_response
        
        agent = self.client.create_data_agent("TestAgent")
        
        self.assertEqual(agent['id'], "agent-123")
    
    def test_create_data_agent_empty_name(self):
        """Test creating data agent with empty name raises error"""
        with self.assertRaises(FabricApiError):
            self.client.create_data_agent("")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_data_agents_success(self, mock_request):
        """Test listing data agents"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "agent-1", "displayName": "Agent1"},
                {"id": "agent-2", "displayName": "Agent2"}
            ]
        }
        mock_request.return_value = mock_response
        
        agents = self.client.list_data_agents()
        
        self.assertEqual(len(agents), 2)
    
    @patch.object(FabricWorkspaceApiClient, 'list_data_agents')
    def test_get_data_agent_by_name_found(self, mock_list):
        """Test getting data agent by name"""
        mock_list.return_value = [
            {"id": "agent-1", "displayName": "Agent1"},
            {"id": "agent-2", "displayName": "Agent2"}
        ]
        
        agent = self.client.get_data_agent_by_name("Agent2")
        
        self.assertEqual(agent['id'], "agent-2")
    
    @patch.object(FabricWorkspaceApiClient, 'list_data_agents')
    def test_get_data_agent_by_name_not_found(self, mock_list):
        """Test getting data agent by name when not found"""
        mock_list.return_value = [
            {"id": "agent-1", "displayName": "Agent1"}
        ]
        
        agent = self.client.get_data_agent_by_name("NonexistentAgent")
        
        self.assertIsNone(agent)


class TestFabricWorkspaceApiClientEnvironments(unittest.TestCase):
    """Test cases for environment operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_environment_success(self, mock_request):
        """Test creating an environment"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "env-123", "displayName": "TestEnv"}
        mock_request.return_value = mock_response
        
        env = self.client.create_environment("TestEnv")
        
        self.assertEqual(env['id'], "env-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_environments_success(self, mock_request):
        """Test listing environments"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "env-1", "displayName": "Env1"},
                {"id": "env-2", "displayName": "Env2"}
            ]
        }
        mock_request.return_value = mock_response
        
        envs = self.client.list_environments()
        
        self.assertEqual(len(envs), 2)
    
    @patch.object(FabricWorkspaceApiClient, 'list_environments')
    def test_get_environment_by_name_found(self, mock_list):
        """Test getting environment by name"""
        mock_list.return_value = [
            {"id": "env-1", "displayName": "Env1"},
            {"id": "env-2", "displayName": "Env2"}
        ]
        
        env = self.client.get_environment_by_name("Env2")
        
        self.assertEqual(env['id'], "env-2")
    
    @patch.object(FabricWorkspaceApiClient, 'list_environments')
    def test_get_environment_by_name_not_found(self, mock_list):
        """Test getting environment by name when not found"""
        mock_list.return_value = [
            {"id": "env-1", "displayName": "Env1"}
        ]
        
        env = self.client.get_environment_by_name("NonexistentEnv")
        
        self.assertIsNone(env)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_delete_environment_success(self, mock_request):
        """Test deleting an environment"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        result = self.client.delete_environment("env-123")
        
        self.assertTrue(result)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_publish_environment_success(self, mock_request):
        """Test publishing an environment"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "Published"}
        mock_request.return_value = mock_response
        
        result = self.client.publish_environment("env-123")
        
        self.assertIsNotNone(result)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_update_environment_definition_success(self, mock_request):
        """Test updating environment definition"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        result = self.client.update_environment_definition(
            "env-123",
            environment_yml_base64="base64content"
        )
        
        self.assertTrue(result)
    
    @patch('builtins.print')
    def test_update_environment_definition_no_parts(self, mock_print):
        """Test updating environment definition with no parts"""
        result = self.client.update_environment_definition("env-123")
        
        self.assertFalse(result)


class TestFabricWorkspaceApiClientRoleAssignments(unittest.TestCase):
    """Test cases for role assignment operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_add_role_assignment_success(self, mock_request):
        """Test adding a role assignment"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "ra-123",
            "principal": {"id": "user-456", "type": "User"},
            "role": "Member"
        }
        mock_request.return_value = mock_response
        
        assignment = self.client.add_role_assignment(
            principal_id="user-456",
            principal_type="User",
            role="Member"
        )
        
        self.assertEqual(assignment['id'], "ra-123")
    
    def test_add_role_assignment_invalid_principal_type(self):
        """Test adding role assignment with invalid principal type"""
        with self.assertRaises(FabricApiError):
            self.client.add_role_assignment(
                principal_id="user-456",
                principal_type="InvalidType",
                role="Member"
            )
    
    def test_add_role_assignment_invalid_role(self):
        """Test adding role assignment with invalid role"""
        with self.assertRaises(FabricApiError):
            self.client.add_role_assignment(
                principal_id="user-456",
                principal_type="User",
                role="InvalidRole"
            )
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_role_assignments_success(self, mock_request):
        """Test listing role assignments"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": "ra-1", "principal": {"id": "user-1"}, "role": "Admin"},
                {"id": "ra-2", "principal": {"id": "user-2"}, "role": "Member"}
            ]
        }
        mock_request.return_value = mock_response
        
        assignments = self.client.list_role_assignments()
        
        self.assertEqual(len(assignments), 2)
    
    @patch.object(FabricWorkspaceApiClient, 'list_role_assignments')
    def test_get_role_assignment_by_principal_found(self, mock_list):
        """Test getting role assignment by principal"""
        mock_list.return_value = [
            {"id": "ra-1", "principal": {"id": "user-1"}, "role": "Admin"},
            {"id": "ra-2", "principal": {"id": "user-2"}, "role": "Member"}
        ]
        
        assignment = self.client.get_role_assignment_by_principal("user-2")
        
        self.assertEqual(assignment['role'], "Member")
    
    @patch.object(FabricWorkspaceApiClient, 'list_role_assignments')
    def test_get_role_assignment_by_principal_not_found(self, mock_list):
        """Test getting role assignment by principal when not found"""
        mock_list.return_value = [
            {"id": "ra-1", "principal": {"id": "user-1"}, "role": "Admin"}
        ]
        
        assignment = self.client.get_role_assignment_by_principal("nonexistent-user")
        
        self.assertIsNone(assignment)


class TestFabricWorkspaceApiClientItems(unittest.TestCase):
    """Test cases for item operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_items_success(self, mock_request):
        """Test listing items"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {"id": "item-1", "type": "Notebook"},
                {"id": "item-2", "type": "Lakehouse"}
            ]
        }
        mock_request.return_value = mock_response
        
        items = self.client.list_items()
        
        self.assertEqual(len(items), 2)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_items_with_type_filter(self, mock_request):
        """Test listing items with type filter"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "value": [
                {"id": "item-1", "type": "Notebook"},
                {"id": "item-2", "type": "Lakehouse"},
                {"id": "item-3", "type": "Notebook"}
            ]
        }
        mock_request.return_value = mock_response
        
        items = self.client.list_items(item_type="Notebook")
        
        self.assertEqual(len(items), 2)


class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions"""
    
    @patch('fabric_api.AzureCliCredential')
    def test_create_fabric_client(self, mock_credential):
        """Test create_fabric_client function"""
        client = create_fabric_client()
        
        self.assertIsInstance(client, FabricApiClient)
    
    @patch('fabric_api.AzureCliCredential')
    def test_create_fabric_client_with_credential(self, mock_credential):
        """Test create_fabric_client with custom credential"""
        custom_cred = Mock()
        
        client = create_fabric_client(credential=custom_cred)
        
        self.assertEqual(client._credential, custom_cred)
    
    @patch('fabric_api.AzureCliCredential')
    def test_create_workspace_fabric_client(self, mock_credential):
        """Test create_workspace_fabric_client function"""
        client = create_workspace_fabric_client("ws-123")
        
        self.assertIsInstance(client, FabricWorkspaceApiClient)
        self.assertEqual(client.workspace_id, "ws-123")


class TestFabricApiClientLROWithPolling(unittest.TestCase):
    """Test cases for LRO with polling"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_lro_with_in_progress_then_complete(self, mock_sleep, mock_get):
        """Test LRO that shows in-progress then completes"""
        response_in_progress = Mock()
        response_in_progress.status_code = 200
        response_in_progress.json.return_value = {"status": "InProgress"}
        
        response_complete = Mock()
        response_complete.status_code = 200
        response_complete.json.return_value = {"status": "Completed", "result": "success"}
        
        mock_get.side_effect = [response_in_progress, response_complete]
        
        result = self.client._wait_for_lro_completion(
            "https://api.fabric.microsoft.com/operations/123",
            operation_name="test"
        )
        
        self.assertEqual(result.status_code, 200)
    
    @patch('builtins.print')
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_lro_with_cancelled_status(self, mock_sleep, mock_get, mock_print):
        """Test LRO that gets cancelled"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "Cancelled",
            "failureReason": {"message": "User cancelled", "errorCode": "CANCELLED"}
        }
        mock_get.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client._wait_for_lro_completion(
                "https://api.fabric.microsoft.com/operations/123",
                operation_name="test"
            )


class TestFabricApiClientStartLRO(unittest.TestCase):
    """Test cases for starting LROs"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch('fabric_api.requests.request')
    def test_start_long_running_operation(self, mock_request):
        """Test starting an LRO without waiting"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {
            'Location': 'https://api.fabric.microsoft.com/operations/123',
            'requestId': 'test-id'
        }
        mock_request.return_value = mock_response
        
        response = self.client.start_long_running_operation("test/endpoint", method="POST")
        
        self.assertEqual(response.status_code, 202)


class TestFabricApiClientCheckLROStatus(unittest.TestCase):
    """Test cases for checking LRO status"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch('fabric_api.requests.get')
    def test_check_lro_job_status_completed(self, mock_get):
        """Test checking LRO job status when completed"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "Completed", "result": "success"}
        mock_get.return_value = mock_response
        
        result = self.client.check_lro_job_status("https://api.fabric.microsoft.com/operations/123")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], "Completed")
    
    @patch('fabric_api.requests.get')
    def test_check_lro_job_status_in_progress(self, mock_get):
        """Test checking LRO job status when in progress"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_get.return_value = mock_response
        
        result = self.client.check_lro_job_status("https://api.fabric.microsoft.com/operations/123")
        
        self.assertIsNone(result)
    
    @patch('fabric_api.requests.get')
    def test_check_lro_job_status_error(self, mock_get):
        """Test checking LRO job status on error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_get.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.check_lro_job_status("https://api.fabric.microsoft.com/operations/123")
    
    @patch('fabric_api.requests.get')
    def test_check_lro_job_status_request_error(self, mock_get):
        """Test checking LRO job status with request error"""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        with self.assertRaises(FabricApiError):
            self.client.check_lro_job_status("https://api.fabric.microsoft.com/operations/123")


class TestFabricApiClientMakeRequestAdvanced(unittest.TestCase):
    """Additional test cases for _make_request method edge cases"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch('fabric_api.requests.request')
    def test_make_request_with_string_data(self, mock_request):
        """Test request with string data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': 'test-id'}
        mock_request.return_value = mock_response
        
        response = self.client._make_request("test/endpoint", method="POST", data='{"test": "data"}')
        
        self.assertEqual(response.status_code, 200)
    
    @patch('fabric_api.requests.request')
    def test_make_request_with_custom_headers(self, mock_request):
        """Test request with custom headers"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'requestId': 'test-id'}
        mock_request.return_value = mock_response
        
        response = self.client._make_request("test/endpoint", headers={"Custom-Header": "value"})
        
        self.assertEqual(response.status_code, 200)
    
    @patch('fabric_api.requests.request')
    def test_make_request_request_exception(self, mock_request):
        """Test request with general request exception"""
        mock_request.side_effect = requests.RequestException("General error")
        
        with self.assertRaises(FabricApiError) as context:
            self.client._make_request("test/endpoint")
        
        self.assertIn("Request failed", str(context.exception))
    
    @patch('fabric_api.requests.request')
    def test_make_request_error_without_json(self, mock_request):
        """Test request with error response that has no JSON"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {'requestId': 'test-id'}
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError) as context:
            self.client._make_request("test/endpoint")
        
        self.assertIn("500", str(context.exception))
    
    @patch('builtins.print')
    @patch('fabric_api.requests.request')
    @patch('fabric_api.time.sleep')
    def test_make_request_rate_limiting_max_retries(self, mock_sleep, mock_request, mock_print):
        """Test rate limiting exceeds max retries"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '1', 'requestId': 'test-id'}
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError) as context:
            self.client._make_request("test/endpoint", max_retries=2)
        
        self.assertIn("Maximum retries", str(context.exception))
    
    @patch('fabric_api.requests.request')
    def test_make_request_202_with_lro(self, mock_request):
        """Test 202 response triggering LRO handling"""
        mock_response_202 = Mock()
        mock_response_202.status_code = 202
        mock_response_202.headers = {'Location': 'https://api.fabric.microsoft.com/operations/123', 'requestId': 'test-id'}
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"status": "Completed"}
        
        # First call returns 202, then polling returns 200
        mock_request.return_value = mock_response_202
        
        with patch('fabric_api.requests.get') as mock_get:
            mock_get.return_value = mock_response_200
            with patch('fabric_api.time.sleep'):
                response = self.client._make_request("test/endpoint", wait_for_lro=True)
        
        self.assertEqual(response.status_code, 200)


class TestFabricApiClientLROAdvanced(unittest.TestCase):
    """Additional test cases for LRO handling"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch('builtins.print')
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_lro_with_202_status(self, mock_sleep, mock_get, mock_print):
        """Test LRO with 202 status code"""
        mock_response_202 = Mock()
        mock_response_202.status_code = 202
        mock_response_202.headers = {'Retry-After': '5'}
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"status": "Completed"}
        
        mock_get.side_effect = [mock_response_202, mock_response_200]
        
        result = self.client._wait_for_lro_completion(
            "https://api.fabric.microsoft.com/operations/123",
            operation_name="test"
        )
        
        self.assertEqual(result.status_code, 200)
    
    @patch('builtins.print')
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_lro_with_404_status(self, mock_sleep, mock_get, mock_print):
        """Test LRO with 404 status"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = self.client._wait_for_lro_completion(
            "https://api.fabric.microsoft.com/operations/123",
            operation_name="test"
        )
        
        self.assertEqual(result.status_code, 404)
    
    @patch('builtins.print')
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_lro_with_unknown_status(self, mock_sleep, mock_get, mock_print):
        """Test LRO with unknown job status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "UnknownStatus"}
        mock_get.return_value = mock_response
        
        result = self.client._wait_for_lro_completion(
            "https://api.fabric.microsoft.com/operations/123",
            operation_name="test"
        )
        
        self.assertEqual(result.status_code, 200)
    
    @patch('builtins.print')
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_lro_with_succeeded_status(self, mock_sleep, mock_get, mock_print):
        """Test LRO with Succeeded status"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "Succeeded"}
        mock_get.return_value = mock_response
        
        result = self.client._wait_for_lro_completion(
            "https://api.fabric.microsoft.com/operations/123",
            operation_name="test"
        )
        
        self.assertEqual(result.status_code, 200)
    
    @patch('builtins.print')
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_lro_with_500_error(self, mock_sleep, mock_get, mock_print):
        """Test LRO with HTTP 500 error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Server error"}}
        mock_response.text = "Internal error"
        mock_get.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client._wait_for_lro_completion(
                "https://api.fabric.microsoft.com/operations/123",
                operation_name="test"
            )
    
    @patch('builtins.print')
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_lro_request_exception(self, mock_sleep, mock_get, mock_print):
        """Test LRO with request exception"""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        with self.assertRaises(FabricApiError):
            self.client._wait_for_lro_completion(
                "https://api.fabric.microsoft.com/operations/123",
                operation_name="test"
            )
    
    @patch('builtins.print')
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_lro_with_no_status_field(self, mock_sleep, mock_get, mock_print):
        """Test LRO with 200 response without status field"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "some_data"}
        mock_get.return_value = mock_response
        
        result = self.client._wait_for_lro_completion(
            "https://api.fabric.microsoft.com/operations/123",
            operation_name="test"
        )
        
        self.assertEqual(result.status_code, 200)
    
    @patch('builtins.print')
    @patch('fabric_api.requests.get')
    @patch('fabric_api.time.sleep')
    def test_lro_with_non_json_response(self, mock_sleep, mock_get, mock_print):
        """Test LRO with 200 response that's not JSON"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_get.return_value = mock_response
        
        result = self.client._wait_for_lro_completion(
            "https://api.fabric.microsoft.com/operations/123",
            operation_name="test"
        )
        
        self.assertEqual(result.status_code, 200)


class TestFabricApiClientWorkspacesAdvanced(unittest.TestCase):
    """Additional test cases for workspace operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_list_workspaces_error(self, mock_request, mock_print):
        """Test listing workspaces with error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.list_workspaces()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_get_workspace_not_found(self, mock_request):
        """Test getting a workspace that doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": []}
        mock_request.return_value = mock_response
        
        workspace = self.client.get_workspace("NonexistentWorkspace")
        
        self.assertIsNone(workspace)
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_assign_workspace_to_capacity_error(self, mock_request, mock_print):
        """Test assigning workspace to capacity with error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.assign_workspace_to_capacity("ws-123", "cap-456")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_workspace_not_found(self, mock_request):
        """Test deleting a workspace that doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        result = self.client.delete_workspace("ws-nonexistent")
        
        self.assertIsNone(result)


class TestFabricApiClientConnectionsAdvanced(unittest.TestCase):
    """Additional test cases for connection operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_create_eventhub_connection_error(self, mock_request, mock_print):
        """Test creating Event Hub connection with error"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.create_eventhub_connection(
                name="TestConnection",
                namespace_name="test-namespace",
                event_hub_name="test-hub",
                shared_access_policy_name="policy",
                shared_access_key="key123"
            )
    
    @patch.object(FabricApiClient, '_make_request')
    def test_update_eventhub_connection_success(self, mock_request):
        """Test updating Event Hub connection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "conn-123", "displayName": "UpdatedConnection"}
        mock_request.return_value = mock_response
        
        connection = self.client.update_eventhub_connection(
            connection_id="conn-123",
            name="UpdatedConnection",
            namespace_name="test-namespace",
            event_hub_name="test-hub",
            shared_access_policy_name="policy",
            shared_access_key="key123"
        )
        
        self.assertEqual(connection['displayName'], "UpdatedConnection")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_connection_not_found(self, mock_request):
        """Test deleting a connection that doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        result = self.client.delete_connection("conn-nonexistent")
        
        self.assertIsNone(result)
    
    @patch.object(FabricApiClient, '_make_request')
    def test_list_supported_connection_types_success(self, mock_request):
        """Test listing supported connection types"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"type": "EventHub"},
                {"type": "SQL"}
            ]
        }
        mock_request.return_value = mock_response
        
        types = self.client.list_supported_connection_types()
        
        self.assertEqual(len(types), 2)


class TestFabricWorkspaceApiClientNotebooksAdvanced(unittest.TestCase):
    """Additional test cases for notebook operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_notebook_with_folder(self, mock_request):
        """Test creating a notebook in a folder"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": "new-nb-id"}'
        mock_response.json.return_value = {"id": "new-nb-id"}
        mock_request.return_value = mock_response
        
        result = self.client.create_notebook(
            notebook_name="NewNotebook",
            notebook_data_base64="base64content",
            folder_id="folder-123"
        )
        
        self.assertEqual(result['id'], "new-nb-id")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_notebook_without_waiting(self, mock_request):
        """Test creating a notebook without waiting for LRO"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_request.return_value = mock_response
        
        result = self.client.create_notebook(
            notebook_name="NewNotebook",
            notebook_data_base64="base64content",
            wait_for_lro=False
        )
        
        self.assertEqual(result.status_code, 202)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_get_notebook_by_name_empty_name(self, mock_request):
        """Test getting notebook by empty name"""
        with self.assertRaises(FabricApiError):
            self.client.get_notebook_by_name("")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_notebooks_single_page(self, mock_request):
        """Test listing notebooks returning single page"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [{"id": "nb-1", "displayName": "Notebook1"}]
        }
        mock_request.return_value = mock_response
        
        notebooks = self.client.list_notebooks(get_all=False)
        
        self.assertIn('value', notebooks)


class TestFabricWorkspaceApiClientNotebookJobsAdvanced(unittest.TestCase):
    """Additional test cases for notebook job operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    @patch.object(FabricWorkspaceApiClient, 'get_notebook')
    def test_schedule_notebook_job_with_lro(self, mock_get_notebook, mock_request):
        """Test scheduling notebook job with LRO"""
        mock_get_notebook.return_value = {
            "id": "nb-123",
            "displayName": "TestNotebook"
        }
        
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {'location': 'https://api.fabric.microsoft.com/operations/123'}
        mock_request.return_value = mock_response
        
        with patch.object(self.client, '_wait_for_lro_completion') as mock_lro:
            mock_lro_response = Mock()
            mock_lro_response.status_code = 200
            mock_lro_response.json.return_value = {"status": "Completed"}
            mock_lro.return_value = mock_lro_response
            
            result = self.client.schedule_notebook_job("nb-123")
        
        self.assertEqual(result['status'], 'Completed')
    
    @patch('builtins.print')
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    @patch.object(FabricWorkspaceApiClient, 'get_notebook')
    def test_schedule_notebook_job_error_response(self, mock_get_notebook, mock_request, mock_print):
        """Test scheduling notebook job with error response"""
        mock_get_notebook.return_value = {
            "id": "nb-123",
            "displayName": "TestNotebook"
        }
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_request.return_value = mock_response
        
        result = self.client.schedule_notebook_job("nb-123")
        
        self.assertEqual(result['status'], 'Failed')


class TestFabricWorkspaceApiClientFoldersAdvanced(unittest.TestCase):
    """Additional test cases for folder operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_folders_with_pagination(self, mock_request):
        """Test listing folders with pagination"""
        mock_response_page1 = Mock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = {
            "value": [{"id": "folder-1"}],
            "continuationToken": "token123"
        }
        
        mock_response_page2 = Mock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = {
            "value": [{"id": "folder-2"}]
        }
        
        mock_request.side_effect = [mock_response_page1, mock_response_page2]
        
        folders = self.client.list_folders()
        
        self.assertEqual(len(folders), 2)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_folders_single_page(self, mock_request):
        """Test listing folders returning single page"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [{"id": "folder-1"}]
        }
        mock_request.return_value = mock_response
        
        result = self.client.list_folders(get_all=False)
        
        self.assertIn('value', result)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_folders_with_root_folder(self, mock_request):
        """Test listing folders with root folder ID"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"id": "folder-1"}]}
        mock_request.return_value = mock_response
        
        folders = self.client.list_folders(root_folder_id="root-123", recursive=False)
        
        self.assertEqual(len(folders), 1)


class TestFabricWorkspaceApiClientRoleAssignmentsAdvanced(unittest.TestCase):
    """Additional test cases for role assignment operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_add_role_assignment_with_user_details(self, mock_request):
        """Test adding role assignment with user principal name"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "ra-123",
            "principal": {"id": "user-456", "type": "User"},
            "role": "Admin"
        }
        mock_request.return_value = mock_response
        
        assignment = self.client.add_role_assignment(
            principal_id="user-456",
            principal_type="User",
            role="Admin",
            display_name="Test User",
            user_principal_name="test@example.com"
        )
        
        self.assertEqual(assignment['role'], "Admin")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_add_role_assignment_service_principal(self, mock_request):
        """Test adding role assignment for service principal"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "ra-123",
            "principal": {"id": "sp-456", "type": "ServicePrincipal"},
            "role": "Contributor"
        }
        mock_request.return_value = mock_response
        
        assignment = self.client.add_role_assignment(
            principal_id="sp-456",
            principal_type="ServicePrincipal",
            role="Contributor",
            aad_app_id="app-123"
        )
        
        self.assertEqual(assignment['role'], "Contributor")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_add_role_assignment_group(self, mock_request):
        """Test adding role assignment for group"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "ra-123",
            "principal": {"id": "grp-456", "type": "Group"},
            "role": "Viewer"
        }
        mock_request.return_value = mock_response
        
        assignment = self.client.add_role_assignment(
            principal_id="grp-456",
            principal_type="Group",
            role="Viewer",
            group_type="SecurityGroup"
        )
        
        self.assertEqual(assignment['role'], "Viewer")
    
    def test_add_role_assignment_invalid_group_type(self):
        """Test adding role assignment with invalid group type"""
        with self.assertRaises(FabricApiError):
            self.client.add_role_assignment(
                principal_id="grp-456",
                principal_type="Group",
                role="Viewer",
                group_type="InvalidGroupType"
            )
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_role_assignments_single_page(self, mock_request):
        """Test listing role assignments returning single page"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [{"id": "ra-1"}]
        }
        mock_request.return_value = mock_response
        
        result = self.client.list_role_assignments(get_all=False)
        
        self.assertIn('value', result)


class TestFabricWorkspaceApiClientLakehousesAdvanced(unittest.TestCase):
    """Additional test cases for lakehouse operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_lakehouse_with_all_options(self, mock_request):
        """Test creating lakehouse with all options"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "lh-123", "displayName": "TestLakehouse"}
        mock_request.return_value = mock_response
        
        lakehouse = self.client.create_lakehouse(
            display_name="TestLakehouse",
            description="Test description",
            folder_id="folder-123",
            enable_schemas=True
        )
        
        self.assertEqual(lakehouse['id'], "lh-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_update_lakehouse_with_description(self, mock_request):
        """Test updating lakehouse with description only"""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "lh-123", "description": "New description"}
        mock_request.return_value = mock_response
        
        lakehouse = self.client.update_lakehouse("lh-123", description="New description")
        
        self.assertEqual(lakehouse['description'], "New description")


class TestFabricWorkspaceApiClientEnvironmentsAdvanced(unittest.TestCase):
    """Additional test cases for environment operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_environment_with_all_options(self, mock_request):
        """Test creating environment with all options"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "env-123", "displayName": "TestEnv"}
        mock_request.return_value = mock_response
        
        env = self.client.create_environment(
            display_name="TestEnv",
            description="Test description",
            folder_id="folder-123"
        )
        
        self.assertEqual(env['id'], "env-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_environments_single_page(self, mock_request):
        """Test listing environments returning single page"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [{"id": "env-1"}]
        }
        mock_request.return_value = mock_response
        
        result = self.client.list_environments(get_all=False)
        
        self.assertIn('value', result)
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_update_environment_definition_with_all_parts(self, mock_request):
        """Test updating environment definition with all parts"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        result = self.client.update_environment_definition(
            "env-123",
            environment_yml_base64="env_content",
            sparkcompute_yml_base64="spark_content",
            platform_base64="platform_content"
        )
        
        self.assertTrue(result)


class TestFabricWorkspaceApiClientDataAgentsAdvanced(unittest.TestCase):
    """Additional test cases for data agent operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_data_agent_with_folder(self, mock_request):
        """Test creating data agent in a folder"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "agent-123", "displayName": "TestAgent"}
        mock_request.return_value = mock_response
        
        agent = self.client.create_data_agent("TestAgent", folder_id="folder-123")
        
        self.assertEqual(agent['id'], "agent-123")
    
    def test_get_data_agent_by_name_empty_name(self):
        """Test getting data agent by empty name"""
        with self.assertRaises(FabricApiError):
            self.client.get_data_agent_by_name("")


class TestFabricWorkspaceApiClientDeletion(unittest.TestCase):
    """Test cases for deletion operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricApiClient, 'delete_workspace')
    def test_delete_workspace_via_client(self, mock_delete):
        """Test deleting workspace via workspace client"""
        mock_delete.return_value = "ws-123"
        
        result = self.client.delete()
        
        self.assertEqual(result, "ws-123")
    
    @patch.object(FabricApiClient, 'assign_workspace_to_capacity')
    def test_assign_to_capacity_via_client(self, mock_assign):
        """Test assigning to capacity via workspace client"""
        self.client.assign_to_capacity("cap-456")
        
        mock_assign.assert_called_once_with("ws-123", "cap-456")


class TestConnectionOperations(unittest.TestCase):
    """Test cases for connection operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_list_connections_success(self, mock_request):
        """Test listing connections successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"id": "conn-1", "name": "Connection1"}]}
        mock_request.return_value = mock_response
        
        connections = self.client.list_connections()
        
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0]['id'], "conn-1")
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_list_connections_error(self, mock_request, mock_print):
        """Test listing connections with error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.list_connections()
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_list_connections_exception(self, mock_request, mock_print):
        """Test listing connections with exception"""
        mock_request.side_effect = Exception("Network error")
        
        with self.assertRaises(FabricApiError):
            self.client.list_connections()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_get_connection_success(self, mock_request):
        """Test getting a connection successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "conn-123", "name": "TestConnection"}
        mock_request.return_value = mock_response
        
        connection = self.client.get_connection("conn-123")
        
        self.assertEqual(connection['id'], "conn-123")
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_get_connection_not_found(self, mock_request, mock_print):
        """Test getting a connection that doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.get_connection("conn-nonexistent")
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_get_connection_exception(self, mock_request, mock_print):
        """Test getting a connection with exception"""
        mock_request.side_effect = Exception("Timeout")
        
        with self.assertRaises(FabricApiError):
            self.client.get_connection("conn-123")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_connection_success(self, mock_request):
        """Test deleting connection successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        result = self.client.delete_connection("conn-123")
        
        self.assertEqual(result, "conn-123")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_connection_not_found(self, mock_request):
        """Test deleting a connection that doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        result = self.client.delete_connection("conn-nonexistent")
        
        self.assertIsNone(result)
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_connection_error(self, mock_request, mock_print):
        """Test deleting connection with error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.delete_connection("conn-123")
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_connection_exception(self, mock_request, mock_print):
        """Test deleting connection with exception"""
        mock_request.side_effect = Exception("Network error")
        
        with self.assertRaises(FabricApiError):
            self.client.delete_connection("conn-123")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_list_supported_connection_types_success(self, mock_request):
        """Test listing supported connection types"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"type": "SqlServer"}, {"type": "EventHub"}]}
        mock_request.return_value = mock_response
        
        types = self.client.list_supported_connection_types()
        
        self.assertEqual(len(types), 2)
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_list_supported_connection_types_error(self, mock_request, mock_print):
        """Test listing supported connection types with error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.list_supported_connection_types()
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_list_supported_connection_types_exception(self, mock_request, mock_print):
        """Test listing supported connection types with exception"""
        mock_request.side_effect = Exception("API error")
        
        with self.assertRaises(FabricApiError):
            self.client.list_supported_connection_types()


class TestEventHubConnectionOperations(unittest.TestCase):
    """Test cases for Event Hub connection operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_create_eventhub_connection_success(self, mock_request):
        """Test creating Event Hub connection"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "conn-123", "name": "TestEH"}
        mock_request.return_value = mock_response
        
        connection = self.client.create_eventhub_connection(
            name="TestEH",
            namespace_name="ns-test",
            event_hub_name="eh-test",
            shared_access_policy_name="policy",
            shared_access_key="key123"
        )
        
        self.assertEqual(connection['id'], "conn-123")
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_create_eventhub_connection_error(self, mock_request, mock_print):
        """Test creating Event Hub connection with error"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.create_eventhub_connection(
                name="TestEH",
                namespace_name="ns-test",
                event_hub_name="eh-test",
                shared_access_policy_name="policy",
                shared_access_key="key123"
            )
    
    @patch.object(FabricApiClient, '_make_request')
    def test_update_eventhub_connection_success(self, mock_request):
        """Test updating Event Hub connection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "conn-123", "name": "UpdatedEH"}
        mock_request.return_value = mock_response
        
        connection = self.client.update_eventhub_connection(
            connection_id="conn-123",
            name="UpdatedEH",
            namespace_name="ns-test",
            event_hub_name="eh-test",
            shared_access_policy_name="policy",
            shared_access_key="newkey123"
        )
        
        self.assertEqual(connection['name'], "UpdatedEH")
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_update_eventhub_connection_error(self, mock_request, mock_print):
        """Test updating Event Hub connection with error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.update_eventhub_connection(
                connection_id="conn-123",
                name="UpdatedEH",
                namespace_name="ns-test",
                event_hub_name="eh-test",
                shared_access_policy_name="policy",
                shared_access_key="newkey123"
            )


class TestDeleteWorkspaceOperations(unittest.TestCase):
    """Test cases for workspace deletion operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_workspace_success(self, mock_request):
        """Test deleting workspace successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        result = self.client.delete_workspace("ws-123")
        
        self.assertEqual(result, "ws-123")
    
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_workspace_not_found(self, mock_request):
        """Test deleting workspace that doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        result = self.client.delete_workspace("ws-nonexistent")
        
        self.assertIsNone(result)
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_workspace_error(self, mock_request, mock_print):
        """Test deleting workspace with error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.delete_workspace("ws-123")
    
    @patch('builtins.print')
    @patch.object(FabricApiClient, '_make_request')
    def test_delete_workspace_exception(self, mock_request, mock_print):
        """Test deleting workspace with exception"""
        mock_request.side_effect = Exception("Network error")
        
        with self.assertRaises(FabricApiError):
            self.client.delete_workspace("ws-123")


class TestCapacityOperations(unittest.TestCase):
    """Test cases for capacity operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch.object(FabricApiClient, '_make_request')
    def test_list_capacities_exception(self, mock_request):
        """Test listing capacities with exception"""
        mock_request.side_effect = Exception("API error")
        
        with self.assertRaises(FabricApiError):
            self.client.list_capacities()


class TestUpdateNotebookOperations(unittest.TestCase):
    """Test cases for notebook update operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_update_notebook_no_wait(self, mock_request):
        """Test updating notebook without waiting"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_request.return_value = mock_response
        
        result = self.client.update_notebook("nb-123", "base64content", wait_for_lro=False)
        
        self.assertEqual(result, mock_response)
    
    @patch('builtins.print')
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_update_notebook_error(self, mock_request, mock_print):
        """Test updating notebook with error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.update_notebook("nb-123", "base64content")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_update_notebook_exception(self, mock_request):
        """Test updating notebook with exception"""
        mock_request.side_effect = Exception("Timeout")
        
        with self.assertRaises(FabricApiError):
            self.client.update_notebook("nb-123", "base64content")


class TestCreateNotebookOperations(unittest.TestCase):
    """Test cases for notebook creation operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_notebook_error(self, mock_request):
        """Test creating notebook with error"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.create_notebook("TestNotebook", "base64content")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_create_notebook_exception(self, mock_request):
        """Test creating notebook with exception"""
        mock_request.side_effect = Exception("Network error")
        
        with self.assertRaises(FabricApiError):
            self.client.create_notebook("TestNotebook", "base64content")


class TestListNotebooksErrors(unittest.TestCase):
    """Test cases for notebook listing error scenarios"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_notebooks_error(self, mock_request):
        """Test listing notebooks with error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client.list_notebooks()
    
    @patch.object(FabricWorkspaceApiClient, '_make_request')
    def test_list_notebooks_exception(self, mock_request):
        """Test listing notebooks with exception"""
        mock_request.side_effect = Exception("Timeout")
        
        with self.assertRaises(FabricApiError):
            self.client.list_notebooks()


class TestWorkspaceInfoOperations(unittest.TestCase):
    """Test cases for workspace info operations"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricWorkspaceApiClient(workspace_id="ws-123")
    
    @patch.object(FabricWorkspaceApiClient, 'get_workspace_info')
    def test_get_workspace_404(self, mock_get_info):
        """Test getting workspace when not found (404)"""
        mock_get_info.side_effect = FabricApiError("Not found", status_code=404)
        
        result = self.client.get_workspace()
        
        self.assertIsNone(result)


class TestLROAdvancedScenarios(unittest.TestCase):
    """Test cases for advanced LRO scenarios"""
    
    @patch('fabric_api.AzureCliCredential')
    def setUp(self, mock_credential_class):
        """Set up test fixtures"""
        self.mock_credential = Mock()
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_token.expires_on = time.time() + 3600
        self.mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = self.mock_credential
        
        self.client = FabricApiClient()
    
    @patch('builtins.print')
    @patch('fabric_api.requests.Session.request')
    def test_lro_no_location_header_warning(self, mock_session_request, mock_print):
        """Test LRO without Location header triggers warning"""
        # First response is 202 but no Location header
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {}  # No Location header
        mock_session_request.return_value = mock_response
        
        # Make request with wait_for_lro=True
        response = self.client._make_request("test", wait_for_lro=True)
        
        self.assertEqual(response.status_code, 202)
    
    @patch('builtins.print')
    @patch('fabric_api.time.sleep')
    @patch('fabric_api.time.time')
    @patch('fabric_api.requests.Session.request')
    def test_wait_for_lro_completion_404_response(self, mock_session_request, mock_time, mock_sleep, mock_print):
        """Test _wait_for_lro_completion with 404 response"""
        mock_time.side_effect = [0, 5]
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session_request.return_value = mock_response
        
        result = self.client._wait_for_lro_completion(
            "https://api.fabric.microsoft.com/v1/operations/op-123",
            max_wait_time=60
        )
        
        self.assertEqual(result.status_code, 404)
    
    @patch('builtins.print')
    @patch('fabric_api.time.sleep')
    @patch('fabric_api.time.time')
    @patch('fabric_api.requests.Session.request')
    def test_wait_for_lro_completion_unexpected_status(self, mock_session_request, mock_time, mock_sleep, mock_print):
        """Test _wait_for_lro_completion with unexpected status code"""
        mock_time.side_effect = [0, 5]
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {"error": {"message": "Server error"}}
        mock_session_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client._wait_for_lro_completion(
                "https://api.fabric.microsoft.com/v1/operations/op-123",
                max_wait_time=60
            )
    
    @patch('builtins.print')
    @patch('fabric_api.time.sleep')
    @patch('fabric_api.time.time')
    @patch('fabric_api.requests.Session.request')
    def test_wait_for_lro_completion_unexpected_status_no_json(self, mock_session_request, mock_time, mock_sleep, mock_print):
        """Test _wait_for_lro_completion with unexpected status code and no JSON response"""
        mock_time.side_effect = [0, 5]
        
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_response.json.side_effect = ValueError("No JSON")
        mock_session_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError):
            self.client._wait_for_lro_completion(
                "https://api.fabric.microsoft.com/v1/operations/op-123",
                max_wait_time=60
            )
    
    @patch('builtins.print')
    @patch('fabric_api.time.sleep')
    @patch('fabric_api.time.time')
    @patch('fabric_api.requests.Session.request')
    def test_wait_for_lro_completion_request_exception(self, mock_session_request, mock_time, mock_sleep, mock_print):
        """Test _wait_for_lro_completion with requests exception"""
        import requests
        mock_time.side_effect = [0, 5]
        mock_session_request.side_effect = requests.RequestException("Connection error")
        
        with self.assertRaises(FabricApiError):
            self.client._wait_for_lro_completion(
                "https://api.fabric.microsoft.com/v1/operations/op-123",
                max_wait_time=60
            )
    
    @patch('builtins.print')
    @patch('fabric_api.time.sleep')
    @patch('fabric_api.time.time')
    @patch('fabric_api.requests.Session.request')
    def test_wait_for_lro_completion_timeout(self, mock_session_request, mock_time, mock_sleep, mock_print):
        """Test _wait_for_lro_completion timeout"""
        # Simulate time passing beyond timeout
        mock_time.side_effect = [0, 65]  # Start at 0, then jump past 60 seconds
        
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {}
        mock_session_request.return_value = mock_response
        
        with self.assertRaises(FabricApiError) as context:
            self.client._wait_for_lro_completion(
                "https://api.fabric.microsoft.com/v1/operations/op-123",
                max_wait_time=60
            )
        
        self.assertIn("timed out", str(context.exception))
    
    @patch('builtins.print')
    @patch('fabric_api.time.sleep')
    @patch('fabric_api.time.time')
    @patch('fabric_api.requests.get')
    def test_wait_for_lro_completion_retry_after_header(self, mock_requests_get, mock_time, mock_sleep, mock_print):
        """Test _wait_for_lro_completion uses Retry-After header"""
        # Provide enough time.time() values for loop iterations
        mock_time.side_effect = [0, 5, 5, 10, 10, 15]
        
        # First call returns 202 with Retry-After (in-progress)
        mock_response_202 = Mock()
        mock_response_202.status_code = 202
        mock_response_202.headers = {"Retry-After": "10"}
        
        # Second call returns 200 (success)
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {}  # Empty JSON, no status field
        
        mock_requests_get.side_effect = [mock_response_202, mock_response_200]
        
        result = self.client._wait_for_lro_completion(
            "https://api.fabric.microsoft.com/v1/operations/op-123",
            max_wait_time=60
        )
        
        self.assertEqual(result.status_code, 200)


if __name__ == "__main__":
    unittest.main()
