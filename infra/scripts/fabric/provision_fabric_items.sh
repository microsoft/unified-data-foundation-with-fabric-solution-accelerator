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
#     The script creates a Python virtual environment for dependency isolation and runs the deployment.
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
#     - Python 3.9+ with pip and venv module
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

# Function to cleanup virtual environment on exit
cleanup_venv() {
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        print_info "Deactivating virtual environment..."
        deactivate 2>/dev/null || true
    fi
    
    # Restore original location if we changed it
    if [[ "${ORIGINAL_DIR:-}" != "$(pwd)" ]] && [[ -n "${ORIGINAL_DIR:-}" ]]; then
        cd "$ORIGINAL_DIR" 2>/dev/null || true
    fi
}

# Set trap to cleanup on exit
trap cleanup_venv EXIT

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
    echo "  - Python 3.9+ with pip and venv module"
    echo "  - Appropriate permissions in the Fabric capacity and workspace"
}

# Main script starts here
print_success "Starting Microsoft Fabric deployment script..."

# Store original directory for cleanup
ORIGINAL_DIR="$(pwd)"

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

# Check if venv module is available
print_step "Checking Python venv module..."
if ! $PYTHON_CMD -m venv --help >/dev/null 2>&1; then
    print_error "❌ Python venv module is not available. Please install python3-venv package and try again."
    print_info "On Ubuntu/Debian: sudo apt-get install python3-venv"
    print_info "On RHEL/CentOS: sudo yum install python3-venv"
    exit 1
fi
print_success "Python venv module is available"

# Create and activate Python virtual environment
print_step "Setting up Python virtual environment..."
VENV_DIR="$SCRIPT_DIR/.venv"

# Create virtual environment if it doesn't exist
if [[ ! -d "$VENV_DIR" ]]; then
    print_info "Creating virtual environment at $VENV_DIR..."
    if ! $PYTHON_CMD -m venv "$VENV_DIR"; then
        print_error "❌ Failed to create virtual environment. Please ensure python3-venv is installed."
        exit 1
    fi
    print_success "Created virtual environment at: $VENV_DIR"
else
    print_success "Using existing virtual environment at: $VENV_DIR"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
print_success "Activated virtual environment"

# Upgrade pip in virtual environment
print_info "Upgrading pip in virtual environment..."
if ! python -m pip install --upgrade pip --quiet; then
    print_warning "⚠️ Failed to upgrade pip, continuing with existing version..."
fi

# Validate that pip is available in the virtual environment
print_step "Checking pip installation in virtual environment..."
if ! command -v pip >/dev/null 2>&1; then
    print_error "❌ pip is not available in the virtual environment."
    exit 1
fi
print_success "pip is available in virtual environment"

# Install Python dependencies in virtual environment
print_step "Installing Python dependencies from requirements.txt..."
if [[ ! -f "$REQUIREMENTS_PATH" ]]; then
    print_error "❌ requirements.txt not found at: $REQUIREMENTS_PATH"
    exit 1
fi
if ! pip install -r "$REQUIREMENTS_PATH" --quiet; then
    print_error "❌ Failed to install Python dependencies. Please check requirements.txt and try again."
    exit 1
fi
print_success "Dependencies installed successfully in virtual environment"

# Change to script directory for Python execution
cd "$SCRIPT_DIR"

# Run the Python deployment script with error handling
print_step "Starting Fabric items deployment..."
print_info "This may take several minutes to complete..."
echo ""

# Build command arguments
python_args=(--capacityName "$fabricCapacityName")
if [[ -n "$fabricWorkspaceName" ]]; then
    python_args+=(--workspaceName "$fabricWorkspaceName")
fi

# Execute Python script and capture result
deployment_success=false
if python -u create_fabric_items.py "${python_args[@]}"; then
    deployment_success=true
fi

# Handle results
if [[ "$deployment_success" == "true" ]]; then
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
    echo -e "${WHITE}6. Check the virtual environment at $VENV_DIR${NC}"
    exit 1
fi