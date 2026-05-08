#!/usr/bin/env python3
"""
Unified Data Foundation Solution Installer

This script provides a simplified deployment entry-point for the Unified Data Foundation
solution. It performs only the minimum steps needed to bootstrap the solution:

    1. setup_workspace        - Create and configure the Fabric workspace/capacity
    2. setup_administrators   - Add workspace administrators
    3. upload_installer       - Upload the installer notebook to the workspace
    4. run_installer          - Execute the installer notebook end-to-end

The installer notebook (udf_solution_installer.ipynb) handles the remaining
solution-specific steps (lakehouse creation, data ingestion, notebook deployment,
post-deployment tasks, …) once it has been uploaded and started.

Usage:
    python install_udf_solution.py

Environment Variables:
    The following variables are automatically set by 'azd' from main.bicep outputs and
    must be present in the environment before running this script:

    AZURE_FABRIC_CAPACITY_NAME           (required) Name of the Fabric capacity resource.
                                                    Sourced from main.bicep output:
                                                    AZURE_FABRIC_CAPACITY_NAME.
    SOLUTION_SUFFIX                      (required) Suffix used for resource naming.
                                                    Sourced from main.bicep output:
                                                    SOLUTION_SUFFIX.
    AZURE_FABRIC_CAPACITY_ADMINISTRATORS (required) JSON array of capacity administrator
                                                    identities. Sourced from main.bicep
                                                    output: AZURE_FABRIC_CAPACITY_ADMINISTRATORS.

    The following variables are optional and must be set manually if needed:

    FABRIC_WORKSPACE_NAME                (optional) Override the default workspace name
                                                    (defaults to "<SOLUTION_NAME> - <SOLUTION_SUFFIX>").
    FABRIC_WORKSPACE_ADMINISTRATORS      (optional) Comma-separated list of additional
                                                    workspace administrator identities.
    GITHUB_TOKEN                         (optional) GitHub token passed only as a
                                                    notebook run parameter for private
                                                    or internal source repositories.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add current directory to path so local modules can be imported
sys.path.append(os.path.dirname(__file__))

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.identity import AzureCliCredential
from azure.storage.filedatalake import DataLakeServiceClient
from fabric_launcher.fabric_deployer import FabricDeployer

from fabric_api import FabricApiError, create_fabric_client, create_workspace_fabric_client
from graph_api import create_graph_client
from helpers.utils import (
    encode_notebook,
    get_required_env_var,
    parse_workspace_administrators,
    print_step,
    print_steps_summary,
)
from helpers.udf_workspace import setup_workspace
from helpers.udf_workspace_admins import setup_workspace_administrators


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOLUTION_NAME = "Unified Data Foundation"
INSTALLER_NOTEBOOK_NAME = "udf_solution_installer"
EXPECTED_DEPLOYED_ITEMS = {
    ("maag_bronze", "Lakehouse"),
    ("maag_silver", "Lakehouse"),
    ("maag_gold", "Lakehouse"),
    ("run_bronze_to_silver", "Notebook"),
    ("run_silver_to_gold", "Notebook"),
    ("sales_dashboard", "Report"),
    ("sales_dashboard", "SemanticModel"),
    ("Data Agent for UDF", "DataAgent"),
}

ALL_DEPLOYMENT_STEPS = [
    "setup_workspace",
    "setup_administrators",
    "upload_installer",
    "deploy_solution",
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _notebook_path() -> str:
    """Return the absolute path to the installer notebook file.

    The notebook lives at ``<repo-root>/infra/deploy/udf_solution_installer.ipynb``.
    This file is located at ``<repo-root>/infra/scripts/fabric/install_udf_solution.py``,
    so we walk two directories up from the script directory to reach ``infra/``.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    infra_dir = os.path.dirname(os.path.dirname(script_dir))
    return os.path.join(infra_dir, "deploy", f"{INSTALLER_NOTEBOOK_NAME}.ipynb")


def _repo_root() -> Path:
    """Return the repository root for local deployment operations."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent.parent


def _upload_installer_notebook(workspace_client, notebook_path: str) -> str:
    """Upload (or update) the installer notebook in the workspace.

    If a notebook with the same name already exists it will be updated in-place;
    otherwise a new notebook is created.

    Args:
        workspace_client: Authenticated :class:`FabricWorkspaceApiClient`.
        notebook_path: Absolute path to the local ``.ipynb`` file.

    Returns:
        str: The notebook ID of the uploaded/updated notebook.

    Raises:
        FileNotFoundError: If the notebook file does not exist.
        FabricApiError: If the Fabric API call fails.
    """
    print(f"   Reading notebook file: {notebook_path}")
    notebook_base64 = encode_notebook(notebook_path)

    print(f"   Checking for existing notebook: {INSTALLER_NOTEBOOK_NAME}")
    existing = workspace_client.get_notebook_by_name(INSTALLER_NOTEBOOK_NAME)

    if existing:
        notebook_id = existing["id"]
        print(f"   ℹ️  Notebook already exists ({notebook_id}) – updating definition")
        workspace_client.update_notebook(notebook_id, notebook_base64)
        print(f"   ✅ Notebook updated: {INSTALLER_NOTEBOOK_NAME}")
    else:
        print(f"   Creating notebook: {INSTALLER_NOTEBOOK_NAME}")
        workspace_client.create_notebook(INSTALLER_NOTEBOOK_NAME, notebook_base64)
        refreshed = workspace_client.get_notebook_by_name(INSTALLER_NOTEBOOK_NAME)
        if not refreshed:
            raise FabricApiError(
                f"Notebook '{INSTALLER_NOTEBOOK_NAME}' was not found after creation"
            )
        notebook_id = refreshed["id"]
        print(f"   ✅ Notebook created: {INSTALLER_NOTEBOOK_NAME} ({notebook_id})")

    return notebook_id


def _run_installer_notebook(workspace_client, notebook_id: str, monitor_interval: int = 20,
                            max_retries: int = 3, initial_backoff: int = 30,
                            github_token: Optional[str] = None) -> None:
    """Schedule and monitor the installer notebook job until completion.

    Transient Fabric Spark errors (e.g. ``GetManagedVnetTimeout``) are retried
    automatically with exponential back-off.

    Args:
        workspace_client: Authenticated :class:`FabricWorkspaceApiClient`.
        notebook_id: ID of the notebook to execute.
        monitor_interval: Seconds between status-polling requests (default: 20).
        max_retries: Maximum number of retry attempts for transient errors (default: 3).
        initial_backoff: Initial back-off in seconds before the first retry (default: 30).
        github_token: Optional GitHub token for internal/private repository downloads.

    Raises:
        FabricApiError: If the notebook job fails to start or returns an error status
            after all retry attempts are exhausted.
    """
    # Error substrings that indicate a transient Spark/VNet issue worth retrying.
    retryable_errors = ["GetManagedVnetTimeout", "Please retry"]

    for attempt in range(1, max_retries + 1):
        print(f"   Scheduling notebook job (attempt {attempt}/{max_retries}): "
              f"{INSTALLER_NOTEBOOK_NAME} ({notebook_id})")
        try:
            parameters = {"github_token": github_token} if github_token else None
            result = workspace_client.schedule_notebook_job(
                notebook_id,
                monitor_interval=monitor_interval,
                parameters=parameters,
            )
        except FabricApiError as exc:
            error_str = str(exc)
            if attempt < max_retries and any(err in error_str for err in retryable_errors):
                backoff = initial_backoff * (2 ** (attempt - 1))
                print(f"   ⚠️  Transient error detected (attempt {attempt}/{max_retries}): {error_str}")
                print(f"   ⏳ Retrying in {backoff}s…")
                time.sleep(backoff)
                continue
            raise

        status = result.get("status", "Unknown")
        duration = result.get("duration", "N/A")

        print(f"   📊 Execution result:")
        print(f"      Status:   {status}")
        print(f"      Duration: {duration}")

        if status == "Completed":
            print(f"   ✅ Installer notebook completed successfully")
            return

        error_detail = result.get("error", "No error details available")
        error_str = str(error_detail)

        if attempt < max_retries and any(err in error_str for err in retryable_errors):
            backoff = initial_backoff * (2 ** (attempt - 1))
            print(f"   ⚠️  Transient error detected (attempt {attempt}/{max_retries}): {error_detail}")
            print(f"   ⏳ Retrying in {backoff}s…")
            time.sleep(backoff)
            continue

        raise FabricApiError(
            f"Installer notebook finished with status '{status}'. Error: {error_detail}"
        )

    print(f"   ✅ Installer notebook completed successfully")


def _verify_solution_items(workspace_client) -> None:
    """Verify that the installer deployed the expected solution items."""
    print("   Verifying deployed Fabric solution items")
    items = workspace_client.list_items()
    item_pairs = {
        (item.get("displayName"), item.get("type"))
        for item in items
    }

    missing = sorted(EXPECTED_DEPLOYED_ITEMS - item_pairs)
    if missing:
        missing_text = ", ".join(f"{name} ({item_type})" for name, item_type in missing)
        raise FabricApiError(
            "Required solution items are missing: "
            f"{missing_text}"
        )

    print(f"   ✅ Verified {len(EXPECTED_DEPLOYED_ITEMS)} deployed solution item(s)")


class _AzureCliNotebookUtils:
    """Minimal notebookutils credential shim for fabric-launcher local deployments."""

    class _Credentials:
        def __init__(self) -> None:
            self._credential = AzureCliCredential()

        def getToken(self, _resource: str) -> str:
            return self._credential.get_token("https://api.fabric.microsoft.com/.default").token

    def __init__(self) -> None:
        self.credentials = self._Credentials()


def _deploy_items_from_local_repo(workspace_id: str, repo_root: Path) -> None:
    """Deploy Fabric items directly from the checked-out local repository."""
    repository_directory = repo_root / "fabric_workspace"
    if not repository_directory.is_dir():
        raise FabricApiError(f"Fabric workspace directory not found: {repository_directory}")

    for stage in (["Lakehouse"], ["Notebook", "Report", "DataAgent", "SemanticModel"]):
        print(f"   Deploying Fabric item stage: {', '.join(stage)}")
        for attempt in range(1, 4):
            deployer = FabricDeployer(
                workspace_id=workspace_id,
                repository_directory=str(repository_directory),
                notebookutils=_AzureCliNotebookUtils(),
                allow_non_empty_workspace=True,
            )
            try:
                deployer.deploy_items(item_types=stage)
                break
            except Exception as exc:
                if attempt == 3:
                    raise
                backoff = 20 * attempt
                print(
                    f"   ⚠️  Fabric item stage failed on attempt {attempt}/3: {exc}. "
                    f"Retrying in {backoff}s."
                )
                time.sleep(backoff)


def _ensure_onelake_directory(file_system_client, base_path: str, directory_path: str,
                              created_paths: set[str]) -> None:
    """Create a OneLake directory under a Lakehouse Files root if it is missing."""
    if not directory_path or directory_path == base_path:
        return
    if not directory_path.startswith(f"{base_path}/"):
        raise FabricApiError(f"Unexpected OneLake target path: {directory_path}")

    current = base_path
    for part in directory_path[len(base_path) + 1:].split("/"):
        current = f"{current}/{part}"
        if current in created_paths:
            continue
        try:
            file_system_client.get_directory_client(current).create_directory()
        except ResourceExistsError:
            pass
        created_paths.add(current)


def _upload_data_to_bronze_lakehouse(workspace_name: str, repo_root: Path,
                                     lakehouse_name: str = "maag_bronze") -> None:
    """Upload repository data files to the bronze Lakehouse Files root."""
    source_root = repo_root / "infra" / "data"
    if not source_root.is_dir():
        raise FabricApiError(f"Data source directory not found: {source_root}")

    service_client = DataLakeServiceClient(
        account_url="https://onelake.dfs.fabric.microsoft.com",
        credential=AzureCliCredential(),
    )
    file_system_client = service_client.get_file_system_client(workspace_name)
    base_path = f"{lakehouse_name}.Lakehouse/Files"
    created_paths: set[str] = set()
    uploaded_count = 0

    for source_file in sorted(path for path in source_root.rglob("*") if path.is_file()):
        relative_path = source_file.relative_to(source_root).as_posix()
        target_path = f"{base_path}/{relative_path}"
        parent_path = target_path.rsplit("/", 1)[0]
        _ensure_onelake_directory(file_system_client, base_path, parent_path, created_paths)

        file_client = file_system_client.get_file_client(target_path)
        try:
            file_client.delete_file()
        except ResourceNotFoundError:
            pass

        data = source_file.read_bytes()
        file_client.create_file()
        if data:
            file_client.append_data(data=data, offset=0, length=len(data))
        file_client.flush_data(len(data))
        uploaded_count += 1

    print(f"   ✅ Uploaded {uploaded_count} data file(s) to {lakehouse_name}/Files")


def _run_post_deployment_notebooks(workspace_client) -> None:
    """Run the standard post-deployment transformation notebooks."""
    items = workspace_client.list_items()
    notebooks = {
        item.get("displayName"): item
        for item in items
        if item.get("type") == "Notebook"
    }

    for notebook_name in ("run_bronze_to_silver", "run_silver_to_gold"):
        notebook = notebooks.get(notebook_name)
        if not notebook:
            raise FabricApiError(f"Post-deployment notebook not found: {notebook_name}")

        print(f"   Running post-deployment notebook: {notebook_name}")
        result = workspace_client.schedule_notebook_job(
            notebook["id"],
            monitor_interval=30,
        )
        status = result.get("status", "Unknown")
        duration = result.get("duration", "N/A")
        print(f"      Status:   {status}")
        print(f"      Duration: {duration}")
        if status != "Completed":
            error_detail = result.get("error", "No error details available")
            raise FabricApiError(
                f"Post-deployment notebook '{notebook_name}' finished with "
                f"status '{status}'. Error: {error_detail}"
            )


def _deploy_solution_locally(workspace_id: str, workspace_name: str, workspace_client) -> None:
    """Deploy the solution from local files, upload data, and run transformations."""
    repo_root = _repo_root()
    print("   Deploying Fabric items from local repository")
    _deploy_items_from_local_repo(workspace_id, repo_root)
    print("   Uploading sample data to bronze Lakehouse")
    _upload_data_to_bronze_lakehouse(workspace_name, repo_root)
    print("   Running post-deployment transformations")
    _run_post_deployment_notebooks(workspace_client)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Orchestrate the solution installation."""

    # ------------------------------------------------------------------
    # Configuration from environment variables
    # ------------------------------------------------------------------
    capacity_name = get_required_env_var("AZURE_FABRIC_CAPACITY_NAME")
    solution_suffix = get_required_env_var("SOLUTION_SUFFIX")
    workspace_name = os.getenv(
        "FABRIC_WORKSPACE_NAME", f"{SOLUTION_NAME} - {solution_suffix}"
    )
    workspace_administrators = parse_workspace_administrators(
        get_required_env_var("AZURE_FABRIC_CAPACITY_ADMINISTRATORS"),
        os.getenv("FABRIC_WORKSPACE_ADMINISTRATORS"),
    )
    github_token = os.getenv("GITHUB_TOKEN")

    notebook_path = _notebook_path()

    # ------------------------------------------------------------------
    # Startup banner
    # ------------------------------------------------------------------
    print(f"🏭 {SOLUTION_NAME} – Solution Installer")
    print("=" * 60)
    print(f"Capacity:          {capacity_name}")
    print(f"Workspace:         {workspace_name}")
    print(f"Solution Suffix:   {solution_suffix}")
    print(f"Installer Notebook:{notebook_path}")
    if workspace_administrators:
        print(f"Administrators:    {', '.join(workspace_administrators)}")
    if github_token:
        print("GitHub Token:      present (not required for local deployment)")
    print(f"Start time:        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Authenticate API clients
    # ------------------------------------------------------------------
    print("\n🔐 Authenticating clients…")
    try:
        fabric_client = create_fabric_client()
        print("   ✅ Fabric API client authenticated")
    except Exception as exc:
        print(f"   ❌ Failed to authenticate Fabric API client: {exc}")
        sys.exit(1)

    try:
        graph_client = create_graph_client()
        print("   ✅ Graph API client authenticated")
    except Exception as exc:
        print(f"   ❌ Failed to authenticate Graph API client: {exc}")
        sys.exit(1)

    executed_steps: list = []
    failed_steps: list = []

    def _abort(step_name: str, error: Exception) -> None:
        """Record the failure, print a summary, and exit."""
        print(f"❌ Exception while executing {step_name}: {error}")
        failed_steps.append({"step": step_name, "error": str(error)})
        completed = {s for s in executed_steps} | {s["step"] for s in failed_steps}
        uncompleted = [s for s in ALL_DEPLOYMENT_STEPS if s not in completed]
        print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, uncompleted)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 1 – Set up Fabric workspace
    # ------------------------------------------------------------------
    print_step(1, 4, "Setting up Fabric workspace and capacity assignment",
               capacity_name=capacity_name, workspace_name=workspace_name)
    try:
        workspace_id = setup_workspace(
            fabric_client=fabric_client,
            capacity_name=capacity_name,
            workspace_name=workspace_name,
        )
        print("✅ Successfully completed: setup_workspace")
        executed_steps.append("setup_workspace")
    except Exception as exc:
        _abort("setup_workspace", exc)

    # Workspace-scoped client required for all subsequent steps
    print("\n🔐 Creating workspace-scoped Fabric API client…")
    try:
        workspace_client = create_workspace_fabric_client(workspace_id)
        print("   ✅ Workspace client authenticated")
    except Exception as exc:
        _abort("create_workspace_client", exc)

    # ------------------------------------------------------------------
    # Step 2 – Configure workspace administrators
    # ------------------------------------------------------------------
    admin_display = ", ".join(workspace_administrators) if workspace_administrators else "None"
    print_step(2, 4, "Configuring workspace administrators",
               workspace_id=workspace_id, administrators=admin_display)
    try:
        setup_workspace_administrators(
            workspace_client=workspace_client,
            fabric_admins=workspace_administrators,
            graph_client=graph_client,
        )
        print("✅ Successfully completed: setup_administrators")
        executed_steps.append("setup_administrators")
    except Exception as exc:
        _abort("setup_administrators", exc)

    # ------------------------------------------------------------------
    # Step 3 – Upload installer notebook
    # ------------------------------------------------------------------
    print_step(3, 4, "Uploading installer notebook",
               notebook=INSTALLER_NOTEBOOK_NAME)
    try:
        notebook_id = _upload_installer_notebook(workspace_client, notebook_path)
        print("✅ Successfully completed: upload_installer")
        executed_steps.append("upload_installer")
    except Exception as exc:
        _abort("upload_installer", exc)

    # ------------------------------------------------------------------
    # Step 4 – Deploy solution artifacts, data, and transformations
    # ------------------------------------------------------------------
    print_step(4, 4, "Deploying solution artifacts, data, and transformations",
               workspace_id=workspace_id)
    try:
        _deploy_solution_locally(workspace_id, workspace_name, workspace_client)
        _verify_solution_items(workspace_client)
        print("✅ Successfully completed: deploy_solution")
        executed_steps.append("deploy_solution")
    except Exception as exc:
        _abort("deploy_solution", exc)

    # ------------------------------------------------------------------
    # Success summary
    # ------------------------------------------------------------------
    workspace_url = (
        f"https://app.fabric.microsoft.com/groups/{workspace_id}?experience=fabric-developer"
    )

    print_steps_summary(SOLUTION_NAME, solution_suffix, executed_steps, failed_steps, [])

    print(f"\n{'='*60}")
    print(f"🎉 {SOLUTION_NAME.upper()} INSTALLATION COMPLETE!")
    print(f"{'='*60}")
    print(f"📅 Completed:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏷️  Suffix:     {solution_suffix}")
    print(f"☁️  Workspace:  {workspace_name}")
    print(f"🔗 URL:        {workspace_url}")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Installation interrupted by user")
        sys.exit(1)
    except Exception as exc:
        print(f"\n\n❌ Unexpected error: {exc}")
        sys.exit(1)
