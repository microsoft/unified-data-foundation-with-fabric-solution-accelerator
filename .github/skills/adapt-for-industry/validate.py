#!/usr/bin/env python3
"""
validate.py — Architecture-aware validator for adapt-for-industry.

Generated for solution accelerator: unified-data-foundation-with-fabric
Publish surface: azd-native

Run after applying changes via the skill workflow:

    python .github/skills/adapt-for-industry/validate.py

Exit 0 on all checks pass; exit 1 on any failure. Skipped checks count as
passes (a check is skipped when the corresponding capability was not
detected during architecture survey — e.g., no test framework configured).

For self-test (validates the validator's own helpers against synthetic
fixtures, no SA files touched):

    python .github/skills/adapt-for-industry/validate.py --self-test

To run a single check by name:

    python .github/skills/adapt-for-industry/validate.py --check environment

Output channels:
    stdout — human-friendly report (color when TTY, plain otherwise)
    stderr — one JSON object per CheckResult (machine-parseable)

# =============================================================================
# SUBSTITUTION SLOTS
# =============================================================================
# All slots use the convention UPPERCASE_SNAKE. There are two substitution
# modes; the table below identifies which mode applies to each slot.
#
#   1. token-level slots — the slot name token sits inside a string literal,
#      JSON heredoc, or Python comment. The generator replaces the token in
#      place. Until that happens the literal `slot name` text is detected by
#      `_load_slot()` (or by `bool(...)` of an unset string) and a no-op
#      default is used, keeping the fragment `py_compile`-clean as-is.
#
#   2. block-replacement slots — a pair of `# === BEGIN NAME ===` /
#      `# === END NAME ===` markers brackets a comment-only no-op block.
#      The generator replaces the entire block (markers included) with
#      generated code. The unfilled block is also `py_compile`-clean
#      because everything between markers is comments.
#
#   slot                              mode    source (architecture-survey YAML)
#   --------------------------------  ------  --------------------------------
#   adapt-for-industry                    token   generation argument (kebab-case skill id)
#   unified-data-foundation-with-fabric                       token   generation argument (sa identifier)
#   azd-native               token   publish.surface
#   true                token   derived: any iac tool == "bicep"
#                                               JSON value: true | false
#   true                  token   derived: publish.surface != "skip"
#                                               JSON value: true | false
#   []         token   validation_capability.lint_tools mapped
#                                               to runnable invocations.
#                                               JSON value: [["label", ["cmd", "arg", ...]], ...]
#                                               example: [["ruff", ["ruff", "check", "."]]]
#   [["infra/scripts/fabric", ["python3", "-m", "py_compile"]]]               token   derived from publish.services + schema_files.
#                                               JSON value: [["path", ["cmd", "arg", ...]], ...]
#                                               example: [["src", ["python", "-m", "py_compile"]]]
#   ["infra/main.parameters.json", "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/data_agent.json", "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/stage_config.json", "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json", "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/fewshots.json", "fabric_workspace/reports/sales_dashboard.Report/report.json", "src/fabric/notebooks/schema/model_shared_silver.ipynb", "src/fabric/notebooks/schema/model_salesfabric_gold.ipynb", "src/fabric/notebooks/data_agent/data_agent_setup.ipynb"]                  token   validation_capability.schema_files
#                                               JSON value: ["path", ...]
#                                               example: ["src/models/event.py"]
#   [["bicep", "az bicep build --file infra/main.bicep --stdout > /dev/null"]]            token   validation_capability.iac_build_commands
#                                               JSON value: [["tool", "shell command"], ...]
#                                               example: [["bicep", "az bicep build infra/main.bicep --stdout > /dev/null"]]
#   []                 token   derived from validation_capability.test_frameworks
#                                               JSON value: [["label", ["cmd", "arg", ...]], ...]
#                                               example: [["pytest", ["pytest", "-q"]]]
#                                               default if unfilled: []
#   true          token   derived: any non-empty
#                                               ui_surface.evidence.* entry,
#                                               build command, or smoke check.
#                                               JSON value: true | false
#   CROSS_LAYER_CHECK_FUNCTIONS       block   one `_check_<pair>()` function per
#                                               validation_capability.cross_layer_pairs
#                                               entry. Default block is a comment-only
#                                               no-op explaining the contract.
#   CROSS_LAYER_CHECK_REGISTRATIONS   block   one
#                                               `CROSS_LAYER_CHECKS.append(_check_<pair>)`
#                                               per pair. Default: comment-only no-op.
#   UI_CONTRACT_CHECK_FUNCTIONS       block   one `_check_ui_<surface>()` function
#                                               per surveyed UI/frontend contract
#                                               risk. Default block is comment-only
#                                               no-op.
#   UI_CONTRACT_CHECK_REGISTRATIONS   block   one
#                                               `UI_CONTRACT_CHECKS.append(_check_ui_<surface>)`
#                                               per UI check. Default: comment-only no-op.
#
# Slots intentionally NOT consumed by validate.py:
#
#   (publish.azure_yaml_hooks)        intentionally NOT consumed by validate.py;
#                                       hook integrity belongs in REDEPLOYMENT.md.
#   (ui_surface.build_commands)       not loaded as a global slot; generated UI
#                                       contract functions may inline frontend
#                                       build checks. deploy-adaptation owns
#                                       mutating activation/deploy.
# =============================================================================
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

# Repo root is two levels above this file (.github/skills/<skill>/validate.py).
REPO_ROOT = Path(__file__).resolve().parents[3]


# =============================================================================
# Slot loader — keeps the fragment py_compile-clean before substitution.
# =============================================================================

def _load_slot(raw: str, default: Any) -> Any:
    """Return JSON-decoded slot value, or `default` when the slot is unfilled.

    Unfilled slots still contain their literal `slot name` text; we detect this
    and fall back to a safe no-op default rather than raising at import time.
    """
    text = raw.strip()
    if not text or text.startswith("<<"):
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            f"validate.py: malformed slot JSON ({exc}); falling back to default.\n"
        )
        return default


# =============================================================================
# Configuration (filled by the generator at skill-emit time).
# =============================================================================

SKILL_NAME: str = "adapt-for-industry"
SA_NAME: str = "unified-data-foundation-with-fabric"
PUBLISH_SURFACE: str = "azd-native"

REQUIRES_BICEP: bool = bool(_load_slot("""true""", False))
REQUIRES_AZD: bool = bool(_load_slot("""true""", False))

# [(label, [cmd, arg, ...]), ...]
LINT_INVOCATIONS: list[tuple[str, list[str]]] = [
    (label, list(cmd))
    for label, cmd in _load_slot("""[]""", [])
]

# [(Path, [cmd, arg, ...]), ...]  — cmd is run with `path` appended as final arg.
COMPILE_TARGETS: list[tuple[Path, list[str]]] = [
    (Path(p), list(cmd))
    for p, cmd in _load_slot("""[["infra/scripts/fabric", ["python3", "-m", "py_compile"]]]""", [])
]

# [Path, ...] — JSON for .json, py_compile + import for .py.
SCHEMA_FILES: list[Path] = [
    Path(p) for p in _load_slot("""["infra/main.parameters.json", "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/data_agent.json", "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/stage_config.json", "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json", "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/fewshots.json", "fabric_workspace/reports/sales_dashboard.Report/report.json", "src/fabric/notebooks/schema/model_shared_silver.ipynb", "src/fabric/notebooks/schema/model_salesfabric_gold.ipynb", "src/fabric/notebooks/data_agent/data_agent_setup.ipynb"]""", [])
]

# [(tool, "shell command"), ...]
IAC_BUILD_COMMANDS: list[tuple[str, str]] = [
    (tool, cmd)
    for tool, cmd in _load_slot("""[["bicep", "az bicep build --file infra/main.bicep --stdout > /dev/null"]]""", [])
]

# [(label, [cmd, arg, ...]), ...] — each entry is one test runner invocation.
# Empty list means "no test framework detected" (check is skipped).
TEST_COMMANDS: list[tuple[str, list[str]]] = [
    (label, list(cmd))
    for label, cmd in _load_slot("""[]""", [])
]

UI_CONTRACT_REQUIRED: bool = bool(_load_slot("""true""", False))

# Default timeouts in seconds. Intentionally generous; covers cold-start
# bicep CLI and slow CI runners.
ENV_PROBE_TIMEOUT = 30
LINT_TIMEOUT = 120
COMPILE_TIMEOUT = 120
IAC_TIMEOUT = 180
TEST_TIMEOUT = 600


# =============================================================================
# Result type and reporter.
# =============================================================================

@dataclass
class CheckResult:
    name: str
    passed: bool
    remediation: str | None = None
    details: str | None = None
    skipped: bool = False

    @property
    def status(self) -> str:
        if self.skipped:
            return "skipped"
        return "pass" if self.passed else "fail"

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "passed": self.passed,
            "skipped": self.skipped,
            "remediation": self.remediation,
            "details": self.details,
        }


class Reporter:
    """Streaming reporter — human stdout, JSON-per-line stderr."""

    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    def __init__(self, stream_out=sys.stdout, stream_err=sys.stderr) -> None:
        self.out = stream_out
        self.err = stream_err
        self.color = stream_out.isatty()

    def _c(self, code: str, text: str) -> str:
        return f"{code}{text}{self.RESET}" if self.color else text

    def emit(self, result: CheckResult) -> None:
        if result.skipped:
            mark = self._c(self.YELLOW, "SKIP")
        elif result.passed:
            mark = self._c(self.GREEN, "PASS")
        else:
            mark = self._c(self.RED, "FAIL")
        self.out.write(f"  [{mark}] {result.name}\n")
        if result.details:
            self.out.write(self._c(self.DIM, f"        {result.details}\n"))
        if not result.passed and not result.skipped and result.remediation:
            self.out.write(f"        → {result.remediation}\n")
        self.out.flush()
        # Machine-parseable line on stderr.
        self.err.write(json.dumps(result.to_json()) + "\n")
        self.err.flush()

    def summary(self, results: Sequence[CheckResult]) -> None:
        passed = sum(1 for r in results if r.passed and not r.skipped)
        failed = sum(1 for r in results if not r.passed and not r.skipped)
        skipped = sum(1 for r in results if r.skipped)
        self.out.write("\n")
        self.out.write(self._c(self.BOLD, "Validation summary\n"))
        self.out.write(f"  passed:  {passed}\n")
        self.out.write(
            f"  failed:  {self._c(self.RED, str(failed)) if failed else '0'}\n"
        )
        self.out.write(f"  skipped: {skipped}\n")
        if failed:
            self.out.write(
                self._c(self.RED, "\nOne or more checks failed. ")
                + "See VALIDATE.md for remediation guidance.\n"
            )
        else:
            self.out.write(self._c(self.GREEN, "\nAll required checks passed.\n"))


# =============================================================================
# Process helpers.
# =============================================================================

def _run(
    cmd: list[str] | str,
    *,
    cwd: Path | None = None,
    timeout: int = 60,
    shell: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess capturing stdout/stderr as text. Never raises on non-zero;
    callers inspect `returncode` and `stderr` themselves."""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=shell,
        check=False,
    )


def _truncate(text: str, limit: int = 400) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


# =============================================================================
# Cross-layer assertion helpers.
#
# These are generic — the generator inlines parsing logic per cross_layer_pair
# (extracting keys from a Python schema, KQL column references, JSON enum
# values, etc.) and then calls one of the helpers below to assert the
# producer/consumer contract holds.
# =============================================================================

def _assert_one_to_one_map(
    producer_keys: Iterable[str],
    consumer_keys: Iterable[str],
    name: str,
    *,
    require_equality: bool = False,
) -> CheckResult:
    """Assert producer keys ⊆ consumer keys (or equality if requested).

    Use for: mapping tables, registries, factory dispatchers — any place
    where every producer-side key must be served by a consumer-side handler.
    """
    p_set, c_set = set(producer_keys), set(consumer_keys)
    missing = p_set - c_set
    extra = c_set - p_set if require_equality else set()
    if not missing and not extra:
        return CheckResult(name=name, passed=True, details=f"{len(p_set)} keys match")
    parts = []
    if missing:
        parts.append(f"missing in consumer: {sorted(missing)}")
    if extra:
        parts.append(f"extra in consumer: {sorted(extra)}")
    return CheckResult(
        name=name,
        passed=False,
        details="; ".join(parts),
        remediation=(
            "Producer and consumer key sets diverged. Add the missing keys to "
            "the consumer (or remove the orphan keys from the producer) so "
            "every producer entry has a matching handler."
        ),
    )


def _assert_column_references(
    definitions: Iterable[str],
    references: Iterable[str],
    name: str,
) -> CheckResult:
    """Assert all column/field references exist in the producer's definitions.

    Use for: KQL/SQL queries referencing columns from a schema; dashboards
    referencing fields from an entity model; templates referencing variables.
    """
    defs, refs = set(definitions), set(references)
    unknown = refs - defs
    if not unknown:
        return CheckResult(
            name=name,
            passed=True,
            details=f"{len(refs)} references resolved against {len(defs)} definitions",
        )
    return CheckResult(
        name=name,
        passed=False,
        details=f"unknown references: {sorted(unknown)}",
        remediation=(
            "Consumer references columns/fields not defined by the producer. "
            "Either add the missing field to the producer schema or fix the "
            "reference in the consumer."
        ),
    )


def _assert_weighted_sum(
    weights: Iterable[float],
    name: str,
    *,
    expected: float = 1.0,
    tolerance: float = 0.001,
) -> CheckResult:
    """Assert |sum(weights) - expected| < tolerance.

    Use for: scoring formulas, fuzzy classifiers, ensemble weight tables —
    any place a list of weights must sum to a target (typically 1.0).
    """
    weights = list(weights)
    total = sum(weights)
    # `<=` allows tolerance=0 for integer/exact sums; conventional tolerance compare.
    if abs(total - expected) <= tolerance:
        return CheckResult(
            name=name,
            passed=True,
            details=f"sum={total:.6f} (target {expected}, tol {tolerance})",
        )
    return CheckResult(
        name=name,
        passed=False,
        details=f"sum={total:.6f} expected {expected} ± {tolerance}; weights={weights}",
        remediation=(
            "Weights no longer sum to the expected total. Rescale the entries "
            "(divide each by the new sum) or fix the value that drifted."
        ),
    )


def _assert_enum_membership(
    allowed: Iterable[str],
    usages: Iterable[str],
    name: str,
) -> CheckResult:
    """Assert every usage is in the allowed enum set.

    Use for: JSON config referencing enum values declared in code; YAML
    rules referencing entity types; dispatcher switches using enum literals.
    """
    allowed_set, usage_set = set(allowed), set(usages)
    invalid = usage_set - allowed_set
    if not invalid:
        return CheckResult(
            name=name,
            passed=True,
            details=f"{len(usage_set)} usages all valid against {len(allowed_set)} allowed",
        )
    return CheckResult(
        name=name,
        passed=False,
        details=f"invalid enum values: {sorted(invalid)}",
        remediation=(
            "Consumer uses enum values not declared by the producer. Either "
            "add the value to the enum or correct the consumer reference."
        ),
    )


# =============================================================================
# Standard checks.
# =============================================================================

def check_environment() -> CheckResult:
    """Verify the host has the tooling this SA needs.

    Always probes Python ≥ 3.10. Probes bicep when REQUIRES_BICEP, azd when
    REQUIRES_AZD. Missing tools are remediation-friendly errors, not crashes.
    """
    failures: list[str] = []
    details: list[str] = []

    py = sys.version_info
    details.append(f"python={py.major}.{py.minor}.{py.micro}")
    if (py.major, py.minor) < (3, 10):
        failures.append("python < 3.10")

    if REQUIRES_BICEP:
        # `shutil.which("az")` returns `az.cmd` on Windows, so a substring
        # check on the path can't reliably distinguish bicep from az. Resolve
        # them independently and pick the right invocation per tool.
        bicep_path = shutil.which("bicep")
        az_path = shutil.which("az")
        probe_cmd: list[str] | None
        if bicep_path:
            probe_cmd = [bicep_path, "--version"]
        elif az_path:
            probe_cmd = [az_path, "bicep", "version"]
        else:
            failures.append("bicep CLI not found (and `az` not on PATH)")
            probe_cmd = None

        if probe_cmd is not None:
            try:
                proc = _run(probe_cmd, timeout=ENV_PROBE_TIMEOUT)
                details.append("bicep=" + _truncate(proc.stdout or proc.stderr, 80))
            except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
                failures.append(f"bicep probe failed: {exc}")

    if REQUIRES_AZD:
        azd = shutil.which("azd")
        if not azd:
            failures.append("azd CLI not found on PATH")
        else:
            try:
                proc = _run([azd, "version"], timeout=ENV_PROBE_TIMEOUT)
                details.append("azd=" + _truncate(proc.stdout or proc.stderr, 80))
            except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
                failures.append(f"azd probe failed: {exc}")

    if failures:
        return CheckResult(
            name="environment",
            passed=False,
            details="; ".join(failures + details),
            remediation=(
                "Install the missing tools. Python 3.10+ is required. "
                "Install bicep with `az bicep install`. Install azd from "
                "https://aka.ms/azd-install."
            ),
        )
    return CheckResult(name="environment", passed=True, details="; ".join(details))


def check_lint() -> CheckResult:
    """Run each detected lint invocation; aggregate results."""
    if not LINT_INVOCATIONS:
        return CheckResult(
            name="lint",
            passed=True,
            skipped=True,
            remediation="no lint tool detected during architecture survey",
        )
    failures: list[str] = []
    details: list[str] = []
    for label, cmd in LINT_INVOCATIONS:
        try:
            proc = _run(cmd, cwd=REPO_ROOT, timeout=LINT_TIMEOUT)
        except subprocess.TimeoutExpired:
            failures.append(f"{label}: timed out after {LINT_TIMEOUT}s")
            continue
        except FileNotFoundError:
            failures.append(f"{label}: tool not found ({cmd[0]})")
            continue
        if proc.returncode == 0:
            details.append(f"{label}: ok")
        else:
            failures.append(
                f"{label} exit={proc.returncode}: " + _truncate(proc.stderr or proc.stdout)
            )
    if failures:
        return CheckResult(
            name="lint",
            passed=False,
            details=" | ".join(failures),
            remediation=(
                "Lint reported style issues. Run the failing tool locally "
                "and fix reported lines, or add an explicit ignore pragma "
                "if the warning is a false positive."
            ),
        )
    return CheckResult(name="lint", passed=True, details=" | ".join(details))


def check_compile() -> CheckResult:
    """Compile every detected source target (py_compile, tsc --noEmit, etc.)."""
    if not COMPILE_TARGETS:
        return CheckResult(
            name="compile",
            passed=True,
            skipped=True,
            remediation="no compile targets detected during architecture survey",
        )
    failures: list[str] = []
    details: list[str] = []
    for path, base_cmd in COMPILE_TARGETS:
        target = (REPO_ROOT / path).resolve() if not path.is_absolute() else path
        if not target.exists():
            details.append(f"{path}: not present (skipped)")
            continue
        # py_compile has its own discovery semantics: walk the dir and compile each .py.
        if base_cmd[-2:] == ["-m", "py_compile"]:
            py_files = list(target.rglob("*.py")) if target.is_dir() else [target]
            if not py_files:
                details.append(f"{path}: no .py files")
                continue
            cmd = list(base_cmd) + [str(f) for f in py_files]
        else:
            cmd = list(base_cmd) + [str(target)]
        try:
            proc = _run(cmd, cwd=REPO_ROOT, timeout=COMPILE_TIMEOUT)
        except subprocess.TimeoutExpired:
            failures.append(f"{path}: compile timed out after {COMPILE_TIMEOUT}s")
            continue
        except FileNotFoundError:
            failures.append(f"{path}: compiler not found ({cmd[0]})")
            continue
        if proc.returncode == 0:
            details.append(f"{path}: ok")
        else:
            failures.append(
                f"{path} exit={proc.returncode}: " + _truncate(proc.stderr or proc.stdout)
            )
    if failures:
        return CheckResult(
            name="compile",
            passed=False,
            details=" | ".join(failures),
            remediation=(
                "Source no longer compiles. Open the failing file at the "
                "reported line and fix the syntax/type error before redeploying."
            ),
        )
    return CheckResult(name="compile", passed=True, details=" | ".join(details))


def check_schema_integrity() -> CheckResult:
    """Verify every declared schema file still parses / imports cleanly."""
    if not SCHEMA_FILES:
        return CheckResult(
            name="schema_integrity",
            passed=True,
            skipped=True,
            remediation="no schema files detected during architecture survey",
        )
    failures: list[str] = []
    details: list[str] = []
    for rel in SCHEMA_FILES:
        target = (REPO_ROOT / rel).resolve() if not rel.is_absolute() else rel
        if not target.exists():
            failures.append(f"{rel}: missing")
            continue
        suffix = target.suffix.lower()
        if suffix in {".json", ".ipynb"}:
            try:
                with target.open("r", encoding="utf-8") as fh:
                    json.load(fh)
                details.append(f"{rel}: json ok")
            except (OSError, json.JSONDecodeError) as exc:
                failures.append(f"{rel}: json parse error — {exc}")
        elif suffix == ".py":
            proc = _run(
                [sys.executable, "-m", "py_compile", str(target)],
                cwd=REPO_ROOT,
                timeout=COMPILE_TIMEOUT,
            )
            if proc.returncode != 0:
                failures.append(
                    f"{rel}: py_compile failed — " + _truncate(proc.stderr or proc.stdout)
                )
                continue
            # Schema modules often import from elsewhere in the repo
            # (e.g., `from src.models.base import BaseEvent`). Put REPO_ROOT
            # on sys.path so those imports resolve; restore sys.path on exit
            # whether the import succeeded or raised.
            sys.path.insert(0, str(REPO_ROOT))
            try:
                spec = importlib.util.spec_from_file_location(target.stem, target)
                if spec is None or spec.loader is None:
                    failures.append(f"{rel}: cannot build import spec")
                    continue
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)  # type: ignore[union-attr]
                details.append(f"{rel}: import ok")
            except Exception as exc:  # noqa: BLE001 — import-time surface is broad
                failures.append(f"{rel}: import failed — {exc!r}")
            finally:
                # Pop the entry we inserted. Guard against the unlikely case
                # of another caller mutating sys.path concurrently.
                try:
                    sys.path.remove(str(REPO_ROOT))
                except ValueError:
                    pass
        else:
            details.append(f"{rel}: unsupported suffix '{suffix}', skipped")
    if failures:
        return CheckResult(
            name="schema_integrity",
            passed=False,
            details=" | ".join(failures),
            remediation=(
                "A schema file no longer parses or imports. Restore the file "
                "to a syntactically valid state — the failure message above "
                "names the file and exact error."
            ),
        )
    return CheckResult(name="schema_integrity", passed=True, details=" | ".join(details))


# =============================================================================
# Cross-layer checks.
#
# The skill generator emits one `_check_<pair_name>()` per cross_layer_pair
# in the architecture survey, then registers it via CROSS_LAYER_CHECKS.append.
# Each `_check_*` function is responsible for parsing its own producer/consumer
# files (the parsing logic is pair-specific) and then calling the appropriate
# `_assert_*` helper above.
#
# Until a generator pass happens, both blocks below are comment-only no-ops
# and CROSS_LAYER_CHECKS remains empty.
# =============================================================================

def _read_text_rel(rel: str, *, encoding: str = "utf-8") -> str:
    return (REPO_ROOT / rel).read_text(encoding=encoding)


def _read_json_rel(rel: str):
    with (REPO_ROOT / rel).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                yield key
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def _check_bicep_outputs_to_install_env() -> CheckResult:
    bicep = _read_text_rel("infra/main.bicep")
    install = _read_text_rel("infra/scripts/fabric/install_udf_solution.py")
    outputs = {
        name for name in [
            "AZURE_FABRIC_CAPACITY_NAME",
            "AZURE_FABRIC_CAPACITY_ADMINISTRATORS",
            "SOLUTION_SUFFIX",
        ]
        if f"output {name}" in bicep
    }
    env_reads = {name for name in outputs if name in install}
    return _assert_one_to_one_map(
        outputs,
        env_reads,
        name="cross_layer:bicep-outputs-to-install-env",
        require_equality=True,
    )


def _check_fabric_parameter_mappings() -> CheckResult:
    parameter_yml = _read_text_rel("fabric_workspace/parameter.yml")
    datasource = _read_text_rel(
        "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json"
    )
    required = {
        "$items.Lakehouse.maag_bronze.$id",
        "$items.Lakehouse.maag_silver.$id",
        "$items.Lakehouse.maag_gold.$id",
        "$items.Lakehouse.maag_gold.$sqlendpoint",
    }
    found = {value for value in required if value in parameter_yml}
    if "a3e8aa1e-8466-9f89-4ce5-fee786c1a3bb" in parameter_yml and "a3e8aa1e-8466-9f89-4ce5-fee786c1a3bb" in datasource:
        found.add("data-agent-maag-gold-artifact-id")
        required.add("data-agent-maag-gold-artifact-id")
    return _assert_one_to_one_map(
        required,
        found,
        name="cross_layer:fabric-parameter-mappings",
        require_equality=True,
    )


def _check_data_agent_fewshots_reference_datasource() -> CheckResult:
    datasource = _read_json_rel(
        "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json"
    )
    fewshots = _read_text_rel(
        "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/fewshots.json"
    )
    definitions = set(_walk_strings(datasource))
    references = {
        key for key in ["CustomerId", "OrderId", "ProductName", "Quantity"]
        if key in fewshots
    }
    return _assert_column_references(
        definitions,
        references,
        name="cross_layer:data-agent-fewshots-to-datasource",
    )


def _check_report_visual_fields_reference_datasource() -> CheckResult:
    datasource = _read_json_rel(
        "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json"
    )
    report = _read_text_rel("fabric_workspace/reports/sales_dashboard.Report/report.json")
    definitions = set(_walk_strings(datasource))
    references = {key for key in ["ProductName", "Quantity"] if key in report}
    return _assert_column_references(
        definitions,
        references,
        name="cross_layer:report-fields-to-datasource",
    )

CROSS_LAYER_CHECKS: list[Callable[[], CheckResult]] = []

CROSS_LAYER_CHECKS.append(_check_bicep_outputs_to_install_env)
CROSS_LAYER_CHECKS.append(_check_fabric_parameter_mappings)
CROSS_LAYER_CHECKS.append(_check_data_agent_fewshots_reference_datasource)
CROSS_LAYER_CHECKS.append(_check_report_visual_fields_reference_datasource)


def check_cross_layer() -> list[CheckResult]:
    """Run every registered cross-layer assertion. Returns one result per pair.

    Empty list when no cross_layer_pairs were detected — main() treats that
    as a single skipped check for reporting purposes.
    """
    if not CROSS_LAYER_CHECKS:
        return [
            CheckResult(
                name="cross_layer",
                passed=True,
                skipped=True,
                remediation="no cross_layer_pairs detected during architecture survey",
            )
        ]
    return [fn() for fn in CROSS_LAYER_CHECKS]


# =============================================================================
# UI contract checks.
#
# The skill generator emits one `_check_ui_<surface>()` per UI/frontend contract
# risk found in `ui_surface.*` and `validation_capability.cross_layer_pairs`.
# Typical generated checks cover two categories:
#   1. user-facing display labels/copy that should change for the adaptation;
#   2. contract-supporting frontend constants, client-side parser/type expectations,
#      API payloads, and backend/API/internal schema keys that should stay aligned.
# When the survey found UI surfaces, `UI_CONTRACT_REQUIRED` makes an empty
# registration set fail because skipped UI contract validation would hide drift.
#
# Multilingual/i18n/localization support is out of scope for this validator; UI
# checks only cover generic display labels/copy and backend/frontend contract stability.
# =============================================================================

def _check_ui_report_copy_and_contract() -> CheckResult:
    report = _read_text_rel("fabric_workspace/reports/sales_dashboard.Report/report.json")
    required_label_groups = {
        "report page title": ("Sales Analysis", "Renewable Energy Portfolio"),
        "overview title": ("Sales Overview", "Renewable Portfolio Overview"),
        "filter group": ("Filter Pane", "Portfolio Filters"),
        "top product visual": (
            "Top 5 Selling Products by Quantity",
            "Top Renewable Products by Delivered Quantity",
        ),
    }
    required_contract = ["ProductName", "Quantity"]
    missing = [
        label
        for label, options in required_label_groups.items()
        if not any(option in report for option in options)
    ]
    missing += [item for item in required_contract if item not in report]
    if missing:
        return CheckResult(
            name="ui_contract:power-bi-report-copy-and-fields",
            passed=False,
            details=f"missing report strings or field bindings: {missing}",
            remediation=(
                "Restore the report display text or update both the semantic/report "
                "field binding and datasource contract intentionally with matching validation."
            ),
        )
    return CheckResult(
        name="ui_contract:power-bi-report-copy-and-fields",
        passed=True,
        details="report display labels and ProductName/Quantity bindings are present",
    )


def _check_ui_data_agent_copy_and_contract() -> CheckResult:
    stage = _read_text_rel(
        "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/stage_config.json"
    ).lower()
    fewshots = _read_text_rel(
        "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/fewshots.json"
    )
    datasource = _read_text_rel(
        "fabric_workspace/Data Agent for UDF.DataAgent/Files/Config/draft/lakehouse-tables-maag_gold/datasource.json"
    )
    required_stage_groups = {
        "synthetic-data disclaimer": ("synthetically generated", "fully synthetic"),
        "chart limitation": ("do not offer charts",),
        "root-cause limitation": ("root cause analysis",),
    }
    required_contract = ["maag_gold", "CustomerId", "OrderId", "ProductName", "Quantity"]
    missing = [
        label
        for label, options in required_stage_groups.items()
        if not any(option in stage for option in options)
    ]
    missing += [item for item in required_contract if item not in datasource]
    fewshots_lower = fewshots.lower()
    has_sales_examples = "customer base" in fewshots_lower and "sales performance" in fewshots_lower
    has_renewable_examples = (
        "renewable offtaker" in fewshots_lower
        and "renewable products" in fewshots_lower
        and "settlement invoices" in fewshots_lower
    )
    if not (has_sales_examples or has_renewable_examples):
        missing.append("representative Data Agent few-shot questions")
    if missing:
        return CheckResult(
            name="ui_contract:data-agent-copy-and-datasource",
            passed=False,
            details=f"missing Data Agent UI/contract signal: {missing}",
            remediation=(
                "Update Data Agent display copy separately from datasource schema/table/column "
                "keys, or intentionally migrate both sides with matching checks."
            ),
        )
    return CheckResult(
        name="ui_contract:data-agent-copy-and-datasource",
        passed=True,
        details="Data Agent copy and stable datasource keys are present",
    )


def _check_ui_theme_branding() -> CheckResult:
    theme_path = REPO_ROOT / "reports/theme.json"
    try:
        theme = json.loads(theme_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return CheckResult(
            name="ui_contract:theme-branding",
            passed=False,
            details=f"reports/theme.json did not parse: {exc!r}",
            remediation="Restore valid JSON in reports/theme.json or update the theme parser check if the file format intentionally changed.",
        )
    if theme.get("name") != "maag-theme":
        return CheckResult(
            name="ui_contract:theme-branding",
            passed=False,
            details=f"unexpected theme name: {theme.get('name')!r}",
            remediation="Keep display branding changes intentional and update report theme references consistently.",
        )
    return CheckResult(
        name="ui_contract:theme-branding",
        passed=True,
        details="reports/theme.json keeps maag-theme branding signal",
    )

UI_CONTRACT_CHECKS: list[Callable[[], CheckResult]] = []

UI_CONTRACT_CHECKS.append(_check_ui_report_copy_and_contract)
UI_CONTRACT_CHECKS.append(_check_ui_data_agent_copy_and_contract)
UI_CONTRACT_CHECKS.append(_check_ui_theme_branding)


def check_ui_contract() -> list[CheckResult]:
    """Run every registered UI/frontend contract assertion."""
    if not UI_CONTRACT_CHECKS:
        if UI_CONTRACT_REQUIRED:
            return [
                CheckResult(
                    name="ui_contract",
                    passed=False,
                    details=(
                        "UI surfaces were found but no UI contract checks were generated"
                    ),
                    remediation=(
                        "Re-run skill generation so each surveyed ui_surface risk "
                        "emits a UI_CONTRACT_CHECKS registration. Only remove the "
                        "ui_surface inventory when the SA truly has no UI/frontend "
                        "surface evidence, build command, or smoke check."
                    ),
                )
            ]
        return [
            CheckResult(
                name="ui_contract",
                passed=True,
                skipped=True,
                remediation=(
                    "no UI/frontend surfaces detected during architecture survey; "
                    "ui_contract skipped"
                ),
            )
        ]
    return [fn() for fn in UI_CONTRACT_CHECKS]


# =============================================================================
# IaC build & tests.
# =============================================================================

def check_iac_build() -> list[CheckResult]:
    """Run every IaC build/validate command. One CheckResult per command."""
    if not IAC_BUILD_COMMANDS:
        return [
            CheckResult(
                name="iac_build",
                passed=True,
                skipped=True,
                remediation="no IaC tools detected during architecture survey",
            )
        ]
    results: list[CheckResult] = []
    for tool, cmd in IAC_BUILD_COMMANDS:
        name = f"iac_build:{tool}"
        try:
            # shell=True is intentional: survey-emitted commands embed shell
            # redirects (e.g., `> /dev/null`) that require shell expansion.
            # Validator host is expected to be POSIX (Linux/macOS).
            proc = _run(cmd, cwd=REPO_ROOT, timeout=IAC_TIMEOUT, shell=True)
        except subprocess.TimeoutExpired:
            results.append(
                CheckResult(
                    name=name,
                    passed=False,
                    details=f"timed out after {IAC_TIMEOUT}s",
                    remediation=(
                        "IaC build exceeded timeout. Run the command manually "
                        "to inspect — it may be downloading modules or the "
                        "template may have a slow expansion."
                    ),
                )
            )
            continue
        if proc.returncode == 0:
            results.append(CheckResult(name=name, passed=True, details="ok"))
        else:
            results.append(
                CheckResult(
                    name=name,
                    passed=False,
                    details=f"exit={proc.returncode}: " + _truncate(proc.stderr or proc.stdout),
                    remediation=(
                        "IaC template failed to build. Open the file/line "
                        "named in the error and fix the resource definition "
                        "before redeploying."
                    ),
                )
            )
    return results


def check_tests() -> CheckResult:
    """Run every configured test command; aggregate failures."""
    if not TEST_COMMANDS:
        return CheckResult(
            name="tests",
            passed=True,
            skipped=True,
            remediation="no test framework detected during architecture survey",
        )
    failures: list[str] = []
    details: list[str] = []
    for label, cmd in TEST_COMMANDS:
        try:
            proc = _run(cmd, cwd=REPO_ROOT, timeout=TEST_TIMEOUT)
        except subprocess.TimeoutExpired:
            failures.append(f"{label}: timed out after {TEST_TIMEOUT}s")
            continue
        except FileNotFoundError:
            failures.append(f"{label}: test runner not found ({cmd[0]})")
            continue
        if proc.returncode == 0:
            details.append(f"{label}: ok")
        else:
            failures.append(
                f"{label} exit={proc.returncode}: " + _truncate(proc.stderr or proc.stdout)
            )
    if failures:
        return CheckResult(
            name="tests",
            passed=False,
            details=" | ".join(failures),
            remediation=(
                "One or more test runners failed. Read the failing assertions "
                "in the runner output above and fix the regression. If the "
                "runner is missing, install it (e.g., `pip install pytest`) "
                "or ensure it is on PATH in the validation environment."
            ),
        )
    return CheckResult(name="tests", passed=True, details=" | ".join(details))


# =============================================================================
# Self-test mode — exercises helpers against synthetic fixtures.
# =============================================================================

def _self_test() -> int:
    """Validate the validator's own machinery. Touches no SA files."""
    failures: list[str] = []

    def _expect(label: str, result: CheckResult, *, want_pass: bool) -> None:
        ok = result.passed if want_pass else (not result.passed)
        if not ok:
            failures.append(
                f"{label}: expected {'pass' if want_pass else 'fail'} but got "
                f"{'pass' if result.passed else 'fail'} — {result.details!r}"
            )

    # one-to-one map
    _expect(
        "1to1 superset",
        _assert_one_to_one_map({"a", "b"}, {"a", "b", "c"}, "test"),
        want_pass=True,
    )
    _expect(
        "1to1 missing",
        _assert_one_to_one_map({"a", "b", "x"}, {"a", "b"}, "test"),
        want_pass=False,
    )
    _expect(
        "1to1 equality strict",
        _assert_one_to_one_map(
            {"a", "b"}, {"a", "b", "c"}, "test", require_equality=True
        ),
        want_pass=False,
    )

    # column-references
    _expect(
        "column refs valid",
        _assert_column_references({"id", "name"}, {"id"}, "test"),
        want_pass=True,
    )
    _expect(
        "column refs invalid",
        _assert_column_references({"id", "name"}, {"id", "ghost"}, "test"),
        want_pass=False,
    )

    # weighted-sum
    _expect(
        "weights sum to 1",
        _assert_weighted_sum([0.25, 0.25, 0.5], "test"),
        want_pass=True,
    )
    _expect(
        "weights drift",
        _assert_weighted_sum([0.25, 0.25, 0.4], "test"),
        want_pass=False,
    )
    _expect(
        "weights custom target",
        _assert_weighted_sum([1, 2, 3], "test", expected=6.0, tolerance=0.0001),
        want_pass=True,
    )

    # enum-membership
    _expect(
        "enum valid",
        _assert_enum_membership({"red", "green"}, {"red"}, "test"),
        want_pass=True,
    )
    _expect(
        "enum invalid",
        _assert_enum_membership({"red", "green"}, {"red", "blue"}, "test"),
        want_pass=False,
    )

    # ui_contract required-vs-skipped behavior. An empty generated registration
    # set is acceptable only when the survey found no UI surfaces.
    global UI_CONTRACT_REQUIRED, UI_CONTRACT_CHECKS
    saved_ui_contract_required = UI_CONTRACT_REQUIRED
    saved_ui_contract_checks = UI_CONTRACT_CHECKS
    try:
        UI_CONTRACT_CHECKS = []
        UI_CONTRACT_REQUIRED = False
        result = check_ui_contract()[0]
        _expect(
            "ui_contract empty not required",
            result,
            want_pass=True,
        )
        if not result.skipped:
            failures.append("ui_contract empty not required: expected skipped result")
        UI_CONTRACT_REQUIRED = True
        result = check_ui_contract()[0]
        _expect(
            "ui_contract empty required",
            result,
            want_pass=False,
        )
        if result.skipped:
            failures.append("ui_contract empty required: must fail, not skip")
        UI_CONTRACT_CHECKS = [
            lambda: CheckResult(name="ui_contract:synthetic", passed=True)
        ]
        result = check_ui_contract()[0]
        _expect(
            "ui_contract registered required",
            result,
            want_pass=True,
        )
        if result.skipped or result.name != "ui_contract:synthetic":
            failures.append(
                "ui_contract registered required: expected generated check result"
            )
    finally:
        UI_CONTRACT_REQUIRED = saved_ui_contract_required
        UI_CONTRACT_CHECKS = saved_ui_contract_checks

    # schema_integrity against a tempdir fixture — exercises both the .json
    # and .py branches by driving check_schema_integrity() with a swapped-in
    # SCHEMA_FILES list. This catches regressions in the .py import path
    # (e.g., the REPO_ROOT-on-sys.path contract).
    import textwrap

    with tempfile.TemporaryDirectory() as tmp:
        good_json = Path(tmp) / "good.json"
        bad_json = Path(tmp) / "bad.json"
        good_py = Path(tmp) / "good_schema.py"
        bad_py = Path(tmp) / "bad_schema.py"
        good_json.write_text('{"ok": true}', encoding="utf-8")
        bad_json.write_text("{not json", encoding="utf-8")
        good_py.write_text(
            textwrap.dedent(
                '''
                FIELDS = ["id", "name"]


                def describe():
                    return FIELDS
                '''
            ).lstrip(),
            encoding="utf-8",
        )
        # Syntax error — must fail py_compile.
        bad_py.write_text("def foo(:\n", encoding="utf-8")

        global SCHEMA_FILES
        saved_schema_files = SCHEMA_FILES
        try:
            # Both good fixtures together — single result, expected pass.
            SCHEMA_FILES = [good_json, good_py]
            _expect(
                "schema_integrity good (.json + .py)",
                check_schema_integrity(),
                want_pass=True,
            )
            # Bad JSON in isolation — expected fail.
            SCHEMA_FILES = [bad_json]
            _expect(
                "schema_integrity bad .json",
                check_schema_integrity(),
                want_pass=False,
            )
            # Bad Python in isolation — expected fail (py_compile catches it).
            SCHEMA_FILES = [bad_py]
            _expect(
                "schema_integrity bad .py",
                check_schema_integrity(),
                want_pass=False,
            )
        finally:
            SCHEMA_FILES = saved_schema_files

    if failures:
        sys.stderr.write("self-test FAILED:\n")
        for f in failures:
            sys.stderr.write(f"  - {f}\n")
        return 1
    sys.stdout.write("self-test: OK (all helpers behave correctly)\n")
    return 0


# =============================================================================
# Main entry point.
# =============================================================================

# (name, callable returning CheckResult or list[CheckResult])
_CHECK_REGISTRY: list[tuple[str, Callable[[], CheckResult | list[CheckResult]]]] = [
    ("environment", check_environment),
    ("lint", check_lint),
    ("compile", check_compile),
    ("schema_integrity", check_schema_integrity),
    ("cross_layer", check_cross_layer),
    ("ui_contract", check_ui_contract),
    ("iac_build", check_iac_build),
    ("tests", check_tests),
]


def _flatten(results: CheckResult | list[CheckResult]) -> list[CheckResult]:
    if isinstance(results, list):
        return results
    return [results]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=f"validate.py ({SKILL_NAME})",
        description="Architecture-aware validator. See VALIDATE.md for details.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run an in-memory test of the validator's own helpers and exit",
    )
    parser.add_argument(
        "--check",
        action="append",
        default=[],
        choices=[name for name, _ in _CHECK_REGISTRY],
        help="run only this check (repeatable). Default: run every check.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.self_test:
        return _self_test()

    reporter = Reporter()
    selected = args.check or [name for name, _ in _CHECK_REGISTRY]
    reporter.out.write(
        f"Validating {SKILL_NAME} (surface={PUBLISH_SURFACE}, sa={SA_NAME})\n"
    )

    all_results: list[CheckResult] = []
    for name, fn in _CHECK_REGISTRY:
        if name not in selected:
            continue
        try:
            results = _flatten(fn())
        except Exception as exc:  # noqa: BLE001 — surface unexpected breakage
            results = [
                CheckResult(
                    name=name,
                    passed=False,
                    details=f"check raised {type(exc).__name__}: {exc}",
                    remediation=(
                        "The check itself errored. This usually means the "
                        "validator's slot data is malformed. Re-run skill "
                        "generation or open VALIDATE.md → Self-test."
                    ),
                )
            ]
        for r in results:
            reporter.emit(r)
            all_results.append(r)

    reporter.summary(all_results)
    return 0 if all(r.passed for r in all_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
