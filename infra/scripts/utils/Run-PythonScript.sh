#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat >&2 <<'EOF'
Usage: Run-PythonScript.sh -ScriptPath <relative-path> [options]

Options:
  -ScriptArguments <args...>        Arguments passed to the Python script.
  -SkipPythonVirtualEnvironment    Use system Python directly.
  -SkipPythonDependencies          Skip requirements installation.
  -SkipPipUpgrade                  Skip pip upgrade.
  -RequirementsPath <path>         Requirements file path, relative to repo root unless absolute.
EOF
}

script_path=""
requirements_path=""
skip_venv=0
skip_dependencies=0
skip_pip_upgrade=0
script_arguments=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -ScriptPath)
            if [[ $# -lt 2 ]]; then
                echo "Missing value for -ScriptPath" >&2
                usage
                exit 1
            fi
            script_path="$2"
            shift 2
            ;;
        -ScriptArguments)
            shift
            while [[ $# -gt 0 && "$1" != -* ]]; do
                script_arguments+=("$1")
                shift
            done
            ;;
        -SkipPythonVirtualEnvironment)
            skip_venv=1
            shift
            ;;
        -SkipPythonDependencies)
            skip_dependencies=1
            shift
            ;;
        -SkipPipUpgrade)
            skip_pip_upgrade=1
            shift
            ;;
        -RequirementsPath)
            if [[ $# -lt 2 ]]; then
                echo "Missing value for -RequirementsPath" >&2
                usage
                exit 1
            fi
            requirements_path="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$script_path" ]]; then
    echo "-ScriptPath is required" >&2
    usage
    exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../../.." && pwd)"
target_script_path="$repo_root/$script_path"

if [[ ! -f "$target_script_path" ]]; then
    echo "Python script not found: $target_script_path" >&2
    exit 1
fi

if command -v python3 >/dev/null 2>&1; then
    python_cmd="python3"
elif command -v python >/dev/null 2>&1; then
    python_cmd="python"
else
    echo "Python 3.9+ is not installed or not available in PATH." >&2
    exit 1
fi

echo "Starting Python script execution..."
echo "Python found: $python_cmd"
echo "Target script: $target_script_path"
echo "Working directory: $(dirname -- "$target_script_path")"

if [[ "$skip_venv" -eq 1 ]]; then
    echo "Skipping Python virtual environment - using system Python"
    python_exec="$python_cmd"
else
    umask 077
    venv_path="$repo_root/.venv"
    if [[ ! -x "$venv_path/bin/python" ]]; then
        echo "Setting up Python virtual environment..."
        if "$python_cmd" -c "import ensurepip" >/dev/null 2>&1; then
            "$python_cmd" -m venv "$venv_path"
        else
            "$python_cmd" -m venv --without-pip "$venv_path"
        fi
    fi
    python_exec="$venv_path/bin/python"

    if ! "$python_exec" -m pip --version >/dev/null 2>&1; then
        echo "Bootstrapping pip in virtual environment..."
        "$python_cmd" -m pip --python "$venv_path" install --upgrade pip --disable-pip-version-check
    fi
fi

if [[ "$skip_pip_upgrade" -eq 0 ]]; then
    echo "Upgrading pip..."
    "$python_exec" -m pip install --upgrade pip --disable-pip-version-check
else
    echo "Skipping pip upgrade"
fi

if [[ "$skip_dependencies" -eq 0 ]]; then
    if [[ -z "$requirements_path" ]]; then
        requirements_path="$repo_root/requirements.txt"
    elif [[ "$requirements_path" != /* ]]; then
        requirements_path="$repo_root/$requirements_path"
    fi

    if [[ ! -f "$requirements_path" ]]; then
        echo "requirements.txt not found at: $requirements_path" >&2
        exit 1
    fi

    echo "Installing requirements..."
    "$python_exec" -m pip install -r "$requirements_path" --disable-pip-version-check
else
    echo "Skipping Python dependencies installation"
fi

pushd "$(dirname -- "$target_script_path")" >/dev/null
echo "Executing Python script..."
"$python_exec" -u "$(basename -- "$target_script_path")" "${script_arguments[@]}"
popd >/dev/null

echo "Python script execution completed successfully."
