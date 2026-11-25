#!/usr/bin/env python3
"""Check catalog.json against the workflow folders and parse every export."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog.json"

REQUIRED_WORKFLOW_FIELDS = [
    "id",
    "title",
    "category",
    "apps",
    "difficulty",
    "tags",
    "path",
    "description",
    "test_status",
    "screenshot",
]
CATEGORIES = {
    "lead-gen-crm",
    "speed-to-lead",
    "invoices-docs",
    "email",
    "social",
    "ecommerce",
    "support",
    "booking",
    "reporting",
    "ops",
    "scraping-enrichment",
    "ai-agents",
    "hr-recruiting",
    "finance",
}
DIFFICULTIES = {"beginner", "intermediate", "advanced"}
STATUSES = {"untested", "imported", "executed", "import_failed", "execution_failed"}
SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9]"),
    re.compile(r"sk-ant-[A-Za-z0-9]"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-"),
    re.compile(r"ghp_[A-Za-z0-9]"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def check_workflow_json(path: Path, errors: list[str]) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        fail(errors, f"{path}: invalid JSON ({exc})")
        return None
    if not isinstance(data, dict):
        fail(errors, f"{path}: workflow export must be an object")
        return None
    for key in ("name", "nodes", "connections"):
        if key not in data:
            fail(errors, f"{path}: missing {key}")
    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        fail(errors, f"{path}: nodes must be a non-empty list")
        return data
    names = []
    code_blobs = []
    for node in nodes:
        if not isinstance(node, dict):
            fail(errors, f"{path}: a node is not an object")
            continue
        for key in ("id", "name", "type", "typeVersion", "position", "parameters"):
            if key not in node:
                fail(errors, f"{path}: node {node.get('name')} missing {key}")
        name = node.get("name")
        if name in names:
            fail(errors, f"{path}: duplicate node name {name}")
        names.append(name)
        position = node.get("position")
        if not (isinstance(position, list) and len(position) == 2):
            fail(errors, f"{path}: {name} position must be [x, y]")
        credentials = node.get("credentials") or {}
        if isinstance(credentials, dict):
            for cred_type, cred in credentials.items():
                cred_id = cred.get("id", "") if isinstance(cred, dict) else ""
                if not str(cred_id).startswith("PLACEHOLDER_"):
                    fail(errors, f"{path}: {name} credential {cred_type} is not a PLACEHOLDER_ id")
        js = (node.get("parameters") or {}).get("jsCode")
        if isinstance(js, str):
            code_blobs.append((name, js))
        blob = json.dumps(node)
        for pattern in SECRET_PATTERNS:
            if pattern.search(blob):
                fail(errors, f"{path}: {name} matches secret pattern {pattern.pattern}")
    known = set(names)
    connections = data.get("connections") or {}
    if not isinstance(connections, dict):
        fail(errors, f"{path}: connections must be an object")
    else:
        for source, outputs in connections.items():
            if source not in known:
                fail(errors, f"{path}: connection source {source} is not a node")
            if not isinstance(outputs, dict):
                continue
            for conn_type, groups in outputs.items():
                if not isinstance(groups, list):
                    fail(errors, f"{path}: {source}.{conn_type} is not a list")
                    continue
                for group in groups:
                    if group is None:
                        continue
                    for link in group:
                        target = link.get("node")
                        if target not in known:
                            fail(errors, f"{path}: {source} links to missing node {target}")
    if not any(node.get("type") == "n8n-nodes-base.manualTrigger" for node in nodes if isinstance(node, dict)):
        fail(errors, f"{path}: missing the Run demo manual trigger")
    if data.get("active") not in (False, None):
        fail(errors, f"{path}: workflow must import inactive")
    _check_javascript(path, code_blobs, errors)
    return data


def _check_javascript(path: Path, blobs: list[tuple[str, str]], errors: list[str]) -> None:
    if not blobs:
        return
    payload = [{"name": name, "code": code} for name, code in blobs]
    script = r"""
const fs = require('fs');
const items = JSON.parse(fs.readFileSync(0, 'utf8'));
const failures = [];
for (const item of items) {
  try { new Function(item.code); }
  catch (error) { failures.push(item.name + ': ' + error.message); }
}
if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
"""
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        fail(errors, f"{path}: JavaScript syntax error\n{detail}")


def main() -> int:
    errors: list[str] = []
    if not CATALOG_PATH.exists():
        print("catalog.json is missing. Run scripts/build_library.py.")
        return 1
    catalog = json.loads(CATALOG_PATH.read_text())
    if catalog.get("schema_version") != "1.0.0":
        fail(errors, "schema_version must stay 1.0.0")
    workflows = catalog.get("workflows")
    if not isinstance(workflows, list):
        fail(errors, "workflows must be a list")
        workflows = []
    ids = [item.get("id") for item in workflows]
    if len(ids) != len(set(ids)):
        fail(errors, "duplicate workflow ids in catalog.json")
    folders = {
        path.parent.relative_to(ROOT).as_posix()
        for path in (ROOT / "workflows").glob("*/*/workflow.json")
    }
    catalog_paths = set()
    for item in workflows:
        for field in REQUIRED_WORKFLOW_FIELDS:
            if field not in item:
                fail(errors, f"{item.get('id')}: missing catalog field {field}")
        if item.get("category") not in CATEGORIES:
            fail(errors, f"{item.get('id')}: unknown category {item.get('category')}")
        if item.get("difficulty") not in DIFFICULTIES:
            fail(errors, f"{item.get('id')}: bad difficulty")
        if item.get("test_status") not in STATUSES:
            fail(errors, f"{item.get('id')}: bad test_status")
        if not isinstance(item.get("apps"), list) or not item["apps"]:
            fail(errors, f"{item.get('id')}: apps must be a non-empty list")
        if not isinstance(item.get("tags"), list) or not item["tags"]:
            fail(errors, f"{item.get('id')}: tags must be a non-empty list")
        path = item.get("path")
        catalog_paths.add(path)
        folder = ROOT / path if isinstance(path, str) else None
        if folder is None or not folder.is_dir():
            fail(errors, f"{item.get('id')}: folder {path} does not exist")
            continue
        for filename in ("workflow.json", "README.md", "sample-input.json"):
            if not (folder / filename).exists():
                fail(errors, f"{path}: missing {filename}")
        workflow_path = folder / "workflow.json"
        if workflow_path.exists():
            data = check_workflow_json(workflow_path, errors)
            if data and data.get("name") != item.get("title"):
                fail(errors, f"{path}: workflow name does not match catalog title")
        readme = (folder / "README.md").read_text() if (folder / "README.md").exists() else ""
        for heading in ("## Problem", "## Who it is for", "## Node by node", "## Diagram", "## Setup", "## Credentials", "## Customization", "## Estimated time saved"):
            if heading not in readme:
                fail(errors, f"{path}: README missing {heading}")
        if "Portfolio demo" not in readme:
            fail(errors, f"{path}: README missing the portfolio disclaimer")
        sample_path = folder / "sample-input.json"
        if sample_path.exists():
            try:
                json.loads(sample_path.read_text())
            except json.JSONDecodeError as exc:
                fail(errors, f"{sample_path}: invalid JSON ({exc})")
        screenshot = item.get("screenshot")
        if screenshot is not None:
            if not isinstance(screenshot, str) or not (ROOT / screenshot).exists():
                fail(errors, f"{item.get('id')}: screenshot {screenshot} is missing")
    missing = folders - catalog_paths
    extra = catalog_paths - folders
    for path in sorted(missing):
        fail(errors, f"folder {path} is not in catalog.json")
    for path in sorted(extra):
        if path:
            fail(errors, f"catalog path {path} has no workflow folder")
    if len(workflows) < 100:
        fail(errors, f"expected at least 100 workflows, found {len(workflows)}")
    if errors:
        print(f"{len(errors)} problem(s):")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validated {len(workflows)} workflows against catalog.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
