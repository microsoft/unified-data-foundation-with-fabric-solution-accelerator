#!/usr/bin/env python3
"""
Databricks Workspace Bootstrap Script
-------------------------------------
Automates:
- Upload of notebooks and CSVs to Databricks workspace
- Unity Catalog creation (if needed)
- Orchestrator notebook execution (optional)

All CSVs are uploaded to a single DBFS folder for simplicity.
All notebooks have widgets for catalog, schema, and base_path, which are normalized dynamically.
"""
 
import os
import re
import argparse
import base64
import json
import time
from pathlib import Path
from typing import Dict, Optional, Any
 
import requests
 
from typing import Dict, Optional, Any




 
def _normalize_widget_defaults_line(line: str, catalog: str, schema: str, base_path: str = None) -> str:
    # Normalize widget defaults for catalog, schema, and base_path
    line = re.sub(r'dbutils\.widgets\.text\(\s*["\']catalog_name["\']\s*,\s*["\'].*?["\']\s*\)',
                 f'dbutils.widgets.text("catalog_name", "{catalog}")', line)
    line = re.sub(r'dbutils\.widgets\.text\(\s*["\']schema_name["\']\s*,\s*["\'].*?["\']\s*\)',
                 f'dbutils.widgets.text("schema_name", "{schema}")', line)
    if base_path is not None:
        line = re.sub(r'dbutils\.widgets\.text\(\s*["\']base_path["\']\s*,\s*["\'].*?["\']\s*\)',
                      f'dbutils.widgets.text("base_path", "{base_path}")', line)
    return line
 
 
def _normalize_run_magics_line(line: str, solution_abs_base: str) -> str:
    # Normalize %run lines to absolute /Workspace path and ensure .ipynb suffix
    m = re.match(r'(^\s*%run\s+)(["\']?)([^"\']+?)(["\']?)\s*$', line)
    if not m:
        # Also repair "%run Shared/..." -> "%run /Shared/..." quickly,
        # then try to match again (rare quirky format).
        line = re.sub(r'(^\s*%run\s+)(["\']?)Shared/', r'\1\2/Shared/', line)
        m = re.match(r'(^\s*%run\s+)(["\']?)([^"\']+?)(["\']?)\s*$', line)
        if not m:
            return line
 
    prefix, _q1, path, _q2 = m.groups()
    path = path.strip()
 
    # Compute absolute path under Workspace
    if path.startswith("/Workspace/"):
        new_path = path
    elif path.startswith("/maag-notebooks/"):
        # If already starts with /maag-notebooks, prepend solution base
        new_path = f"/Workspace{solution_abs_base}/maag-notebooks/{path[len('/maag-notebooks/'):] }"
    elif path.startswith("maag-notebooks/"):
        new_path = f"/Workspace{solution_abs_base}/maag-notebooks/{path[len('maag-notebooks/'):] }"
    elif path.startswith("./"):
        new_path = f"/Workspace{solution_abs_base}/maag-notebooks/{path[2:]}"
    elif path.startswith("../"):
        new_path = f"/Workspace{solution_abs_base}/maag-notebooks/{path[3:]}"
    elif not path.startswith("/"):
        new_path = f"/Workspace{solution_abs_base}/maag-notebooks/{path}"
    else:
        new_path = path  # unknown absolute; leave as-is
 
    # Ensure .ipynb extension (Databricks accept both, but your env expects the file form)
    if not new_path.endswith(".ipynb"):
        new_path += ".ipynb"
 
    return f"{prefix}{new_path}\n"
 
 
def _process_ipynb_text_safely(raw_json: str, solution_abs_base: str,
                               catalog: str, schema: str,
                               kv_replacements: Dict[str, str],
                               dbfs_solution: str = None) -> str:

    nb = json.loads(raw_json)
 
    def fix_source(src):
        if isinstance(src, list):
            out = []
            for line in src:
                line = _normalize_widget_defaults_line(line, catalog, schema, base_path=dbfs_solution)
                for k, v in kv_replacements.items():
                    line = line.replace(k, v)
                if line.lstrip().startswith("%run"):
                    line = _normalize_run_magics_line(line, solution_abs_base)
                out.append(line)
            return out
        elif isinstance(src, str):
            s = _normalize_widget_defaults_line(src, catalog, schema, base_path=dbfs_solution)
            for k, v in kv_replacements.items():
                s = s.replace(k, v)
            if s.lstrip().startswith("%run"):
                s = _normalize_run_magics_line(s, solution_abs_base)
            return s
        return src

    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code" and "source" in cell:
            cell["source"] = fix_source(cell["source"])
 
    return json.dumps(nb, ensure_ascii=False)
  
 
# ---------------------- Databricks Jobs Helpers (Notebook Run) ----------------------
 
def _jobs_runs_submit(host: str, hdrs: Dict[str, str], payload: Dict[str, Any]) -> str:
    url = f"{host}/api/2.1/jobs/runs/submit"
    r = requests.post(url, headers=hdrs, json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"jobs/runs/submit failed: {r.status_code} {r.text}")
    return r.json()["run_id"]
 
 
def _jobs_runs_get(host: str, hdrs: Dict[str, str], run_id: str) -> Dict[str, Any]:
    url = f"{host}/api/2.1/jobs/runs/get?run_id={run_id}"
    r = requests.get(url, headers=hdrs, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"jobs/runs/get failed: {r.status_code} {r.text}")
    return r.json()
 
 
def run_notebook_once(host: str, hdrs: Dict[str, str], notebook_path: str,
                      parameters: Dict[str, str], existing_cluster_id: str,
                      timeout_s: int = 3600):

    if not existing_cluster_id:
        raise RuntimeError("Missing --cluster-id (Jobs need a cluster to run notebooks).")
    submit = {
        "run_name": "maag-bootstrap-run_bronze_to_adb",
        "timeout_seconds": timeout_s,
        "tasks": [
            {
                "task_key": "run_bronze",
                "existing_cluster_id": existing_cluster_id,
                "notebook_task": {
                    "notebook_path": notebook_path,
                    "base_parameters": parameters
                }
            }
        ]
    }
    run_id = _jobs_runs_submit(host, hdrs, submit)
    start = time.time()
    while True:
        resp = _jobs_runs_get(host, hdrs, run_id)
        life = resp.get("state", {}).get("life_cycle_state")
        res = resp.get("state", {}).get("result_state")
        if life in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR"):
            if res == "SUCCESS":
                print("Orchestration notebook finished successfully.")
                return
            raise RuntimeError(f"Notebook run failed: {json.dumps(resp, indent=2)}")
        if time.time() - start > timeout_s:
            raise RuntimeError("Timeout waiting for notebook to finish.")
        time.sleep(10)
 
 

 
def resolve_external_location_url(host: str, hdrs: Dict[str, str], loc: str) -> str:

    if re.match(r"^(abfss|abfs|s3|gs)://", loc.strip(), re.IGNORECASE):
        return loc.strip()
    get_url = f"{host}/api/2.1/unity-catalog/external-locations/{loc}"
    r = requests.get(get_url, headers=hdrs, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Couldn't resolve external location '{loc}': {r.status_code} {r.text}")
    return r.json()["url"]
 
 
 
 
def get_host(cli_url: Optional[str]) -> str:
    host = (cli_url or os.environ.get("DATABRICKS_HOST") or "").strip().rstrip("/")
    if not host:
        raise RuntimeError("Set DATABRICKS_HOST env or pass --workspaceUrl")
    return host
 
 
def headers(token: Optional[str]) -> Dict[str, str]:
    tok = (token or os.environ.get("DATABRICKS_TOKEN") or "").strip()
    if not tok:
        raise RuntimeError("Set DATABRICKS_TOKEN env or pass --token")
    return {"Authorization": f"Bearer {tok}"}
 
 
def mkdirs(host: str, hdrs: Dict[str, str], path: str):
    url = f"{host}/api/2.0/workspace/mkdirs"
    r = requests.post(url, headers=hdrs, json={"path": path}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"workspace mkdirs failed for {path}: {r.status_code} {r.text}")
 
 
def _reduce_replace(s: str, kv: Dict[str, str]) -> str:
    for k, v in kv.items():
        s = s.replace(k, v)
    return s
 
 
def import_file(host: str, hdrs: Dict[str, str], local_path: Path, ws_path: str,
                replacements: Dict[str, str], catalog: str, schema: str, dbfs_solution: str = None):

    lp = str(local_path).lower()
    if lp.endswith(".ipynb"):
        fmt = "JUPYTER"
        language = "PYTHON"
        raw = local_path.read_text(encoding="utf-8")
        # Normalize %run and widgets
        parts = ws_path.split("/")
        abs_base = None
        if "Shared" in parts:
            try:
                sol = parts[parts.index("Shared") + 1]
                abs_base = f"/Shared/{sol}"
            except Exception:
                abs_base = None
        base_path_val = dbfs_solution
        nb = json.loads(raw)
        for cell in nb.get("cells", []):
            if cell.get("cell_type") == "code" and "source" in cell:
                if isinstance(cell["source"], list):
                    out = []
                    for line in cell["source"]:
                        line = _normalize_widget_defaults_line(line, catalog, schema, base_path=base_path_val)
                        for k, v in replacements.items():
                            line = line.replace(k, v)
                        if line.lstrip().startswith("%run"):
                            line = _normalize_run_magics_line(line, abs_base)
                        out.append(line)
                    cell["source"] = out
                elif isinstance(cell["source"], str):
                    s = _normalize_widget_defaults_line(cell["source"], catalog, schema, base_path=base_path_val)
                    for k, v in replacements.items():
                        s = s.replace(k, v)
                    if s.lstrip().startswith("%run"):
                        s = _normalize_run_magics_line(s, abs_base)
                    cell["source"] = s
        raw = json.dumps(nb, ensure_ascii=False)
    elif lp.endswith(".py"):
        fmt = "SOURCE"
        language = "PYTHON"
        raw = local_path.read_text(encoding="utf-8")
        raw = _normalize_widget_defaults_line(raw, catalog, schema)
        raw = _reduce_replace(raw, replacements)
    elif lp.endswith(".sql"):
        fmt = "SQL"
        language = "SQL"
        raw = local_path.read_text(encoding="utf-8")
        raw = _reduce_replace(raw, replacements)
    else:
        return False
    content_b64 = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
    url = f"{host}/api/2.0/workspace/import"
    payload = {"path": ws_path, "format": fmt, "language": language, "overwrite": True, "content": content_b64}
    r = requests.post(url, headers=hdrs, json=payload, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"workspace import failed for {ws_path}: {r.status_code} {r.text}")
    return True
 
 
def dbfs_mkdirs(host: str, hdrs: Dict[str, str], dbfs_dir: str):
    url = f"{host}/api/2.0/dbfs/mkdirs"
    r = requests.post(url, headers=hdrs, json={"path": dbfs_dir}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"dbfs mkdirs failed for {dbfs_dir}: {r.status_code} {r.text}")
 
 
def dbfs_put(host: str, hdrs: Dict[str, str], local_path: Path, dbfs_path: str, overwrite=True):
    url = f"{host}/api/2.0/dbfs/put"
    content_b64 = base64.b64encode(local_path.read_bytes()).decode("utf-8")
    payload = {"path": dbfs_path, "overwrite": overwrite, "contents": content_b64}
    r = requests.post(url, headers=hdrs, json=payload, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"dbfs put failed for {dbfs_path}: {r.status_code} {r.text}")
 
 
def relposix(root: Path, file: Path) -> str:
    return file.relative_to(root).as_posix()
 
 
def create_catalog(host: str, hdrs: Dict[str, str], catalog_name: str,
                   managed_location: str = "", warehouse_id: str = ""):
    get_url = f"{host}/api/2.1/unity-catalog/catalogs/{catalog_name}"
    gr = requests.get(get_url, headers=hdrs, timeout=60)
    if gr.status_code == 200:
        return

    post_url = f"{host}/api/2.1/unity-catalog/catalogs"
    payload = {"name": catalog_name, "comment": f"Auto-created for {catalog_name}"}
    if managed_location.strip():
        uri = resolve_external_location_url(host, hdrs, managed_location.strip())
        payload["storage_root"] = uri
    r = requests.post(post_url, headers=hdrs, json=payload, timeout=60)
    if r.status_code in (200, 201):
        return
    if r.status_code == 409:
        return  # Already exists (race)
    # Enhanced diagnostics for missing metastore storage root
    if r.status_code == 400 and 'Metastore storage root URL does not exist' in r.text:
        raise RuntimeError(
            "Catalog creation failed because the metastore has no default storage root configured and no managed location was provided. "
            "Provide one of: (1) --catalog-managed-location <external-location-name>, (2) --catalog-managed-location <cloud-uri>, or "
            "configure a metastore root storage location in the Databricks admin console. Original response: " + r.text
        )
    gr2 = requests.get(get_url, headers=hdrs, timeout=60)
    if gr2.status_code == 200:
        return
    raise RuntimeError(f"create/get catalog failed: {r.status_code} {r.text} | get: {gr.status_code} {gr.text}")

 
 

# ---------------------- Main ----------------------
 
def main():
    p = argparse.ArgumentParser(description="Bootstrap Databricks Workspace + DBFS + UC + optional job run.")
    p.add_argument("--workspaceUrl")
    p.add_argument("--token")
    p.add_argument("--solutionname", required=True)
    p.add_argument("--catalogname", default="")
    p.add_argument("--schemaname", default="")
    p.add_argument("--cluster-id", required=True, help="Existing cluster ID to run the orchestration notebook")
    p.add_argument("--catalog-managed-location", default="",
                   help="External Location name or cloud URI for catalog managed storage (required when --catalogname is set)")

    args = p.parse_args()

    # --- Setup paths and environment ---
    host = get_host(args.workspaceUrl)
    hdrs = headers(args.token)

    # Cluster ID (argparse enforces presence)
    cluster_id = args.cluster_id.strip()

    # Use catalog managed location as provided by user
    cat_loc = args.catalog_managed_location.strip()

    catalog = args.catalogname.strip()
    if catalog and not cat_loc:
        raise RuntimeError("--catalog-managed-location is required. Please provide a valid managed location or external location name.")



    # --- Setup paths and environment ---
    host = get_host(args.workspaceUrl)
    hdrs = headers(args.token)
    # Always resolve notebooks path relative to repo root
    notebooks_root = (Path(__file__).parent.parent.parent.parent / "src/databricks/notebooks").resolve()
    data_root = (Path(__file__).parent.parent.parent.parent / "infra/data/samples_databricks").resolve()
    shared_base = "/Shared"
    solution_ws = f"{shared_base}/{args.solutionname}"
    maag_notebooks_ws = f"{solution_ws}/maag-notebooks"
    dbfs_base = os.environ.get("DATABRICKS_DBFS_BASE", "dbfs:/FileStore/tables")
    dbfs_solution = f"{dbfs_base.rstrip('/')}/{args.solutionname}"
    schema = args.schemaname.strip()

    # Ensure workspace folders exist
    print(f"Ensuring workspace folder: {solution_ws}")
    mkdirs(host, hdrs, solution_ws)
    print(f"Ensuring maag-notebooks folder: {maag_notebooks_ws}")
    mkdirs(host, hdrs, maag_notebooks_ws)

    # Upload notebooks with widget normalization
    if not notebooks_root.exists():
        raise RuntimeError(f"Notebooks folder not found: {notebooks_root}")
    print(f"Uploading notebooks from: {notebooks_root}")
    repl: Dict[str, str] = {}
    repl.setdefault('WORKSPACE_NAME = "Fabric_MAAG"', f'WORKSPACE_NAME = "{args.solutionname}"')
    repl['base_path = \'/FileStore/tables/sales\''] = "base_path = os.environ.get('DATABRICKS_DBFS_BASE', '/FileStore/tables/sales')"
    repl['base_path = "/FileStore/tables/sales"'] = 'base_path = os.environ.get("DATABRICKS_DBFS_BASE", "/FileStore/tables/sales")'
    for file in notebooks_root.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in [".ipynb", ".py", ".sql"]:
            continue
        ws_path = f"{solution_ws}/{file.name}" if file.name == "run_bronze_to_adb.ipynb" else f"{maag_notebooks_ws}/{file.name}"
        print(f"  Import: {file.name} -> {ws_path}")
        import_file(host, hdrs, file, ws_path, repl, catalog=catalog or "", schema=schema or "", dbfs_solution=dbfs_solution)

    # Upload all CSVs to a single DBFS folder
    if data_root.exists():
        print(f"Uploading CSVs to DBFS under: {dbfs_solution}")
        dbfs_mkdirs(host, hdrs, dbfs_solution)
        for file in data_root.rglob("*.csv"):
            dbfs_path = f"{dbfs_solution}/{file.name}"
            print(f"  DBFS put: {file.name} -> {dbfs_path}")
            dbfs_put(host, hdrs, file, dbfs_path, overwrite=True)
    else:
        print(f"[warn] Data folder not found; skipping CSV upload: {data_root}")

    # Create Unity Catalog if needed
    if catalog:
        print(f"Ensuring catalog: {catalog}")
    create_catalog(host, hdrs, catalog, managed_location=cat_loc)

   
    # Run orchestrator notebook if cluster provided
    if catalog and schema and cluster_id:
        nb_path = f"{solution_ws}/run_bronze_to_adb.ipynb"
        print(f"Running orchestration notebook: {nb_path}")
        run_notebook_once(
            host=host,
            hdrs=hdrs,
            notebook_path=nb_path,
            parameters={"catalog_name": catalog, "schema_name": schema},
            existing_cluster_id=cluster_id
        )
 
 
if __name__ == "__main__":
    main()
