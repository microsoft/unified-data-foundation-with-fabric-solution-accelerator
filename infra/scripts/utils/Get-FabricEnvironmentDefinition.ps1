<#
.SYNOPSIS
    Get Microsoft Fabric Environment Definition using REST API

.DESCRIPTION
    This script retrieves and decodes Microsoft Fabric Environment definitions using the Fabric REST API.
    It handles Azure CLI authentication, makes the API request, and decodes the Base64 payload to provide
    readable environment configuration including libraries, custom libraries, settings, and configuration files.

.PARAMETER WorkspaceId
    The workspace ID (GUID) containing the environment

.PARAMETER EnvironmentId
    The environment ID (GUID) to retrieve

.PARAMETER FolderPath
    Path to save the decoded definition files (defaults to "src/fabric/definitions/environment" relative to repository root)

.PARAMETER Format
    Optional format parameter for the environment definition (as supported by the API)

.PARAMETER SkipTokenization
    If specified, skips the automatic tokenization of JSON files after creation

.EXAMPLE
    .\Get-FabricEnvironmentDefinition.ps1 -WorkspaceId "aaaabbbb-0000-cccc-1111-dddd2222eeee" -EnvironmentId "bbbbcccc-1111-dddd-2222-eeee3333ffff"

.EXAMPLE
    .\Get-FabricEnvironmentDefinition.ps1 -WorkspaceId "aaaabbbb-0000-cccc-1111-dddd2222eeee" -EnvironmentId "bbbbcccc-1111-dddd-2222-eeee3333ffff" -FolderPath "C:\temp\environment"

.NOTES
    Requires Azure CLI to be installed and logged in with appropriate permissions to access Fabric resources.
    
    Required Scopes:
    - Environment.ReadWrite.All or Item.ReadWrite.All
    
    Required Permissions:
    - Read and write permissions for the environment

.LINK
    https://learn.microsoft.com/en-us/rest/api/fabric/environment/items/get-environment-definition
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')]
    [string]$WorkspaceId,
    
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')]
    [string]$EnvironmentId,
    
    [Parameter(Mandatory = $false)]
    [string]$FolderPath = $null,
    
    [Parameter(Mandatory = $false)]
    [string]$Format,

    [Parameter(Mandatory = $false)]
    [int]$TimeoutSeconds = 240,

    [Parameter(Mandatory = $false)]
    [switch]$SkipTokenization
)

# Global variables
$script:ApiUrl = "https://api.fabric.microsoft.com/v1"
$script:ResourceUrl = "https://api.fabric.microsoft.com"
$script:AccessToken = $null
$script:TokenExpiry = $null

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("INFO", "WARNING", "ERROR")]
        [string]$Level = "INFO"
    )
    
    $icon = switch ($Level) {
        "ERROR" { "❌" }
        "WARNING" { "⚠️" }
        default { "ℹ️" }
    }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "$icon [$timestamp] $Message" -ForegroundColor $(
        switch ($Level) {
            "ERROR" { "Red" }
            "WARNING" { "Yellow" }
            default { "White" }
        }
    )
}

function Get-AuthToken {
    <#
    .SYNOPSIS
        Get or refresh Azure CLI authentication token for Fabric API
    #>
    
    try {
        # Check if we need to refresh the token (refresh 5 minutes before expiry)
        $currentTime = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        
        if (-not $script:AccessToken -or ($script:TokenExpiry -and $currentTime -gt ($script:TokenExpiry - 300))) {
            Write-Log "Getting authentication token from Azure CLI"
            
            # Get token using Azure CLI
            $tokenResponse = az account get-access-token --resource $script:ResourceUrl --query "{accessToken:accessToken,expiresOn:expiresOn}" --output json 2>$null
            
            if ($LASTEXITCODE -ne 0) {
                throw "Azure CLI authentication failed. Please run 'az login' first."
            }
            
            $tokenData = $tokenResponse | ConvertFrom-Json
            $script:AccessToken = $tokenData.accessToken
            
            # Parse expiry time (Azure CLI returns ISO 8601 format)
            $expiryDateTime = [DateTime]::Parse($tokenData.expiresOn)
            $script:TokenExpiry = [DateTimeOffset]::new($expiryDateTime).ToUnixTimeSeconds()
            
            Write-Log "Authentication successful"
        }
        
        return $script:AccessToken
    }
    catch {
        throw "Authentication failed: $($_.Exception.Message)"
    }
}

function Invoke-FabricApiRequest {
    <#
    .SYNOPSIS
        Make HTTP request to Fabric API with error handling and authentication
    #>
    param(
        [string]$Uri,
        [string]$Method = "GET",
        [object]$Body = $null,
        [hashtable]$Headers = @{},
        [int]$TimeoutSec = $TimeoutSeconds,
        [int]$MaxRetries = 3
    )
    
    $fullUrl = "$script:ApiUrl/$($Uri.TrimStart('/'))"
    $retryCount = 0
    
    do {
        try {
            Write-Log "Making $Method request to $fullUrl $(if ($retryCount -gt 0) { "(attempt $($retryCount + 1))" })"
            
            # Prepare headers with authentication
            $requestHeaders = @{
                'Content-Type'  = 'application/json; charset=utf-8'
                'Authorization' = "Bearer $(Get-AuthToken)"
            }
            
            # Add custom headers
            foreach ($key in $Headers.Keys) {
                $requestHeaders[$key] = $Headers[$key]
            }
            
            # Prepare request parameters
            $requestParams = @{
                Uri             = $fullUrl
                Method          = $Method
                Headers         = $requestHeaders
                TimeoutSec      = $TimeoutSec
                UseBasicParsing = $true
            }
            
            if ($Body) {
                if ($Body -is [string]) {
                    $requestParams.Body = $Body
                }
                else {
                    $requestParams.Body = $Body | ConvertTo-Json -Depth 10 -Compress
                }
            }
            
            $response = Invoke-WebRequest @requestParams
            
            # Log request ID if available
            $requestId = $response.Headers['requestId']
            if ($requestId) {
                $requestIdValue = if ($requestId -is [array]) { $requestId[0] } else { $requestId }
                Write-Log "Request ID: $requestIdValue"
            }
            
            # Handle different status codes
            switch ($response.StatusCode) {
                200 {
                    Write-Log "Request completed successfully"
                    return $response
                }
                202 {
                    Write-Log "Long-running operation detected, returning 202 response"
                    return $response
                }
                429 {
                    # Rate limiting - retry with exponential backoff
                    $retryAfter = if ($response.Headers['Retry-After']) { 
                        $retryHeaderValue = $response.Headers['Retry-After']
                        [int]($retryHeaderValue -is [array] ? $retryHeaderValue[0] : $retryHeaderValue)
                    }
                    else { 
                        [Math]::Min(60, [Math]::Pow(2, $retryCount))
                    }
                    
                    $retryAfter = [Math]::Min($retryAfter, 300)  # Cap at 5 minutes
                    
                    Write-Log "Rate limit exceeded. Retrying in $retryAfter seconds... (attempt $($retryCount + 1)/$MaxRetries)" "WARNING"
                    Start-Sleep -Seconds $retryAfter
                    $retryCount++
                    continue
                }
                default {
                    $errorMsg = "API request failed with status $($response.StatusCode)"
                    
                    try {
                        $errorResponse = $response.Content | ConvertFrom-Json
                        Write-Log "Error response: $($errorResponse | ConvertTo-Json -Depth 5)" "ERROR"
                        
                        if ($errorResponse.error) {
                            $errorMsg += ": $($errorResponse.error.message)"
                        }
                    }
                    catch {
                        $errorMsg += ": $($response.Content.Substring(0, [Math]::Min(500, $response.Content.Length)))"
                    }
                    
                    throw $errorMsg
                }
            }
        }
        catch {
            if ($_.Exception -is [System.Net.WebException] -and $_.Exception.Response.StatusCode -eq 429 -and $retryCount -lt $MaxRetries) {
                # Handle rate limiting in older PowerShell versions
                $retryAfter = 60
                Write-Log "Rate limit exceeded. Retrying in $retryAfter seconds... (attempt $($retryCount + 1)/$MaxRetries)" "WARNING"
                Start-Sleep -Seconds $retryAfter
                $retryCount++
                continue
            }
            
            throw "Request failed: $($_.Exception.Message)"
        }
    } while ($retryCount -lt $MaxRetries)
    
    throw "Maximum retries ($MaxRetries) exceeded"
}

function ConvertFrom-Base64 {
    <#
    .SYNOPSIS
        Decode Base64 string to UTF-8 text
    #>
    param(
        [string]$Base64String
    )
    
    try {
        $bytes = [System.Convert]::FromBase64String($Base64String)
        return [System.Text.Encoding]::UTF8.GetString($bytes)
    }
    catch {
        throw "Failed to decode Base64 string: $($_.Exception.Message)"
    }
}

function Get-EnvironmentDefinition {
    <#
    .SYNOPSIS
        Get and decode Environment definition from Fabric API
    #>
    
    try {
        Write-Log "Getting environment definition for workspace $WorkspaceId, environment $EnvironmentId"
        
        # Build URI with optional format parameter
        $uri = "workspaces/$WorkspaceId/environments/$EnvironmentId/getDefinition"
        if ($Format) {
            $uri += "?format=$Format"
        }
        
        # Make API request
        $response = Invoke-FabricApiRequest -Uri $uri -Method "POST"
        
        if ($response.StatusCode -eq 202) {
            # Handle long-running operation according to Fabric LRO pattern
            $operationId = $response.Headers['x-ms-operation-id']
            $operationId = if ($operationId -is [array]) { $operationId[0] } else { $operationId }
            $retryAfter = if ($response.Headers['Retry-After']) { 
                $retryHeaderValue = $response.Headers['Retry-After']
                [int]($retryHeaderValue -is [array] ? $retryHeaderValue[0] : $retryHeaderValue)
            }
            else { 30 }
            
            if (-not $operationId) {
                throw "Long-running operation started but no operation ID received"
            }
            
            Write-Log "Long-running operation started. Operation ID: $operationId" "WARNING"
            Write-Log "Polling for completion every $retryAfter seconds..."
            
            do {
                Start-Sleep -Seconds $retryAfter
                Write-Log "Checking operation state..."
                
                try {
                    # Check operation state using proper Fabric LRO endpoint
                    $stateResponse = Invoke-FabricApiRequest -Uri "operations/$operationId" -Method "GET"
                    $stateData = $stateResponse.Content | ConvertFrom-Json
                    
                    Write-Log "Operation status: $($stateData.status)"
                    
                    switch ($stateData.status.ToLower()) {
                        "succeeded" {
                            Write-Log "Operation completed successfully"
                            
                            # Get the operation result using proper Fabric LRO endpoint
                            Write-Log "Retrieving operation result..."
                            $resultResponse = Invoke-FabricApiRequest -Uri "operations/$operationId/result" -Method "GET"
                            $response = $resultResponse
                            break
                        }
                        "failed" {
                            $errorMsg = "Operation failed"
                            if ($stateData.error) {
                                $errorMsg += ": $($stateData.error.message)"
                                Write-Log "Operation error details: $($stateData.error | ConvertTo-Json -Depth 3)" "ERROR"
                            }
                            throw $errorMsg
                        }
                        "running" {
                            Write-Log "Operation still in progress (status: $($stateData.status))..."
                            
                            # Update retry interval if provided in the state response
                            if ($stateData.retryAfter) {
                                $retryAfter = [int]$stateData.retryAfter
                                Write-Log "Updated retry interval to $retryAfter seconds"
                            }
                            continue
                        }
                        "notstarted" {
                            Write-Log "Operation still in progress (status: $($stateData.status))..."
                            
                            # Update retry interval if provided in the state response
                            if ($stateData.retryAfter) {
                                $retryAfter = [int]$stateData.retryAfter
                                Write-Log "Updated retry interval to $retryAfter seconds"
                            }
                            continue
                        }
                        default {
                            Write-Log "Unknown operation status: $($stateData.status)" "WARNING"
                            continue
                        }
                    }
                    
                    # Break out of the polling loop if operation completed (success or failure)
                    break
                }
                catch {
                    Write-Log "Error checking operation state: $($_.Exception.Message)" "ERROR"
                    throw
                }
            } while ($true)
        }
        elseif ($response.StatusCode -ne 200) {
            throw "Failed to get environment definition. Status: $($response.StatusCode)"
        }
        
        # Parse response
        $responseData = $response.Content | ConvertFrom-Json
        
        # Debug: Log the response structure
        Write-Log "Response structure: $($responseData | ConvertTo-Json -Depth 2 -Compress)"
        
        if (-not $responseData.definition) {
            Write-Log "Response does not contain 'definition' property" "ERROR"
            Write-Log "Available properties: $($responseData.PSObject.Properties.Name -join ', ')" "ERROR"
            throw "Invalid response format: missing 'definition' property"
        }
        
        if (-not $responseData.definition.parts) {
            Write-Log "Definition does not contain 'parts' property" "ERROR"
            if ($responseData.definition.PSObject.Properties.Name) {
                Write-Log "Available definition properties: $($responseData.definition.PSObject.Properties.Name -join ', ')" "ERROR"
            }
            throw "Invalid response format: missing 'parts' in definition"
        }
        
        Write-Log "Retrieved environment definition with $($responseData.definition.parts.Count) part(s)"
        
        # Decode all parts
        $decodedParts = @{}
        $summaryInfo = @{}
        
        foreach ($part in $responseData.definition.parts) {
            Write-Log "Processing part: $($part.path)"
            
            if ($part.payloadType -eq "InlineBase64") {
                try {
                    $decodedContent = ConvertFrom-Base64 -Base64String $part.payload
                    $decodedParts[$part.path] = $decodedContent
                    
                    # Try to parse as JSON/YAML for summary information
                    try {
                        # Analyze content based on file name and type
                        switch -Wildcard ($part.path) {
                            "Libraries/PublicLibraries/environment.yml" {
                                # Analyze YAML environment file
                                $lines = $decodedContent -split "`n"
                                $dependenciesCount = ($lines | Where-Object { $_ -match '^\s*-\s*' }).Count
                                $summaryInfo[$part.path] = "Environment YAML file ($dependenciesCount dependencies)"
                            }
                            "Setting/Sparkcompute.yml" {
                                # Analyze Spark compute configuration
                                $summaryInfo[$part.path] = "Spark compute configuration (YAML)"
                            }
                            "Libraries/CustomLibraries/*" {
                                # Analyze custom libraries
                                $fileExtension = [System.IO.Path]::GetExtension($part.path)
                                $fileSize = [Math]::Round($decodedContent.Length / 1024, 2)
                                switch ($fileExtension) {
                                    ".jar" { $summaryInfo[$part.path] = "Custom JAR library ($fileSize KB)" }
                                    ".py" { $summaryInfo[$part.path] = "Custom Python library ($fileSize KB)" }
                                    ".whl" { $summaryInfo[$part.path] = "Python wheel package ($fileSize KB)" }
                                    ".tar.gz" { $summaryInfo[$part.path] = "R package archive ($fileSize KB)" }
                                    default { $summaryInfo[$part.path] = "Custom library file ($fileSize KB)" }
                                }
                            }
                            ".platform" {
                                # Try to parse as JSON for platform configuration
                                try {
                                    $jsonContent = $decodedContent | ConvertFrom-Json
                                    $itemType = if ($jsonContent.metadata -and $jsonContent.metadata.type) { $jsonContent.metadata.type } else { "Unknown" }
                                    $summaryInfo[$part.path] = "Platform configuration ($itemType)"
                                }
                                catch {
                                    $summaryInfo[$part.path] = "Platform configuration file"
                                }
                            }
                            "*.json" {
                                # Try to parse generic JSON files
                                try {
                                    $jsonContent = $decodedContent | ConvertFrom-Json
                                    $summaryInfo[$part.path] = "JSON configuration file"
                                }
                                catch {
                                    $summaryInfo[$part.path] = "JSON file (parse error)"
                                }
                            }
                            default {
                                $fileSize = [Math]::Round($decodedContent.Length / 1024, 2)
                                $summaryInfo[$part.path] = "File content ($fileSize KB)"
                            }
                        }
                    }
                    catch {
                        # Analysis failed - that's okay
                        $summaryInfo[$part.path] = "Text content ($($decodedContent.Length) characters)"
                    }
                }
                catch {
                    Write-Log "Failed to decode part $($part.path): $($_.Exception.Message)" "WARNING"
                    $decodedParts[$part.path] = "[DECODE ERROR: $($_.Exception.Message)]"
                    $summaryInfo[$part.path] = "Decode error"
                }
            }
            else {
                Write-Log "Unsupported payload type for part $($part.path): $($part.payloadType)" "WARNING"
                $decodedParts[$part.path] = "[UNSUPPORTED PAYLOAD TYPE: $($part.payloadType)]"
                $summaryInfo[$part.path] = "Unsupported payload type"
            }
        }
        
        Write-Log "Successfully decoded environment definition"
        
        # Display summary
        Write-Log "Environment definition summary:"
        foreach ($key in $summaryInfo.Keys) {
            Write-Log "  $key : $($summaryInfo[$key])"
        }
        
        # Save to files if folder path specified
        if ($FolderPath) {
            Write-Log "Saving decoded environment definition files to: $FolderPath"
            
            # Create directory and replace if it exists
            if (Test-Path $FolderPath) {
                Write-Log "Folder already exists, replacing contents..." "WARNING"
                Remove-Item -Path $FolderPath -Recurse -Force
            }
            New-Item -ItemType Directory -Path $FolderPath -Force | Out-Null
            
            # Save each part to a separate file, preserving directory structure
            foreach ($partPath in $decodedParts.Keys) {
                # Clean the path but preserve directory structure
                $relativePath = $partPath -replace '^\/', ''  # Remove leading slash if present
                $fullFilePath = Join-Path $FolderPath $relativePath
                
                # Create subdirectories if needed
                $directory = Split-Path $fullFilePath -Parent
                if (-not (Test-Path $directory)) {
                    New-Item -ItemType Directory -Path $directory -Force | Out-Null
                }
                
                try {
                    # Handle different file types appropriately
                    if ($partPath -like "*.json" -and -not $decodedParts[$partPath].StartsWith("[")) {
                        # Pretty-print JSON files
                        $jsonContent = $decodedParts[$partPath] | ConvertFrom-Json
                        $jsonContent | ConvertTo-Json -Depth 10 | Set-Content -Path $fullFilePath -Encoding UTF8 -Force
                    }
                    elseif ($partPath -like "*.yml" -or $partPath -like "*.yaml") {
                        # Save YAML files as-is
                        $decodedParts[$partPath] | Set-Content -Path $fullFilePath -Encoding UTF8 -Force
                    }
                    else {
                        # Save other files as-is
                        $decodedParts[$partPath] | Set-Content -Path $fullFilePath -Encoding UTF8 -Force
                    }
                    
                    Write-Log "  Saved: $relativePath"
                }
                catch {
                    Write-Log "  Failed to save $relativePath : $($_.Exception.Message)" "WARNING"
                }
            }
            
            Write-Log "Environment definition files saved successfully"
        }
        
        # Return the decoded parts
        return $decodedParts
    }
    catch {
        Write-Log "Failed to get environment definition: $($_.Exception.Message)" "ERROR"
        throw
    }
}

# Main execution
try {
    # Calculate default folder path if not provided
    if (-not $FolderPath) {
        $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
        # Script is located at infra\scripts\utils\Get-FabricEnvironmentDefinition.ps1
        $RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir))
        $FolderPath = Join-Path $RepoRoot "src" | Join-Path -ChildPath "fabric" | Join-Path -ChildPath "definitions" | Join-Path -ChildPath "environment"
        Write-Log "Using default folder path: $FolderPath"
    }
    
    Write-Log "Starting Fabric Environment Definition retrieval"
    Write-Log "Workspace ID: $WorkspaceId"
    Write-Log "Environment ID: $EnvironmentId"
    Write-Log "Folder Path: $FolderPath"
    
    if ($Format) {
        Write-Log "Format: $Format"
    }
    
    # Get and display environment definition
    $environmentDefinition = Get-EnvironmentDefinition
    
    Write-Log "Environment definition retrieved successfully" 
    
    # Display the decoded content
    Write-Host "`n=== DECODED ENVIRONMENT DEFINITION PARTS ===" -ForegroundColor Green
    
    foreach ($partPath in $environmentDefinition.Keys) {
        Write-Host "`n--- PART: $partPath ---" -ForegroundColor Cyan
        
        # Try to format based on file type
        try {
            if ($partPath -like "*.json" -and -not $environmentDefinition[$partPath].StartsWith("[")) {
                $jsonContent = $environmentDefinition[$partPath] | ConvertFrom-Json
                $jsonContent | ConvertTo-Json -Depth 10
            }
            else {
                # Display first few lines for large files
                $content = $environmentDefinition[$partPath]
                $lines = $content -split "`n"
                if ($lines.Count -gt 50) {
                    $lines[0..49] -join "`n"
                    Write-Host "`n... (truncated, full content saved to file) ..." -ForegroundColor Yellow
                }
                else {
                    $content
                }
            }
        }
        catch {
            # Display as-is if processing fails
            $environmentDefinition[$partPath]
        }
    }
    
    Write-Host "`n=== END OF DEFINITION ===" -ForegroundColor Green
    
}
catch {
    Write-Log "Script execution failed: $($_.Exception.Message)" "ERROR"
    exit 1
}

Write-Log "Script completed successfully"