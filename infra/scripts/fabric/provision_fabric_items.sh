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
#     ./provision_fabric_items.sh [options]
#
# OPTIONS
#     -c, --capacity-name <name>     Microsoft Fabric capacity name (optional, will use AZURE_FABRIC_CAPACITY_NAME env var if not provided)
#     -w, --workspace-name <name>    Microsoft Fabric workspace name (optional, will use AZURE_FABRIC_WORKSPACE_NAME env var if not provided)
#     -h, --help                     Show this help message
#
# EXAMPLES
#     ./provision_fabric_items.sh -c "MyCapacity" -w "UDFF-Workspace"
#     ./provision_fabric_items.sh -c "MyCapacity"
#     export AZURE_FABRIC_CAPACITY_NAME="MyCapacity" && ./provision_fabric_items.sh
#     export AZURE_FABRIC_CAPACITY_NAME="MyCapacity" AZURE_FABRIC_WORKSPACE_NAME="MyWorkspace" && ./provision_fabric_items.sh
#
# PREREQUISITES
#     - Azure CLI installed and authenticated (az login)
#     - Python 3.9+ with pip
#     - Appropriate permissions in the Fabric capacity and workspace
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

# Function to show usage
show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -c, --capacity-name <name>     Microsoft Fabric capacity name (optional, will use AZURE_FABRIC_CAPACITY_NAME env var if not provided)"
    echo "  -w, --workspace-name <name>    Microsoft Fabric workspace name (optional, will use AZURE_FABRIC_WORKSPACE_NAME env var if not provided)"
    echo "  -h, --help                     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -c \"MyCapacity\" -w \"UDFF-Workspace\""
    echo "  $0 -c \"MyCapacity\""
    echo "  export AZURE_FABRIC_CAPACITY_NAME=\"MyCapacity\" && $0"
    echo "  export AZURE_FABRIC_CAPACITY_NAME=\"MyCapacity\" AZURE_FABRIC_WORKSPACE_NAME=\"MyWorkspace\" && $0"
    echo ""
    echo "Prerequisites:"
    echo "  - Azure CLI installed and authenticated (az login)"
    echo "  - Python 3.9+ with pip"
    echo "  - Appropriate permissions in the Fabric capacity and workspace"
}

# Main script starts here
print_success "Starting Microsoft Fabric deployment script..."

# Get script directory for relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS_PATH="$SCRIPT_DIR/requirements.txt"

# Initialize variables
fabricCapacityName=""
fabricWorkspaceName=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--capacity-name)
            fabricCapacityName="$2"
            shift 2
            ;;
        -w|--workspace-name)
            fabricWorkspaceName="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "❌ Unknown option: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
done

# Validate parameters
if [[ -z "$fabricCapacityName" ]]; then
    # Check if environment variable exists
    if [[ -n "${AZURE_FABRIC_CAPACITY_NAME:-}" ]]; then
        fabricCapacityName="$AZURE_FABRIC_CAPACITY_NAME"
        print_info "Using Fabric capacity name from environment variable: $fabricCapacityName"
    else
        print_error "❌ Error: Capacity name is required"
        echo ""
        print_info "Please provide the capacity name either:"
        echo -e "${WHITE}1. As a parameter: -c 'MyCapacity'${NC}"
        echo -e "${WHITE}2. Set the AZURE_FABRIC_CAPACITY_NAME environment variable${NC}"
        echo ""
        print_info "Usage examples:"
        echo -e "${WHITE}  $0 -c 'MyCapacity' -w 'MyWorkspace'${NC}"
        echo -e "${WHITE}  $0 -c 'MyCapacity'${NC}"
        echo -e "${WHITE}  export AZURE_FABRIC_CAPACITY_NAME='MyCapacity' && $0${NC}"
        exit 1
    fi
fi

# Check if workspace name is provided, otherwise use environment variable
if [[ -z "$fabricWorkspaceName" ]]; then
    if [[ -n "${AZURE_FABRIC_WORKSPACE_NAME:-}" ]]; then
        fabricWorkspaceName="$AZURE_FABRIC_WORKSPACE_NAME"
        print_info "Using Fabric workspace name from environment variable: $fabricWorkspaceName"
    fi
fi

print_info "Fabric Capacity Name: $fabricCapacityName"
if [[ -n "$fabricWorkspaceName" ]]; then
    print_info "Fabric Workspace Name: $fabricWorkspaceName"
    print_warning "Mode: Create/use workspace with specified name"
else
    print_warning "Mode: Create workspace with auto-generated name"
fi

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
if [[ ! -f "$REQUIREMENTS_PATH" ]]; then
    print_error "❌ requirements.txt not found at: $REQUIREMENTS_PATH"
    exit 1
fi
if ! $PIP_CMD install -r "$REQUIREMENTS_PATH" --quiet; then
    print_error "❌ Failed to install Python dependencies. Please check requirements.txt and try again."
    exit 1
fi
print_success "Dependencies installed successfully"

# Change to script directory for Python execution
cd "$SCRIPT_DIR"

# Run the Python deployment script
print_step "Starting Fabric items deployment..."
print_info "This may take several minutes to complete..."
echo ""

# Build command arguments
python_args=(--capacityName "$fabricCapacityName")
if [[ -n "$fabricWorkspaceName" ]]; then
    python_args+=(--workspaceName "$fabricWorkspaceName")
fi

# Run Python unbuffered so prints show immediately
if $PYTHON_CMD -u create_fabric_items.py "${python_args[@]}"; then
    echo ""
    print_success "✅ Fabric deployment completed successfully!"
    echo ""
    print_info "Next steps:"
    echo -e "${WHITE}1. Open your Microsoft Fabric workspace${NC}"
    echo -e "${WHITE}2. Verify that lakehouses (maag_bronze, maag_silver, maag_gold) have been created${NC}"
    echo -e "${WHITE}3. Check that notebooks are organized in the correct folder structure${NC}"
    echo -e "${WHITE}4. Explore the sample data in the bronze lakehouse${NC}"
    echo -e "${WHITE}5. Review any deployed Power BI reports in the reports folder${NC}"
    echo -e "${WHITE}6. Note the workspace ID for future deployments${NC}"
else
    exit_code=$?
    print_error "❌ Deployment failed with exit code: $exit_code"
    echo ""
    print_warning "Troubleshooting tips:"
    echo -e "${WHITE}1. Ensure you are logged in to Azure CLI: az login${NC}"
    echo -e "${WHITE}2. Verify you have permissions in the Fabric capacity and workspace${NC}"
    echo -e "${WHITE}3. Check that the capacity name is correct and accessible${NC}"
    echo -e "${WHITE}4. Ensure Python 3.9+ and pip are properly installed${NC}"
    echo -e "${WHITE}5. Check your internet connection and Fabric API access${NC}"
    exit 1
fi