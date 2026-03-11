#!/usr/bin/env pwsh
<#
.SYNOPSIS
    JSON Tokenizer Script for Microsoft Fabric RTI Solution

.DESCRIPTION
    This script processes JSON configuration files and replaces specific values with standardized tokens based on the schema type.
    For Activator schema: Tokenizes "eventstreamArtifactId" and "name" (for Event definition types) values in ReflexEntities.json and "displayName", "description" in metadata of .platform file
    For Eventstream schema: Tokenizes "id", "name", "itemId", "workspaceId", "databaseName", "dataConnectionId" values in eventstream.json and "displayName", "description" in metadata of .platform file
    For RealTimeDashboard schema: Tokenizes "clusterUri", "database", "workspace" values in dataSources in RealTimeDashboard.json and "displayName", "description" in metadata of .platform file
    The tokens follow the format __TOKEN_[key_name]_[occurrence]__ where key_name preserves the original key name and occurrence is a sequential number.
    All occurrences of the same value throughout the file are replaced with the same token.
    The double underscore format ensures JSON compatibility and clear token identification.

.PARAMETER SchemaType
    The schema type to process. Valid values: Activator, Eventstream, RealTimeDashboard
    - Activator: Processes ReflexEntities.json and .platform from src/activator/
    - Eventstream: Processes eventstream.json and .platform from src/eventstream/
    - RealTimeDashboard: Processes RealTimeDashboard.json and .platform from src/realTimeDashboard/

.PARAMETER JsonFilePath
    Optional path to the JSON file to tokenize. If not specified, path is calculated based on SchemaType.

.PARAMETER OutputPath
    Optional output path for the tokenized JSON. If not specified, overwrites the original file.

.PARAMETER DryRun
    If specified, shows what would be changed without modifying files

.PARAMETER SaveTokenMap
    If specified, creates a separate token mapping file alongside the tokenized JSON

.EXAMPLE
    .\Run-FabricJsonTokenizer.ps1 -SchemaType Eventstream
    
.EXAMPLE
    .\Run-FabricJsonTokenizer.ps1 -SchemaType Activator -OutputPath "ReflexEntities_tokenized.json"

.EXAMPLE
    .\Run-FabricJsonTokenizer.ps1 -SchemaType RealTimeDashboard

.EXAMPLE
    .\Run-FabricJsonTokenizer.ps1 -SchemaType Eventstream -DryRun

.EXAMPLE
    .\Run-FabricJsonTokenizer.ps1 -SchemaType RealTimeDashboard -SaveTokenMap

.NOTES
    Token format: __TOKEN_[key_name]_[occurrence]__ (JSON-safe with double underscores)
    Schema-aware tokenization:
    - Activator: eventstreamArtifactId and name (for Event definition types) values in ReflexEntities.json and displayName, description in .platform metadata
    - Eventstream: name, itemId, workspaceId, databaseName, dataConnectionId values in eventstream.json and displayName, description in .platform metadata
    - RealTimeDashboard: clusterUri, database, workspace values in dataSources in RealTimeDashboard.json and displayName, description in .platform metadata
    File paths are automatically calculated based on schema type
    Token examples: __TOKEN_eventstreamArtifactId_1__, __TOKEN_name_1__, __TOKEN_clusterUri_1__, __TOKEN_database_1__, __TOKEN_workspace_1__, __TOKEN_displayName_1__, __TOKEN_description_1__, etc.
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Activator", "Eventstream", "RealTimeDashboard")]
    [string]$SchemaType,
    
    [Parameter(Mandatory = $false)]
    [string]$JsonFilePath,
    
    [Parameter(Mandatory = $false)]
    [string]$OutputPath,
    
    [Parameter(Mandatory = $false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory = $false)]
    [switch]$SaveTokenMap
)

# Function to get the default file path based on schema type
function Get-SchemaFilePath {
    param([string]$SchemaType)
    
    $scriptDir = Split-Path -Parent $PSCommandPath
    $rootDir = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir))
    
    switch ($SchemaType.ToLower()) {
        "activator" {
            return @(
                (Join-Path $rootDir "src\activator\ReflexEntities.json"),
                (Join-Path $rootDir "src\activator\.platform")
            )
        }
        "eventstream" {
            return @(
                (Join-Path $rootDir "src\eventstream\eventstream.json"),
                (Join-Path $rootDir "src\eventstream\.platform")
            )
        }
        "realtimedashboard" {
            return @(
                (Join-Path $rootDir "src\realTimeDashboard\RealTimeDashboard.json"),
                (Join-Path $rootDir "src\realTimeDashboard\.platform")
            )
        }
        default {
            throw "Unknown schema type: $SchemaType"
        }
    }
}



# Function to normalize schema type
function Get-NormalizedSchemaType {
    param([string]$SchemaType)
    
    switch ($SchemaType.ToLower()) {
        "activator" {
            return "reflexentities"
        }
        "eventstream" {
            return "eventstream"
        }
        "realtimedashboard" {
            return "realtimedashboard"
        }
        default {
            throw "Unknown schema type: $SchemaType"
        }
    }
}

# Function to get tokenizable fields based on schema type
function Get-TokenizableFields {
    param([string]$SchemaType)
    
    switch ($SchemaType) {
        "eventstream" {
            return @("name", "workspaceId", "databaseName")
        }
        "reflexentities" {
            return @("eventstreamArtifactId", "name", "email")
        }
        "realtimedashboard" {
            return @("clusterUri", "workspace", "database")
        }
        "platform" {
            return @("displayName", "description")
        }
        default {
            return @("eventstreamArtifactId", "name")
        }
    }
}

# Function to determine if a value should be tokenized
function Should-Tokenize {
    param(
        [string]$Key,
        [string]$Value,
        [string[]]$TokenizableFields
    )
    
    # Skip empty values
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }
    
    # Check if the key is in the list of tokenizable fields
    return $TokenizableFields -contains $Key.ToLower()
}

# Function to check if a string is a valid email address
function Test-EmailAddress {
    param([string]$Value)
    
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }
    
    # Email regex pattern - matches standard email format
    $emailPattern = '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    return $Value -match $emailPattern
}

# Function to find all email addresses in a string
function Find-EmailsInString {
    param([string]$InputString)
    
    if ([string]::IsNullOrWhiteSpace($InputString)) {
        return @()
    }
    
    # Email regex pattern - matches standard email format
    $emailPattern = '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    $matches = [regex]::Matches($InputString, $emailPattern)
    
    return $matches | ForEach-Object { $_.Value }
}

# Function to apply schema-driven token replacement without affecting JSON keys
function Apply-SchemaTokenReplacement {
    param(
        [object]$JsonObject,
        [hashtable]$ValueToTokenMap,
        [string]$SchemaType,
        [switch]$DryRun
    )
    
    if ($JsonObject -is [System.Collections.IDictionary]) {
        # Handle schema-specific processing at the top level
        if ($SchemaType -eq "eventstream") {
            # For eventstream schema, apply specific logic based on JSON structure
            foreach ($key in @($JsonObject.Keys)) {
                $value = $JsonObject[$key]
                switch ($key) {
                    "sources" {
                        if ($value -is [System.Array]) {
                            foreach ($source in $value) {
                                Apply-EventstreamSourceTokens -Source $source -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                            }
                        }
                    }
                    "destinations" {
                        if ($value -is [System.Array]) {
                            foreach ($destination in $value) {
                                Apply-EventstreamDestinationTokens -Destination $destination -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                            }
                        }
                    }
                    "streams" {
                        if ($value -is [System.Array]) {
                            foreach ($stream in $value) {
                                Apply-EventstreamStreamTokens -Stream $stream -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                            }
                        }
                    }
                    default {
                        # Recursively process other objects/arrays
                        Apply-SchemaTokenReplacement -JsonObject $value -ValueToTokenMap $ValueToTokenMap -SchemaType $SchemaType -DryRun:$DryRun
                    }
                }
            }
        }
        elseif ($SchemaType -eq "reflexentities") {
            # For Activator schema, handle the root array directly since ReflexEntities.json is an array
            if ($JsonObject -is [System.Array]) {
                foreach ($entity in $JsonObject) {
                    if ($entity -is [hashtable]) {
                        Apply-ActivatorEntityTokens -Entity $entity -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                    }
                }
            }
            else {
                # Handle if it's an object with array properties
                foreach ($key in @($JsonObject.Keys)) {
                    $value = $JsonObject[$key]
                    if ($value -is [System.Array]) {
                        foreach ($entity in $value) {
                            Apply-ActivatorEntityTokens -Entity $entity -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                        }
                    }
                    else {
                        # Recursively process other objects/arrays
                        Apply-SchemaTokenReplacement -JsonObject $value -ValueToTokenMap $ValueToTokenMap -SchemaType $SchemaType -DryRun:$DryRun
                    }
                }
            }
        }
        elseif ($SchemaType -eq "realtimedashboard") {
            # Handle different sections with specific tokenization rules
            foreach ($key in @($JsonObject.Keys)) {
                $value = $JsonObject[$key]
                switch ($key) {
                    "tiles" {
                        if ($value -is [System.Array]) {
                            foreach ($tile in $value) {
                                Apply-DashboardTileTokens -Tile $tile -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                            }
                        }
                    }
                    "parameters" {
                        if ($value -is [System.Array]) {
                            foreach ($parameter in $value) {
                                Apply-DashboardParameterTokens -Parameter $parameter -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                            }
                        }
                    }
                    "dataSources" {
                        if ($value -is [System.Array]) {
                            foreach ($datasource in $value) {
                                Apply-DashboardDataSourceTokens -DataSource $datasource -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                            }
                        }
                    }
                    "pages" {
                        if ($value -is [System.Array]) {
                            foreach ($page in $value) {
                                Apply-DashboardPageTokens -Page $page -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                            }
                        }
                    }
                    "queries" {
                        if ($value -is [System.Array]) {
                            foreach ($query in $value) {
                                Apply-DashboardQueryTokens -Query $query -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                            }
                        }
                    }
                    default {
                        # Recursively process other objects/arrays
                        Apply-SchemaTokenReplacement -JsonObject $value -ValueToTokenMap $ValueToTokenMap -SchemaType $SchemaType -DryRun:$DryRun
                    }
                }
            }
        }
        elseif ($SchemaType -eq "platform") {
            # Handle .platform file schema with metadata tokenization
            foreach ($key in @($JsonObject.Keys)) {
                $value = $JsonObject[$key]
                if ($key -eq "metadata" -and $value -is [System.Collections.IDictionary]) {
                    # Tokenize displayName and description in metadata using field-specific tokens
                    foreach ($metadataField in @("displayName", "description")) {
                        if ($value.ContainsKey($metadataField) -and $value[$metadataField]) {
                            $originalValue = $value[$metadataField]
                            $token = "__TOKEN_${metadataField}_1__"
                            $value[$metadataField] = $token
                            if (-not $DryRun) {
                                Write-Host "  Replaced metadata.${metadataField}: '$originalValue' -> $token" -ForegroundColor Green
                            }
                        }
                    }
                }
                else {
                    Apply-SchemaTokenReplacement -JsonObject $value -ValueToTokenMap $ValueToTokenMap -SchemaType $SchemaType -DryRun:$DryRun
                }
            }
        }
        else {
            # For unknown schemas, use general recursive processing with value replacement
            foreach ($key in @($JsonObject.Keys)) {
                $value = $JsonObject[$key]
                if ($value -is [System.Collections.IDictionary] -or $value -is [System.Array]) {
                    Apply-SchemaTokenReplacement -JsonObject $value -ValueToTokenMap $ValueToTokenMap -SchemaType $SchemaType -DryRun:$DryRun
                }
                elseif ($ValueToTokenMap.ContainsKey($value)) {
                    $token = $ValueToTokenMap[$value]
                    $JsonObject[$key] = $token
                    if (-not $DryRun) {
                        Write-Host "  Replaced: $key = '$value' -> $token" -ForegroundColor Green
                    }
                }
            }
        }
    }
    elseif ($JsonObject -is [System.Array]) {
        for ($i = 0; $i -lt $JsonObject.Length; $i++) {
            Apply-SchemaTokenReplacement -JsonObject $JsonObject[$i] -ValueToTokenMap $ValueToTokenMap -SchemaType $SchemaType -DryRun:$DryRun
        }
    }
}

# Function to apply tokens to eventstream source objects
function Apply-EventstreamSourceTokens {
    param(
        [hashtable]$Source,
        [hashtable]$ValueToTokenMap,
        [switch]$DryRun
    )
    
    # Tokenize specific fields in sources
    $tokenizableFields = @("name")
    foreach ($field in $tokenizableFields) {
        if ($Source.ContainsKey($field) -and $ValueToTokenMap.ContainsKey($Source[$field])) {
            $originalValue = $Source[$field]
            $token = $ValueToTokenMap[$originalValue]
            $Source[$field] = $token
            if (-not $DryRun) {
                Write-Host "  Replaced source.${field}: '$originalValue' -> $token" -ForegroundColor Green
            }
        }
    }
    
    # Process nested properties - but don't tokenize dataConnectionId anymore
    # No specific property tokenization for sources
}

# Function to apply tokens to eventstream destination objects
function Apply-EventstreamDestinationTokens {
    param(
        [hashtable]$Destination,
        [hashtable]$ValueToTokenMap,
        [switch]$DryRun
    )
    
    # Tokenize specific fields in destinations
    $tokenizableFields = @("name")
    foreach ($field in $tokenizableFields) {
        if ($Destination.ContainsKey($field) -and $ValueToTokenMap.ContainsKey($Destination[$field])) {
            $originalValue = $Destination[$field]
            $token = $ValueToTokenMap[$originalValue]
            $Destination[$field] = $token
            if (-not $DryRun) {
                Write-Host "  Replaced destination.${field}: '$originalValue' -> $token" -ForegroundColor Green
            }
        }
    }
    
    # Process nested properties
    if ($Destination.ContainsKey("properties") -and $Destination["properties"] -is [hashtable]) {
        $properties = $Destination["properties"]
        $propertyFields = @("workspaceId", "databaseName")
        foreach ($field in $propertyFields) {
            if ($properties.ContainsKey($field) -and $ValueToTokenMap.ContainsKey($properties[$field])) {
                $originalValue = $properties[$field]
                $token = $ValueToTokenMap[$originalValue]
                $properties[$field] = $token
                if (-not $DryRun) {
                    Write-Host "  Replaced destination.properties.${field}: '$originalValue' -> $token" -ForegroundColor Green
                }
            }
        }
    }
    
    # Process inputNodes and inputSchemas for name tokenization
    Apply-EventstreamNameTokens -Object $Destination -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
}

# Function to apply tokens to eventstream stream objects
function Apply-EventstreamStreamTokens {
    param(
        [hashtable]$Stream,
        [hashtable]$ValueToTokenMap,
        [switch]$DryRun
    )
    
    # Tokenize specific fields in streams
    $tokenizableFields = @("name")
    foreach ($field in $tokenizableFields) {
        if ($Stream.ContainsKey($field) -and $ValueToTokenMap.ContainsKey($Stream[$field])) {
            $originalValue = $Stream[$field]
            $token = $ValueToTokenMap[$originalValue]
            $Stream[$field] = $token
            if (-not $DryRun) {
                Write-Host "  Replaced stream.${field}: '$originalValue' -> $token" -ForegroundColor Green
            }
        }
    }
    
    # Process inputNodes for name tokenization
    Apply-EventstreamNameTokens -Object $Stream -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
}

# Function to apply name tokenization to inputNodes and inputSchemas
function Apply-EventstreamNameTokens {
    param(
        [hashtable]$Object,
        [hashtable]$ValueToTokenMap,
        [switch]$DryRun
    )
    
    # Process inputNodes
    if ($Object.ContainsKey("inputNodes") -and $Object["inputNodes"] -is [System.Array]) {
        foreach ($inputNode in $Object["inputNodes"]) {
            if ($inputNode -is [hashtable] -and $inputNode.ContainsKey("name") -and $ValueToTokenMap.ContainsKey($inputNode["name"])) {
                $originalValue = $inputNode["name"]
                $token = $ValueToTokenMap[$originalValue]
                $inputNode["name"] = $token
                if (-not $DryRun) {
                    Write-Host "  Replaced inputNode.name: '$originalValue' -> $token" -ForegroundColor Green
                }
            }
        }
    }
    
    # Process inputSchemas
    if ($Object.ContainsKey("inputSchemas") -and $Object["inputSchemas"] -is [System.Array]) {
        foreach ($inputSchema in $Object["inputSchemas"]) {
            if ($inputSchema -is [hashtable] -and $inputSchema.ContainsKey("name") -and $ValueToTokenMap.ContainsKey($inputSchema["name"])) {
                $originalValue = $inputSchema["name"]
                $token = $ValueToTokenMap[$originalValue]
                $inputSchema["name"] = $token
                if (-not $DryRun) {
                    Write-Host "  Replaced inputSchema.name: '$originalValue' -> $token" -ForegroundColor Green
                }
            }
            
            # Process schema columns (but don't tokenize column names as they are field definitions)
            # Column names in schema definition should remain as-is since they define the data structure
        }
    }
}

# Function to apply tokens to dashboard tile objects
function Apply-DashboardTileTokens {
    param(
        [hashtable]$Tile,
        [hashtable]$ValueToTokenMap,
        [switch]$DryRun
    )
    
    # Process nested queryRef for queryId
    if ($Tile.ContainsKey("queryRef") -and $Tile["queryRef"] -is [hashtable]) {
        $queryRef = $Tile["queryRef"]
        if ($queryRef.ContainsKey("queryId") -and $ValueToTokenMap.ContainsKey($queryRef["queryId"])) {
            $originalValue = $queryRef["queryId"]
            $token = $ValueToTokenMap[$originalValue]
            $queryRef["queryId"] = $token
            if (-not $DryRun) {
                Write-Host "  Replaced tile.queryRef.queryId: '$originalValue' -> $token" -ForegroundColor Green
            }
        }
    }
}

# Function to apply tokens to activator entity objects
function Apply-ActivatorEntityTokens {
    param(
        [hashtable]$Entity,
        [hashtable]$ValueToTokenMap,
        [switch]$DryRun
    )
    
    # Check if this entity has a payload
    if ($Entity.ContainsKey("payload") -and $Entity["payload"] -is [hashtable]) {
        $payload = $Entity["payload"]
        
        # Check if this payload has definition type "Event"
        $isEventType = $false
        if ($payload.ContainsKey("definition") -and $payload["definition"] -is [hashtable]) {
            $definition = $payload["definition"]
            if ($definition.ContainsKey("type") -and $definition["type"] -eq "Event") {
                $isEventType = $true
                
                # Tokenize name field for Event definition types
                if ($payload.ContainsKey("name") -and $ValueToTokenMap.ContainsKey($payload["name"])) {
                    $originalValue = $payload["name"]
                    $token = $ValueToTokenMap[$originalValue]
                    $payload["name"] = $token
                    if (-not $DryRun) {
                        Write-Host "  Replaced activator.payload.name (Event type): '$originalValue' -> $token" -ForegroundColor Green
                    }
                }
            }
        }
        
        # Process eventstreamArtifactId in metadata (applies to all payload types, not just Events)
        if ($payload.ContainsKey("metadata") -and $payload["metadata"] -is [hashtable]) {
            $metadata = $payload["metadata"]
            if ($metadata.ContainsKey("eventstreamArtifactId") -and $ValueToTokenMap.ContainsKey($metadata["eventstreamArtifactId"])) {
                $originalValue = $metadata["eventstreamArtifactId"]
                $token = $ValueToTokenMap[$originalValue]
                $metadata["eventstreamArtifactId"] = $token
                if (-not $DryRun) {
                    Write-Host "  Replaced activator.payload.metadata.eventstreamArtifactId: '$originalValue' -> $token" -ForegroundColor Green
                }
            }
        }
        
        # Process email addresses in rule definitions (for timeSeriesView-v1 entities with Rule type)
        if ($payload.ContainsKey("definition") -and $payload["definition"] -is [hashtable]) {
            $definition = $payload["definition"]
            if ($definition.ContainsKey("type") -and $definition["type"] -eq "Rule" -and $definition.ContainsKey("instance")) {
                $instanceStr = $definition["instance"]
                if (-not [string]::IsNullOrWhiteSpace($instanceStr)) {
                    $emailsInInstance = Find-EmailsInString -InputString $instanceStr
                    foreach ($email in $emailsInInstance) {
                        if ($ValueToTokenMap.ContainsKey($email)) {
                            $token = $ValueToTokenMap[$email]
                            $definition["instance"] = $definition["instance"].Replace($email, $token)
                            if (-not $DryRun) {
                                Write-Host "    Applied email token: $email -> $token" -ForegroundColor Yellow
                            }
                        }
                    }
                }
            }
        }
        
        # Recursively process any nested arrays or objects within payload for additional Event types
        foreach ($key in $payload.Keys) {
            $value = $payload[$key]
            if ($value -is [System.Array]) {
                foreach ($item in $value) {
                    if ($item -is [hashtable]) {
                        Apply-ActivatorEntityTokens -Entity @{"payload" = $item } -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
                    }
                }
            }
            elseif ($value -is [hashtable] -and $key -ne "metadata" -and $key -ne "definition") {
                # Process nested objects that might contain Event definitions
                Apply-ActivatorEntityTokens -Entity @{"payload" = $value } -ValueToTokenMap $ValueToTokenMap -DryRun:$DryRun
            }
        }
    }
}

# Function to apply tokens to dashboard parameter objects
function Apply-DashboardParameterTokens {
    param(
        [hashtable]$Parameter,
        [hashtable]$ValueToTokenMap,
        [switch]$DryRun
    )
    
    # Process nested dataSource for queryRef
    if ($Parameter.ContainsKey("dataSource") -and $Parameter["dataSource"] -is [hashtable]) {
        $dataSource = $Parameter["dataSource"]
        if ($dataSource.ContainsKey("queryRef") -and $dataSource["queryRef"] -is [hashtable]) {
            $queryRef = $dataSource["queryRef"]
            if ($queryRef.ContainsKey("queryId") -and $ValueToTokenMap.ContainsKey($queryRef["queryId"])) {
                $originalValue = $queryRef["queryId"]
                $token = $ValueToTokenMap[$originalValue]
                $queryRef["queryId"] = $token
                if (-not $DryRun) {
                    Write-Host "  Replaced parameter.dataSource.queryRef.queryId: '$originalValue' -> $token" -ForegroundColor Green
                }
            }
        }
    }
}

# Function to apply tokens to dashboard data source objects
function Apply-DashboardDataSourceTokens {
    param(
        [hashtable]$DataSource,
        [hashtable]$ValueToTokenMap,
        [switch]$DryRun
    )
    
    # Tokenize specific fields in dataSources
    $tokenizableFields = @("clusterUri", "workspace", "database")
    foreach ($field in $tokenizableFields) {
        if ($DataSource.ContainsKey($field) -and $ValueToTokenMap.ContainsKey($DataSource[$field])) {
            $originalValue = $DataSource[$field]
            $token = $ValueToTokenMap[$originalValue]
            $DataSource[$field] = $token
            if (-not $DryRun) {
                Write-Host "  Replaced dataSource.${field}: '$originalValue' -> $token" -ForegroundColor Green
            }
        }
    }
}

# Function to apply tokens to dashboard page objects
function Apply-DashboardPageTokens {
    param(
        [hashtable]$Page,
        [hashtable]$ValueToTokenMap,
        [switch]$DryRun
    )
    
    # No id tokenization for pages
}

# Function to apply tokens to dashboard query objects
function Apply-DashboardQueryTokens {
    param(
        [hashtable]$Query,
        [hashtable]$ValueToTokenMap,
        [switch]$DryRun
    )
    
    # Process nested dataSource for dataSourceId
    if ($Query.ContainsKey("dataSource") -and $Query["dataSource"] -is [hashtable]) {
        $dataSource = $Query["dataSource"]
        if ($dataSource.ContainsKey("dataSourceId") -and $ValueToTokenMap.ContainsKey($dataSource["dataSourceId"])) {
            $originalValue = $dataSource["dataSourceId"]
            $token = $ValueToTokenMap[$originalValue]
            $dataSource["dataSourceId"] = $token
            if (-not $DryRun) {
                Write-Host "  Replaced query.dataSource.dataSourceId: '$originalValue' -> $token" -ForegroundColor Green
            }
        }
    }
}

# Function to discover tokens for eventstream schema specifically
function Find-EventstreamTokenizableValues {
    param(
        [object]$JsonObject,
        [hashtable]$ValueToTokenMap,
        [hashtable]$TokenMap,
        [hashtable]$KeyCounters
    )
    
    # Only tokenize specific fields in eventstream, avoiding column definitions
    $tokenizableFields = @("name", "workspaceId", "databaseName")
    
    if ($JsonObject.ContainsKey("sources") -and $JsonObject["sources"] -is [System.Array]) {
        foreach ($source in $JsonObject["sources"]) {
            # Tokenize source name only
            if ($source.ContainsKey("name") -and $source["name"]) {
                Add-TokenMapping -Key "name" -Value $source["name"] -ValueToTokenMap $ValueToTokenMap -TokenMap $TokenMap -KeyCounters $KeyCounters
            }
            # Do not tokenize dataConnectionId anymore
        }
    }
    
    if ($JsonObject.ContainsKey("destinations") -and $JsonObject["destinations"] -is [System.Array]) {
        foreach ($destination in $JsonObject["destinations"]) {
            # Tokenize destination name
            if ($destination.ContainsKey("name") -and $destination["name"]) {
                Add-TokenMapping -Key "name" -Value $destination["name"] -ValueToTokenMap $ValueToTokenMap -TokenMap $TokenMap -KeyCounters $KeyCounters
            }
            # Check properties for workspaceId, databaseName (not itemId anymore)
            if ($destination.ContainsKey("properties")) {
                $props = $destination["properties"]
                foreach ($field in @("workspaceId", "databaseName")) {
                    if ($props.ContainsKey($field) -and $props[$field]) {
                        Add-TokenMapping -Key $field -Value $props[$field] -ValueToTokenMap $ValueToTokenMap -TokenMap $TokenMap -KeyCounters $KeyCounters
                    }
                }
            }
            # Tokenize inputNode names (stream references, not column names)
            if ($destination.ContainsKey("inputNodes") -and $destination["inputNodes"] -is [System.Array]) {
                foreach ($inputNode in $destination["inputNodes"]) {
                    if ($inputNode.ContainsKey("name") -and $inputNode["name"]) {
                        Add-TokenMapping -Key "name" -Value $inputNode["name"] -ValueToTokenMap $ValueToTokenMap -TokenMap $TokenMap -KeyCounters $KeyCounters
                    }
                }
            }
            # Tokenize inputSchema names (stream references, not column names)
            if ($destination.ContainsKey("inputSchemas") -and $destination["inputSchemas"] -is [System.Array]) {
                foreach ($inputSchema in $destination["inputSchemas"]) {
                    if ($inputSchema.ContainsKey("name") -and $inputSchema["name"]) {
                        Add-TokenMapping -Key "name" -Value $inputSchema["name"] -ValueToTokenMap $ValueToTokenMap -TokenMap $TokenMap -KeyCounters $KeyCounters
                    }
                    # Do NOT tokenize column names in schema.columns - they are field definitions
                }
            }
        }
    }
    
    if ($JsonObject.ContainsKey("streams") -and $JsonObject["streams"] -is [System.Array]) {
        foreach ($stream in $JsonObject["streams"]) {
            # Tokenize stream name
            if ($stream.ContainsKey("name") -and $stream["name"]) {
                Add-TokenMapping -Key "name" -Value $stream["name"] -ValueToTokenMap $ValueToTokenMap -TokenMap $TokenMap -KeyCounters $KeyCounters
            }
            # Tokenize inputNode names (source references)
            if ($stream.ContainsKey("inputNodes") -and $stream["inputNodes"] -is [System.Array]) {
                foreach ($inputNode in $stream["inputNodes"]) {
                    if ($inputNode.ContainsKey("name") -and $inputNode["name"]) {
                        Add-TokenMapping -Key "name" -Value $inputNode["name"] -ValueToTokenMap $ValueToTokenMap -TokenMap $TokenMap -KeyCounters $KeyCounters
                    }
                }
            }
        }
    }
}

# Helper function to add token mapping
function Add-TokenMapping {
    param(
        [string]$Key,
        [string]$Value,
        [hashtable]$ValueToTokenMap,
        [hashtable]$TokenMap,
        [hashtable]$KeyCounters
    )
    
    if (-not [string]::IsNullOrWhiteSpace($Value) -and -not $ValueToTokenMap.ContainsKey($Value)) {
        # Increment counter for this key type
        if (-not $KeyCounters.ContainsKey($Key)) {
            $KeyCounters[$Key] = 0
        }
        $KeyCounters[$Key]++
        $occurrence = $KeyCounters[$Key]
        
        # Create token with format: __TOKEN_[key_name]_[occurrence]__
        $token = "__TOKEN_${Key}_${occurrence}__"
        
        $TokenMap[$token] = $Value
        $ValueToTokenMap[$Value] = $token
        
        if (-not $DryRun) {
            Write-Host "  Tokenized: $Key = '$Value' -> $token" -ForegroundColor Yellow
        }
    }
}

# Function to discover tokens for platform schema specifically
function Find-PlatformTokenizableValues {
    param(
        [object]$JsonObject,
        [hashtable]$ValueToTokenMap,
        [hashtable]$TokenMap,
        [hashtable]$KeyCounters
    )
    
    # Only tokenize displayName and description in metadata section
    if ($JsonObject.ContainsKey("metadata") -and $JsonObject["metadata"] -is [System.Collections.IDictionary]) {
        $metadata = $JsonObject["metadata"]
        foreach ($field in @("displayName", "description")) {
            if ($metadata.ContainsKey($field) -and $metadata[$field]) {
                # Always create a separate token for each field, even if values are identical
                $value = $metadata[$field]
                $key = $field
                
                # Increment counter for this key type
                if (-not $KeyCounters.ContainsKey($key)) {
                    $KeyCounters[$key] = 0
                }
                $KeyCounters[$key]++
                $occurrence = $KeyCounters[$key]
                
                # Create token with format: __TOKEN_[key_name]_[occurrence]__
                $token = "__TOKEN_${key}_${occurrence}__"
                
                $TokenMap[$token] = $value
                # Don't use ValueToTokenMap for platform fields to avoid collision
                
                if (-not $DryRun) {
                    Write-Host "  Tokenized: $key = '$value' -> $token" -ForegroundColor Yellow
                }
            }
        }
    }
}

function Find-TokenizableValues {
    param(
        [object]$JsonObject,
        [string[]]$TokenizableFields,
        [hashtable]$ValueToTokenMap,
        [hashtable]$TokenMap,
        [hashtable]$KeyCounters,
        [string]$Path = ""
    )
    
    if ($JsonObject -is [System.Collections.IDictionary]) {
        foreach ($key in $JsonObject.Keys) {
            $value = $JsonObject[$key]
            $currentPath = if ($Path) { "$Path.$key" } else { $key }
            
            # Check if this key should be tokenized
            if (Should-Tokenize -Key $key -Value $value -TokenizableFields $TokenizableFields) {
                # Special handling for Activator schema name field
                if ($SchemaType -eq "reflexentities" -and $key.ToLower() -eq "name") {
                    # Only tokenize name if it's in a payload with definition type "Event"
                    $shouldTokenizeName = $false
                    
                    # Check if we're in a payload context (handles nested structures)
                    if ($Path -match "payload$" -and $JsonObject -is [System.Collections.IDictionary]) {
                        # Direct payload context - check if this payload has Event definition type
                        if ($JsonObject.ContainsKey("definition") -and $JsonObject["definition"] -is [System.Collections.IDictionary]) {
                            $definition = $JsonObject["definition"]
                            if ($definition.ContainsKey("type") -and $definition["type"] -eq "Event") {
                                $shouldTokenizeName = $true
                            }
                        }
                    }
                    elseif ($Path -match "\.payload$" -and $JsonObject -is [System.Collections.IDictionary]) {
                        # Nested payload context (e.g., "entities[0].payload") - check parent payload
                        if ($JsonObject.ContainsKey("definition") -and $JsonObject["definition"] -is [System.Collections.IDictionary]) {
                            $definition = $JsonObject["definition"]
                            if ($definition.ContainsKey("type") -and $definition["type"] -eq "Event") {
                                $shouldTokenizeName = $true
                            }
                        }
                    }
                    
                    if (-not $shouldTokenizeName) {
                        # Skip tokenizing this name - continue processing nested structures
                        Find-TokenizableValues -JsonObject $value -TokenizableFields $TokenizableFields -ValueToTokenMap $ValueToTokenMap -TokenMap $TokenMap -KeyCounters $KeyCounters -Path $currentPath
                        continue
                    }
                }
                
                if (-not $ValueToTokenMap.ContainsKey($value)) {
                    # Increment counter for this key type
                    if (-not $KeyCounters.ContainsKey($key)) {
                        $KeyCounters[$key] = 0
                    }
                    $KeyCounters[$key]++
                    $occurrence = $KeyCounters[$key]
                    
                    # Create token with new format: __TOKEN_[key_name]_[occurrence]__
                    $token = "__TOKEN_${key}_${occurrence}__"
                    
                    $TokenMap[$token] = $value
                    $ValueToTokenMap[$value] = $token
                    
                    if (-not $DryRun) {
                        Write-Host "  Tokenized: $key = '$value' -> $token" -ForegroundColor Yellow
                    }
                }
                else {
                    if (-not $DryRun) {
                        Write-Host "  Reusing token: $key = '$value' -> $($ValueToTokenMap[$value])" -ForegroundColor Cyan
                    }
                }
            }
            # Special handling for email addresses in string values (for reflexentities schema)
            elseif ($value -is [string] -and $TokenizableFields -contains "email") {
                $emailsInValue = Find-EmailsInString -InputString $value
                foreach ($email in $emailsInValue) {
                    if (-not $ValueToTokenMap.ContainsKey($email)) {
                        # Increment counter for email type
                        if (-not $KeyCounters.ContainsKey("email")) {
                            $KeyCounters["email"] = 0
                        }
                        $KeyCounters["email"]++
                        $occurrence = $KeyCounters["email"]
                        
                        # Create token with format: __TOKEN_email_[occurrence]__
                        $token = "__TOKEN_email_${occurrence}__"
                        
                        $TokenMap[$token] = $email
                        $ValueToTokenMap[$email] = $token
                        
                        if (-not $DryRun) {
                            Write-Host "  Tokenized email: '$email' -> $token" -ForegroundColor Yellow
                        }
                    }
                }
            }
            
            # Recursively process nested objects/arrays
            Find-TokenizableValues -JsonObject $value -TokenizableFields $TokenizableFields -ValueToTokenMap $ValueToTokenMap -TokenMap $TokenMap -KeyCounters $KeyCounters -Path $currentPath
        }
    }
    elseif ($JsonObject -is [System.Array]) {
        for ($i = 0; $i -lt $JsonObject.Length; $i++) {
            $currentPath = "$Path[$i]"
            Find-TokenizableValues -JsonObject $JsonObject[$i] -TokenizableFields $TokenizableFields -ValueToTokenMap $ValueToTokenMap -TokenMap $TokenMap -KeyCounters $KeyCounters -Path $currentPath
        }
    }
}

# Function to process JSON using structure-aware replacement
function Process-JsonString {
    param(
        [string]$JsonString,
        [hashtable]$TokenMap,
        [string]$SchemaType,
        [bool]$DryRun = $false
    )
    
    $processedJson = $JsonString
    $tokenCounter = 0
    
    # Get tokenizable fields for this schema type
    $tokenizableFields = Get-TokenizableFields -SchemaType $SchemaType
    
    # Create hashtables to track value-to-token mappings and key occurrence counters
    $valueToTokenMap = @{}
    $keyCounters = @{}
    
    try {
        # Parse JSON to navigate structure
        $jsonObject = $JsonString | ConvertFrom-Json -AsHashtable
        
        # Use schema-specific token discovery
        if ($SchemaType -eq "eventstream") {
            Find-EventstreamTokenizableValues -JsonObject $jsonObject -ValueToTokenMap $valueToTokenMap -TokenMap $TokenMap -KeyCounters $keyCounters
        }
        elseif ($SchemaType -eq "platform") {
            # For .platform files, only find displayName and description in metadata
            Find-PlatformTokenizableValues -JsonObject $jsonObject -ValueToTokenMap $valueToTokenMap -TokenMap $TokenMap -KeyCounters $keyCounters
        }
        else {
            # Find all tokenizable values in the JSON structure for other schemas
            Find-TokenizableValues -JsonObject $jsonObject -TokenizableFields $tokenizableFields -ValueToTokenMap $valueToTokenMap -TokenMap $TokenMap -KeyCounters $keyCounters
        }
        
        $tokenCounter = $valueToTokenMap.Count
        
        # Apply schema-driven replacement directly to the JSON object
        Apply-SchemaTokenReplacement -JsonObject $jsonObject -ValueToTokenMap $valueToTokenMap -SchemaType $SchemaType -DryRun:$DryRun
        
        # Convert the modified JSON object back to string
        $processedJson = $jsonObject | ConvertTo-Json -Depth 100 -Compress:$false
        
        # Additional string-based replacement to ensure all tokens are applied
        foreach ($value in $valueToTokenMap.Keys) {
            $token = $valueToTokenMap[$value]
            
            # For email addresses, use comprehensive string replacement to handle all escaping patterns
            if ($value -match '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$') {
                # 1. Direct string replacement for emails in JSON (normal case)
                $processedJson = $processedJson.Replace('"' + $value + '"', '"' + $token + '"')
                
                # 2. Handle single-escaped JSON strings (like \"email@domain.com\")
                $processedJson = $processedJson.Replace('\"' + $value + '\"', '\"' + $token + '\"')
                
                # 3. Handle emails within any context - comprehensive replacement
                $processedJson = $processedJson.Replace($value, $token)
            }
            else {
                # Use regex escaping for non-email values
                $escapedValue = [regex]::Escape($value)
                
                # Replace quoted values in JSON
                $quotedPattern = '"' + $escapedValue + '"'
                $quotedReplacement = '"' + $token + '"'
                $processedJson = $processedJson -replace $quotedPattern, $quotedReplacement
                
                # Replace values within escaped JSON strings (for nested JSON)
                $escapedJsonPattern = '\\"' + $escapedValue + '\\"'
                $escapedJsonReplacement = '\\"' + $token + '\\"'
                $processedJson = $processedJson -replace $escapedJsonPattern, $escapedJsonReplacement
            }
            
            if (-not $DryRun) {
                Write-Host "  Replaced: '$value' -> $token" -ForegroundColor Green
            }
        }
    }
    catch {
        Write-Warning "Failed to parse JSON structure, falling back to regex patterns for schema: $SchemaType"
        
        # Fallback to regex-based processing for malformed JSON
        if ($SchemaType -eq "reflexentities") {
            # Parse JSON to find Event definition type names and eventstreamArtifactId values
            try {
                $jsonObj = $JsonString | ConvertFrom-Json
                foreach ($entity in $jsonObj) {
                    # Handle eventstreamArtifactId
                    if ($entity.payload -and $entity.payload.metadata -and $entity.payload.metadata.eventstreamArtifactId) {
                        $value = $entity.payload.metadata.eventstreamArtifactId
                        if (-not $valueToTokenMap.ContainsKey($value)) {
                            $key = "eventstreamArtifactId"
                            if (-not $keyCounters.ContainsKey($key)) {
                                $keyCounters[$key] = 0
                            }
                            $keyCounters[$key]++
                            $occurrence = $keyCounters[$key]
                            $token = "__TOKEN_${key}_${occurrence}__"
                            $TokenMap[$token] = $value
                            $valueToTokenMap[$value] = $token
                            $tokenCounter++
                        }
                    }
                    
                    # Handle name for Event definition types only - supports multiple Event entities
                    if ($entity.payload -and $entity.payload.definition -and $entity.payload.definition.type -eq "Event" -and $entity.payload.name) {
                        $value = $entity.payload.name
                        if (-not $valueToTokenMap.ContainsKey($value)) {
                            $key = "name"
                            if (-not $keyCounters.ContainsKey($key)) {
                                $keyCounters[$key] = 0
                            }
                            $keyCounters[$key]++
                            $occurrence = $keyCounters[$key]
                            $token = "__TOKEN_${key}_${occurrence}__"
                            $TokenMap[$token] = $value
                            $valueToTokenMap[$value] = $token
                            $tokenCounter++
                        }
                    }
                    
                    # Recursively process nested arrays or objects for additional Event entities
                    function ProcessNestedEventEntities($obj, $path = "") {
                        if ($obj -is [System.Array]) {
                            for ($i = 0; $i -lt $obj.Length; $i++) {
                                ProcessNestedEventEntities -obj $obj[$i] -path "$path[$i]"
                            }
                        }
                        elseif ($obj -is [PSCustomObject] -or $obj -is [System.Collections.Hashtable]) {
                            if ($obj.payload -and $obj.payload.definition -and $obj.payload.definition.type -eq "Event" -and $obj.payload.name) {
                                $value = $obj.payload.name
                                if (-not $valueToTokenMap.ContainsKey($value)) {
                                    $key = "name"
                                    if (-not $keyCounters.ContainsKey($key)) {
                                        $keyCounters[$key] = 0
                                    }
                                    $keyCounters[$key]++
                                    $occurrence = $keyCounters[$key]
                                    $token = "__TOKEN_${key}_${occurrence}__"
                                    $TokenMap[$token] = $value
                                    $valueToTokenMap[$value] = $token
                                    $tokenCounter++
                                }
                            }
                            
                            # Process nested properties
                            foreach ($prop in $obj.PSObject.Properties) {
                                if ($prop.Value -and ($prop.Value -is [System.Array] -or $prop.Value -is [PSCustomObject] -or $prop.Value -is [System.Collections.Hashtable])) {
                                    ProcessNestedEventEntities -obj $prop.Value -path "$path.$($prop.Name)"
                                }
                            }
                        }
                    }
                    
                    # Process the current entity for nested Event entities
                    ProcessNestedEventEntities -obj $entity
                }
            }
            catch {
                # Fallback to regex for eventstreamArtifactId if JSON parsing fails
                $eventstreamIdPattern = '"eventstreamArtifactId"\s*:\s*"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"'
                $matches = [regex]::Matches($JsonString, $eventstreamIdPattern)
                
                foreach ($match in $matches) {
                    $value = $match.Groups[1].Value
                    if (-not $valueToTokenMap.ContainsKey($value)) {
                        $key = "eventstreamArtifactId"
                        if (-not $keyCounters.ContainsKey($key)) {
                            $keyCounters[$key] = 0
                        }
                        $keyCounters[$key]++
                        $occurrence = $keyCounters[$key]
                        $token = "__TOKEN_${key}_${occurrence}__"
                        $TokenMap[$token] = $value
                        $valueToTokenMap[$value] = $token
                        $tokenCounter++
                    }
                }
            }
        }
        
        # Apply replacements for all schemas
        foreach ($value in $valueToTokenMap.Keys) {
            $token = $valueToTokenMap[$value]
            $escapedValue = [regex]::Escape($value)
            
            # First, replace values in JSON value positions (after colons)
            $valuePattern = '(:\s*)"' + $escapedValue + '"'
            $valueReplacement = '${1}"' + $token + '"'
            $processedJson = $processedJson -replace $valuePattern, $valueReplacement
            
            # Then, perform comprehensive replacement of any remaining occurrences
            # Pattern 1: Regular quoted values
            $globalValuePattern = '"' + $escapedValue + '"'
            $globalReplacement = '"' + $token + '"'
            $processedJson = $processedJson -replace $globalValuePattern, $globalReplacement
            
            # Pattern 2: Values within escaped JSON strings
            $escapedJsonPattern = '\\"' + $escapedValue + '\\"'
            $escapedJsonReplacement = '\\"' + $token + '\\"'
            $processedJson = $processedJson -replace $escapedJsonPattern, $escapedJsonReplacement
        }
    }
    
    return @{
        ProcessedJson = $processedJson
        TokenCount    = $tokenCounter
    }
}

# Main execution
try {
    Write-Host "🔧 JSON Tokenizer Script" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Cyan
    
    # Determine file path based on schema type or use provided path
    if (-not $JsonFilePath) {
        $filePaths = Get-SchemaFilePath -SchemaType $SchemaType
        Write-Host "📁 Detected file paths for schema '$SchemaType':" -ForegroundColor Blue
        foreach ($fp in $filePaths) {
            $exists = Test-Path $fp
            $status = if ($exists) { "✅ EXISTS" } else { "❌ MISSING" }
            Write-Host "  - $fp ($status)" -ForegroundColor $(if ($exists) { "Green" } else { "Red" })
        }
        
        if ($filePaths -is [array]) {
            # Handle multiple files (like RealTimeDashboard scenario)
            $processedFiles = New-Object System.Collections.ArrayList
            foreach ($filePath in $filePaths) {
                if (Test-Path $filePath) {
                    [void]$processedFiles.Add($filePath)
                }
            }
        }
        else {
            if (-not (Test-Path $filePaths)) {
                throw "File not found: $filePaths"
            }
            $processedFiles = New-Object System.Collections.ArrayList
            [void]$processedFiles.Add($filePaths)
        }
    }
    else {
        # Handle explicit file path parameter
        $processedFiles = New-Object System.Collections.ArrayList
        [void]$processedFiles.Add($JsonFilePath)
    }
    
    # Display initial information
    Write-Host "Schema type: $SchemaType" -ForegroundColor Green
    
    # Display files
    if ($processedFiles.Count -gt 1) {
        Write-Host "Input files: $($processedFiles.Count) files" -ForegroundColor Green
        for ($i = 0; $i -lt $processedFiles.Count; $i++) {
            Write-Host "  - $($processedFiles[$i])" -ForegroundColor Gray
        }
    }
    else {
        Write-Host "Input file: $($processedFiles[0])" -ForegroundColor Green
    }
    if ($DryRun) {
        Write-Host "Mode: DRY RUN (no files will be modified)" -ForegroundColor Magenta
    }
    Write-Host ""
    
    # Get normalized schema type for processing
    $normalizedSchemaType = Get-NormalizedSchemaType -SchemaType $SchemaType
    Write-Host "📋 Processing schema: $normalizedSchemaType" -ForegroundColor Blue
    Write-Host ""
    
    # Process each file
    $totalTokenCount = 0
    $allTokenMaps = @{}
    
    Write-Host "🔄 Processing $($processedFiles.Count) files..." -ForegroundColor Blue
    
    for ($i = 0; $i -lt $processedFiles.Count; $i++) {
        $currentFilePath = $processedFiles[$i]
        # Validate input file
        if (-not (Test-Path $currentFilePath)) {
            Write-Warning "File not found: $currentFilePath (skipping)"
            continue
        }
        
        # Determine output path for current file
        if (-not $OutputPath) {
            $currentOutputPath = $currentFilePath
        }
        else {
            $currentOutputPath = $OutputPath
        }
        
        Write-Host "Processing file: $currentFilePath" -ForegroundColor Yellow
        
        # Load JSON content as string
        Write-Host "📄 Loading JSON content from: $currentFilePath" -ForegroundColor Blue
        $jsonContent = Get-Content -Path $currentFilePath -Raw -Encoding UTF8
        
        # Process the JSON string and collect tokens
        $tokenMap = @{}
        Write-Host "🔄 Processing JSON and creating tokens for: $(Split-Path $currentFilePath -Leaf)" -ForegroundColor Blue
        
        # Determine schema type for current file
        $currentSchemaType = $normalizedSchemaType
        if ($currentFilePath.EndsWith(".platform")) {
            $currentSchemaType = "platform"
        }
        
        $result = Process-JsonString -JsonString $jsonContent -TokenMap $tokenMap -SchemaType $currentSchemaType -DryRun $DryRun.IsPresent
        
        # Accumulate results
        $totalTokenCount += $result.TokenCount
        foreach ($token in $tokenMap.Keys) {
            $allTokenMaps[$token] = $tokenMap[$token]
        }
        
        # Save tokenized JSON for current file
        if (-not $DryRun) {
            Write-Host "💾 Saving tokenized JSON to: $currentOutputPath" -ForegroundColor Blue
            Set-Content -Path $currentOutputPath -Value $result.ProcessedJson -Encoding UTF8 -NoNewline
            Write-Host "✅ Tokenized JSON saved to: $currentOutputPath" -ForegroundColor Green
        }
        
        Write-Host "" # Add spacing between files
    }
    
    # Display results
    Write-Host "📊 Tokenization Results:" -ForegroundColor Cyan
    Write-Host "  Total tokens created: $totalTokenCount" -ForegroundColor Green
    
    if ($allTokenMaps.Count -gt 0) {
        Write-Host ""
        Write-Host "🎯 Token Map:" -ForegroundColor Cyan
        $allTokenMaps.GetEnumerator() | Sort-Object Key | ForEach-Object {
            Write-Host "  $($_.Key) = '$($_.Value)'" -ForegroundColor Gray
        }
    }
    
    # Create token mapping file only if requested
    if ($SaveTokenMap -and -not $DryRun) {
        $mappingPath = if ($OutputPath) { $OutputPath -replace '\.json$', '_token_map.json' } else { "token_map.json" }
        $allTokenMaps | ConvertTo-Json | Set-Content -Path $mappingPath -Encoding UTF8
        Write-Host "📋 Token mapping saved to: $mappingPath" -ForegroundColor Green
    }
    
    if ($DryRun) {
        Write-Host ""
        Write-Host "🔍 DRY RUN: No files were modified" -ForegroundColor Magenta
    }
    
    Write-Host ""
    Write-Host "🎉 JSON tokenization completed successfully!" -ForegroundColor Green
}
catch {
    Write-Error "❌ Error during JSON tokenization: $($_.Exception.Message)"
    exit 1
}