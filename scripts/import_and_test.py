#!/usr/bin/env python3
"""Import every workflow into a local n8n, and optionally execute the demo branch.

The default n8n binary is the one installed for this workspace. GitHub Actions
passes N8N_BIN after `npm install n8n`. Execution is off in CI (`--import-only`)
because it needs a few minutes and a local credential-scope seed. The seed does
not touch workflow JSON. It only lets this empty n8n accept placeholder
credential ids during `n8n execute`.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog.json"

DEFAULT_NODE = "/tmp/node-v24.22.3-linux-x64/bin/node"
DEFAULT_N8N = "/tmp/n8n-runner/node_modules/n8n/bin/n8n"


def n8n_env(user_folder: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "N8N_USER_FOLDER": str(user_folder),
            "N8N_ENCRYPTION_KEY": "portfolio-demo-key-not-a-secret",
            "N8N_DIAGNOSTICS_ENABLED": "false",
            "N8N_PERSONALIZATION_ENABLED": "false",
            "N8N_VERSION_NOTIFICATIONS_ENABLED": "false",
            "N8N_TEMPLATES_ENABLED": "false",
            "N8N_HIRING_BANNER_ENABLED": "false",
        }
    )
    return env


def run(cmd: list[str], env: dict[str, str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, env=env, text=True, capture_output=True, check=check)


def ensure_owner_scope(user_folder: Path) -> str:
    db_path = user_folder / ".n8n" / "database.sqlite"
    if not db_path.exists():
        raise SystemExit(f"n8n database was not created at {db_path}")
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    user_id = cursor.execute("SELECT id FROM user LIMIT 1").fetchone()
    if user_id is None:
        raise SystemExit("n8n did not create an owner user")
    cursor.execute(
        "INSERT OR IGNORE INTO scope (slug, displayName, description) VALUES (?, ?, ?)",
        ("credential:use", "Use Credential", "Allows the portfolio demo user to execute workflows that reference placeholder credentials"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO role_scope (roleSlug, scopeSlug) VALUES ('global:owner', 'credential:use')"
    )
    connection.commit()
    connection.close()
    return user_id[0]


def collect_workflows() -> list[dict]:
    catalog = json.loads(CATALOG_PATH.read_text())
    workflows = []
    for item in catalog["workflows"]:
        path = ROOT / item["path"] / "workflow.json"
        workflows.append(json.loads(path.read_text()))
    return workflows


def parse_execution(stdout: str) -> dict | None:
    start = stdout.find("\n{")
    if start < 0 and stdout.startswith("{"):
        start = 0
    elif start >= 0:
        start += 1
    else:
        return None
    try:
        return json.loads(stdout[start:])
    except json.JSONDecodeError:
        return None


def execution_ok(payload: dict | None) -> tuple[bool, str]:
    if not payload:
        return False, "no JSON result"
    result = payload.get("data", {}).get("resultData", {})
    if result.get("error"):
        message = result["error"].get("message") if isinstance(result["error"], dict) else str(result["error"])
        return False, message
    run_data = result.get("runData") or {}
    if "Package demo result" not in run_data:
        return False, "demo branch did not run"
    try:
        item = run_data["Package demo result"][0]["data"]["main"][0][0]["json"]
    except (KeyError, IndexError, TypeError):
        return False, "demo result payload missing"
    if item.get("status") != "demo_ready" or not str(item.get("summary") or "").strip():
        return False, "demo result was not demo_ready"
    return True, "executed"


def update_catalog(statuses: dict[str, str]) -> None:
    catalog = json.loads(CATALOG_PATH.read_text())
    for item in catalog["workflows"]:
        if item["id"] in statuses:
            item["test_status"] = statuses[item["id"]]
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--import-only", action="store_true")
    parser.add_argument("--n8n-node", default=os.environ.get("N8N_NODE", DEFAULT_NODE if Path(DEFAULT_NODE).exists() else "node"))
    parser.add_argument("--n8n-bin", default=os.environ.get("N8N_BIN", DEFAULT_N8N if Path(DEFAULT_N8N).exists() else "n8n"))
    args = parser.parse_args()

    node = args.n8n_node
    n8n_bin = args.n8n_bin
    with tempfile.TemporaryDirectory(prefix="n8n-library-") as folder:
        user_folder = Path(folder)
        env = n8n_env(user_folder)
        base = [node, n8n_bin]
        probe = run(base + ["list:workflow"], env, check=False)
        if probe.returncode != 0:
            sys.stderr.write(probe.stderr or probe.stdout)
            return probe.returncode
        user_id = ensure_owner_scope(user_folder)
        combined = user_folder / "all-workflows.json"
        combined.write_text(json.dumps(collect_workflows()))
        imported = run(base + ["import:workflow", f"--input={combined}", f"--userId={user_id}"], env, check=False)
        if imported.returncode != 0:
            sys.stdout.write(imported.stdout)
            sys.stderr.write(imported.stderr)
            print("Import failed")
            return imported.returncode
        listing = run(base + ["list:workflow"], env, check=False)
        imported_names = [line.split("|", 1)[1] for line in listing.stdout.splitlines() if "|" in line]
        expected = len(json.loads(CATALOG_PATH.read_text())["workflows"])
        if len(imported_names) != expected:
            sys.stdout.write(imported.stdout)
            sys.stderr.write(imported.stderr)
            print(f"Import count mismatch: expected {expected}, listed {len(imported_names)}")
            return 1
        if args.import_only:
            print(f"Import-only pass succeeded ({len(imported_names)} workflows)")
            return 0

        db_path = user_folder / ".n8n" / "database.sqlite"
        rows = sqlite3.connect(db_path).execute("SELECT id, name FROM workflow_entity").fetchall()
        name_to_id = {name: workflow_id for workflow_id, name in rows}
        catalog = json.loads(CATALOG_PATH.read_text())
        statuses: dict[str, str] = {}
        failures = []
        id_to_catalog = {}
        batch_ids = []
        lone_ids = []
        for item in catalog["workflows"]:
            workflow_id = name_to_id.get(item["title"])
            if not workflow_id:
                statuses[item["id"]] = "import_failed"
                failures.append(f"{item['id']}: missing after import")
                continue
            id_to_catalog[workflow_id] = item["id"]
            # execute-batch keeps only ids that contain a digit.
            if any(character.isdigit() for character in workflow_id):
                batch_ids.append(workflow_id)
            else:
                lone_ids.append(workflow_id)
        id_file = user_folder / "ids.txt"
        id_file.write_text(",".join(batch_ids))
        batched = run(base + ["execute-batch", f"--ids={id_file}", "--shortOutput", "--concurrency=1"], env, check=False)
        batch_payload = parse_execution(batched.stdout) or {}
        summary = batch_payload.get("summary") or {}
        failed_ids = {error.get("workflowId"): error.get("error", "execution failed") for error in summary.get("errors") or []}
        if summary.get("successfulExecutions", 0) + summary.get("failedExecutions", 0) != len(batch_ids):
            failures.append(
                f"batch coverage {summary.get('successfulExecutions', 0) + summary.get('failedExecutions', 0)} of {len(batch_ids)}"
            )
        for workflow_id in batch_ids:
            catalog_id = id_to_catalog[workflow_id]
            if workflow_id in failed_ids:
                statuses[catalog_id] = "execution_failed"
                failures.append(f"{catalog_id}: {failed_ids[workflow_id]}")
                print(f"failed {catalog_id}")
            else:
                statuses[catalog_id] = "executed"
                print(f"executed {catalog_id}")
        for workflow_id in lone_ids:
            catalog_id = id_to_catalog[workflow_id]
            executed = run(base + ["execute", f"--id={workflow_id}", "--rawOutput"], env, check=False)
            ok, detail = execution_ok(parse_execution(executed.stdout))
            if ok and executed.returncode == 0:
                statuses[catalog_id] = "executed"
                print(f"executed {catalog_id}")
            else:
                statuses[catalog_id] = "execution_failed"
                message = detail if detail != "no JSON result" else (executed.stderr or executed.stdout)[-500:]
                failures.append(f"{catalog_id}: {message}")
                print(f"failed {catalog_id}: {message}")
        update_catalog(statuses)
        summary = {
            "imported": len(catalog["workflows"]),
            "executed": sum(1 for status in statuses.values() if status == "executed"),
            "execution_failed": sum(1 for status in statuses.values() if status == "execution_failed"),
            "import_failed": sum(1 for status in statuses.values() if status == "import_failed"),
            "failures": failures,
        }
        out = ROOT / "test-results"
        out.mkdir(exist_ok=True)
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps({key: summary[key] for key in ("imported", "executed", "execution_failed", "import_failed")}))
        return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
