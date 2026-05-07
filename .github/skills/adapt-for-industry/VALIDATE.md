# Validate `adapt-for-industry` for `unified-data-foundation-with-fabric` (publish surface: `azd-native`)

Architecture-aware sanity checks that run after the skill mutates files in
`unified-data-foundation-with-fabric`. The validator catches breakage **before** you redeploy.

## When to run

Run `validate.py` whenever any of these is true:

- The skill workflow just finished mutating files.
- You hand-edited config, schema, or IaC files since the last successful run.
- You are about to redeploy (`azd up`, `azd deploy`, or equivalent).

It is safe to run `validate.py` at any other time too — every check is
read-only against your repo (subprocess invocations of lint / compile /
IaC build only read source).

## How to run

From the SA repo root:

```bash
python .github/skills/adapt-for-industry/validate.py
```

To run a single check (repeatable):

```bash
python .github/skills/adapt-for-industry/validate.py --check compile --check schema_integrity
```

Available check names: `environment`, `lint`, `compile`, `schema_integrity`,
`cross_layer`, `ui_contract`, `iac_build`, `tests`.

## What it checks

The validator runs the checks below. Checks for which no capability was
detected during architecture survey are skipped (and skipped counts as
passed for exit-code purposes). The exception is `ui_contract`, because a
surveyed UI/frontend surface needs an explicit contract-drift signal.

`ui_contract` behavior:

- **Required** when `ui_surface.evidence.*`, `ui_surface.build_commands`, or
  `ui_surface.smoke_checks` contains any surveyed UI/frontend surface.
- **Skipped** only when the survey found no UI/frontend surfaces and no
  generated UI contract checks exist.
- **Failed** when required checks were not generated, or when a generated check
  finds UI contract drift between display labels/copy, frontend parser/type
  expectations, API payloads, and backend/API/internal schema keys.

- **environment** — checks Python and required Azure tooling for the azd-native/Bicep surface.
- **compile** — py-compiles Fabric deployment scripts under `infra/scripts/fabric`.
- **schema_integrity** — parses Fabric/Data Agent/report JSON and selected source notebooks.
- **cross_layer** — verifies Bicep output/script environment alignment, Fabric parameter mappings, Data Agent query references, and report field bindings.
- **ui_contract** — verifies Fabric report/Data Agent display surfaces remain separate from stable lakehouse/data-source contract keys.
- **iac_build** — runs `az bicep build --file infra/main.bicep --stdout > /dev/null`.
- **lint** — skipped: no repository lint config was detected by the survey.
- **tests** — skipped: no repository test framework config was detected by the survey.
## Reading the output

`validate.py` writes two streams:

| Stream | Audience | Format |
|--------|----------|--------|
| `stdout` | humans | colorized pass/fail/skip lines and a summary table |
| `stderr` | tools | one JSON object per check (newline-delimited) |

Each result has:

- `name` — short check identifier (`environment`, `lint`, …).
- `status` — `pass`, `fail`, or `skipped`.
- `details` — short factual context (timing, exit codes, key counts).
- `remediation` — present on failures; one-line hint pointing at the fix.

Exit codes:

- **0** — every check passed (or was skipped because the SA has no such
  capability).
- **1** — at least one check failed.

To capture machine-readable results in CI, redirect stderr to a file:

```bash
python .github/skills/adapt-for-industry/validate.py 2> validate-results.jsonl
```

Each line in `validate-results.jsonl` is a complete JSON object — easy to
post-process with `jq`.

## Common failures and remediation

The validator is a contract-enforcer, not a fixer. When a check fails it
prints a one-line remediation hint; the table below expands those hints
with general guidance. None of the entries below are SA-specific — they
apply to any failure of that check kind.

### `environment` failed

- **Python version too old** — install Python 3.10+ and re-run.
- **`bicep` not on PATH** — `az bicep install` (Azure CLI ships it) or
  install the standalone CLI from
  https://github.com/Azure/bicep/releases.
- **`azd` not on PATH** — install Azure Developer CLI from
  https://aka.ms/azd-install.

### `lint` failed

The configured lint tool reported style issues. Run the tool locally with
the same arguments shown in the failure details to see the full report,
then either fix the offending lines or, if the warning is a false
positive, add an explicit ignore pragma in the project's lint config.

### `compile` failed

A source file no longer parses or type-checks. Open the file at the line
named in the failure detail. Common causes after a skill mutation:

- A reference (import, type, variable) was removed but the call sites
  weren't updated.
- The mutated file introduces a syntax error (mismatched brackets,
  missing colons, etc.).
- A new dependency was referenced before it was declared in
  `pyproject.toml` / `requirements.txt` / `package.json`.

### `schema_integrity` failed

A JSON schema file no longer parses, or a Python schema module fails to
import. The failure detail names the file and the exact error. For JSON,
check for trailing commas or unbalanced braces. For Python, the most
common cause is an `ImportError` because a referenced module was renamed
or removed.

### `cross_layer` failed

The highest-value signal. A producer/consumer contract drifted — for
example, a query references a column that no longer exists in the
schema, or a config file uses an enum value the code doesn't know about.
Each cross-layer assertion has one of four kinds, each with its own
remediation pattern:

| Kind | Failure means | Fix |
|------|---------------|-----|
| `1to1-map` | a producer key has no consumer handler (or vice versa) | add the missing handler, or remove the orphan key |
| `column-references` | a query/template references a field the producer doesn't define | add the field upstream, or correct the reference |
| `weighted-sum` | weights no longer sum to the expected total | rescale the entries, or fix the value that drifted |
| `enum-membership` | a usage points at an enum value not declared by the producer | add the value to the enum, or fix the usage |

### `ui_contract` failed

This check reports UI contract drift between frontend display surfaces and
backend/API/internal contracts. It also fails when the survey found UI
surfaces but the generated validator contains no UI contract checks.

The adapted UI drifted from a backend/frontend contract. Common causes:

- The skill was generated from a `ui_surface` inventory but no
  `UI_CONTRACT_CHECKS` registrations were emitted.
- A display label or copy change also renamed a backend/API/internal schema key.
- A client-side parser/type, generated client, or frontend constant no longer
  matches the API payload expectation.
- A form field, review step, route, component, or validation message still uses
  old use-case or industry terminology after the data/config update.
- A frontend build or UI smoke route was not run after UI changes.

Fix by restoring stable backend/API/internal schema keys, updating display
labels/copy separately, or intentionally updating both backend and frontend
contract files with matching validation coverage. Multilingual/i18n/localization
support is out of scope; do not treat translation into other languages as a
validator requirement.

### `iac_build` failed

The IaC tool (Bicep, Terraform, Pulumi, …) refused the template. The
failure detail includes the tool's exit code and the first ~400 chars of
its output. Open the file/line named in the error and fix the resource
definition before redeploying.

### `tests` failed

The SA's test suite reported failures. Read the failing assertions and
fix the regression — the validator does not retry. If the failure looks
environmental (network, credential, missing fixture), reproduce locally
before assuming a code regression.

## Self-test

To validate the validator itself (helpful when you suspect the script's
own data is wrong rather than the SA's):

```bash
python .github/skills/adapt-for-industry/validate.py --self-test
```

Self-test exercises every cross-layer assertion helper against in-memory
fixtures (no SA files are read). Exit code is 0 when every helper behaves
correctly, 1 otherwise. This is useful when:

- You believe the validator is reporting a false positive — self-test
  rules out a bug in the helpers themselves.
- You modified `validate.py` directly and want to confirm the helpers
  still work.
- You're debugging the substitution output of the skill generator.

## Optional: pre-commit hook integration

This is **opt-in** and not required by the skill. If you'd like the
validator to run automatically on every commit, add this snippet to
`.pre-commit-config.yaml` at the SA repo root:

```yaml
repos:
  - repo: local
    hooks:
      - id: sa-validate-adapt-for-industry
        name: validate adapt-for-industry
        entry: python .github/skills/adapt-for-industry/validate.py
        language: system
        pass_filenames: false
        stages: [pre-commit]
```

Then install the hook with `pre-commit install`. Skip this section if
you don't already use pre-commit — the validator is fully usable as a
standalone command.
