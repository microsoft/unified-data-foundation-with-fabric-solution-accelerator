#!/bin/bash

#
# provision_fabric_items.sh
#
# SYNOPSIS
#     Deploys Microsoft Fabric items (lakehouses, notebooks, folders, reports) to a Fabric workspace.
#
# DESCRIPTION
#     This script automates the deployment of UDFF (Unified Data Foundation with Fabric) components 
#     to Microsoft Fabric including folder structure, lakehouses, sample data, notebooks, and Power BI reports.
#
# USAGE
#     ./provision_fabric_items.sh <fabric-workspace-id>
#
# EXAMPLE
#     ./provision_fabric_items.sh "12345678-1234-1234-1234-123456789abc"
#
# PREREQUISITES
#     - Azure CLI installed and authenticated (az login)
#     - Python 3.9+ with pip
#     - Appropriate permissions in the Fabric workspace
#

# Set strict error handling
set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Functions for colored output
print_info() {
    echo -e "${CYAN}$1${NC}"
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

print_step() {
    echo -e "${YELLOW}$1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate GUID format
validate_guid() {
    local guid="$1"
    if [[ ! $guid =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
        print_warning "The provided workspace ID doesn't appear to be a valid GUID format. Proceeding anyway..."
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <fabric-workspace-id>"
    echo ""
    echo "Arguments:"
    echo "  fabric-workspace-id    The ID of the Microsoft Fabric workspace where items will be deployed"
    echo ""
    echo "Example:"
    echo "  $0 \"12345678-1234-1234-1234-123456789abc\""
    echo ""
    echo "Prerequisites:"
    echo "  - Azure CLI installed and authenticated (az login)"
    echo "  - Python 3.9+ with pip"
    echo "  - Appropriate permissions in the Fabric workspace"
}

# Main script starts here
print_success "Starting Microsoft Fabric deployment script..."

# Check if workspace ID parameter is provided
if [ $# -eq 0 ]; then
    print_error "❌ Error: Fabric workspace ID is required"
    echo ""
    show_usage
    exit 1
fi

fabricWorkspaceId="$1"
print_info "Fabric Workspace ID: $fabricWorkspaceId"

# Validate workspace ID format
validate_guid "$fabricWorkspaceId"

# Validate that Python is available
print_step "Checking Python installation..."
if ! command_exists python && ! command_exists python3; then
    print_error "❌ Python is not installed or not available in PATH. Please install Python 3.9+ and try again."
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python"
if command_exists python3; then
    PYTHON_CMD="python3"
fi

# Check Python version
python_version=$($PYTHON_CMD --version 2>&1)
print_success "Found: $python_version"

# Validate that pip is available
print_step "Checking pip installation..."
if ! command_exists pip && ! command_exists pip3; then
    print_error "❌ pip is not available. Please ensure pip is installed and try again."
    exit 1
fi

# Use pip3 if available, otherwise pip
PIP_CMD="pip"
if command_exists pip3; then
    PIP_CMD="pip3"
fi

print_success "pip is available"

# Install Python dependencies
print_step "Installing Python dependencies from requirements.txt..."
if ! $PIP_CMD install -r requirements.txt --quiet; then
    print_error "❌ Failed to install Python dependencies. Please check requirements.txt and try again."
    exit 1
fi
print_success "Dependencies installed successfully"

# Run the Python deployment script
print_step "Starting Fabric items deployment..."
print_info "This may take several minutes to complete..."
echo ""

# Run Python unbuffered so prints show immediately
if $PYTHON_CMD -u create_fabric_items.py --workspaceId "$fabricWorkspaceId"; then
    echo ""
    print_success "✅ Fabric deployment completed successfully!"
    echo ""
    print_info "Next steps:"
    echo -e "${WHITE}1. Open your Microsoft Fabric workspace${NC}"
    echo -e "${WHITE}2. Verify that lakehouses (udff_bronze, udff_silver, udff_gold) have been created${NC}"
    echo -e "${WHITE}3. Check that notebooks are organized in the correct folder structure${NC}"
    echo -e "${WHITE}4. Explore the sample data in the bronze lakehouse${NC}"
    echo -e "${WHITE}5. Review any deployed Power BI reports in the reports folder${NC}"
else
    exit_code=$?
    print_error "❌ Deployment failed with exit code: $exit_code"
    echo ""
    print_warning "Troubleshooting tips:"
    echo -e "${WHITE}1. Ensure you are logged in to Azure CLI: az login${NC}"
    echo -e "${WHITE}2. Verify you have permissions in the Fabric workspace${NC}"
    echo -e "${WHITE}3. Check that the workspace ID is correct and accessible${NC}"
    echo -e "${WHITE}4. Ensure Python 3.9+ and pip are properly installed${NC}"
    echo -e "${WHITE}5. Check your internet connection and Fabric API access${NC}"
    exit 1
fi