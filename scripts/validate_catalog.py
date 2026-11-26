#!/usr/bin/env python3
"""Check catalog.json against the workflow folders and parse every export.

Static checks only: nothing here imports into n8n or calls the network.

    python3 scripts/validate_catalog.py              validate the repository
    python3 scripts/validate_catalog.py --self-test  prove each check fires on a broken fixture
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog.json"
MIN_WORKFLOWS = 100

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
FOLDER_FILES = ("workflow.json", "README.md", "sample-input.json")
README_HEADINGS = (
    "## Problem",
    "## Who it is for",
    "## Node by node",
    "## Diagram",
    "## Setup",
    "## Credentials",
    "## Customization",
    "## Estimated time saved",
)
SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9]"),
    re.compile(r"sk_test_[A-Za-z0-9]{10,}"),
    re.compile(r"rk_live_[A-Za-z0-9]"),
    re.compile(r"sk-ant-[A-Za-z0-9]"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-"),
    re.compile(r"ghp_[A-Za-z0-9]"),
    re.compile(r"github_pat_[A-Za-z0-9_]"),
    re.compile(r"glpat-[A-Za-z0-9_-]{10,}"),
    re.compile(r"shp(?:at|ss|ca|pa)_[A-Fa-f0-9]{10,}"),
    re.compile(r"\bAC[0-9a-f]{32}\b"),
    re.compile(r"\bSK[0-9a-f]{32}\b"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."),
    re.compile(r"Bearer [A-Za-z0-9._~+/-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"hooks\.slack\.com/services/"),
]
# Identifiers that point at a real account: Slack workspace objects and Stripe objects.
ACCOUNT_ID_PATTERNS = [
    re.compile(r"\b[CDGUW]0[A-Z0-9]{7,10}\b"),
    re.compile(r"\b(?:acct|cus|sub|pi|py|ch|in|price|prod|evt|txn)_[A-Za-z0-9]{10,}\b"),
]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
URL_RE = re.compile(r"https?://[^\s\"'<>)\\]+")
PHONE_RE = re.compile(r"\+\d[\d ().-]{7,}\d")
# RFC 2606 / 6761 reserved names and the 555-0100..0199 fictional phone range.
RESERVED_DOMAIN_RE = re.compile(r"(?:^|\.)(?:example|test|invalid|localhost)$|(?:^|\.)example\.(?:com|net|org)$", re.I)
FICTIONAL_PHONE_RE = re.compile(r"^1?55555501\d\d$")
ALLOWED_URL_PREFIXES = (
    "https://docs.n8n.io",
    "https://www.notion.so/0123456789abcdef0123456789abcdef",
)
PLACEHOLDER_ID_RE = re.compile(r"^PLACEHOLDER_[A-Z0-9_]+$")
SAFE_RESOURCE_VALUE_RE = re.compile(r"^(?:=|YOUR_|PLACEHOLDER_|#)")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def check_identifiers(label: str, text: str, errors: list[str], allowed_urls: tuple[str, ...] = ALLOWED_URL_PREFIXES) -> None:
    """Flag secrets and anything that looks like a real account, inbox, phone, or host."""
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            fail(errors, f"{label}: matches secret pattern {pattern.pattern}")
    for pattern in ACCOUNT_ID_PATTERNS:
        for match in sorted(set(pattern.findall(text))):
            fail(errors, f"{label}: looks like a real account id: {match}")
    for domain in sorted(set(EMAIL_RE.findall(text))):
        if not RESERVED_DOMAIN_RE.search(domain):
            fail(errors, f"{label}: email domain {domain} is not a reserved example domain")
    for url in sorted(set(URL_RE.findall(text))):
        host = re.sub(r"^https?://", "", url).split("/", 1)[0].split(":", 1)[0]
        if RESERVED_DOMAIN_RE.search(host) or url.startswith(allowed_urls):
            continue
        fail(errors, f"{label}: URL {url} is not a reserved or allow-listed host")
    for phone in sorted(set(PHONE_RE.findall(text))):
        digits = re.sub(r"\D", "", phone)
        if not FICTIONAL_PHONE_RE.match(digits):
            fail(errors, f"{label}: phone {phone} is outside the fictional 555-01xx range")


def _check_resource_locators(path: Path, name: str, value, errors: list[str]) -> None:
    """Resource ids picked by id or url must be placeholders, expressions, or reserved values."""
    if isinstance(value, dict):
        if value.get("__rl") and value.get("mode") in ("id", "url"):
            raw = value.get("value")
            if isinstance(raw, str) and not (
                SAFE_RESOURCE_VALUE_RE.match(raw)
                or (EMAIL_RE.fullmatch(raw) and RESERVED_DOMAIN_RE.search(EMAIL_RE.fullmatch(raw).group(1)))
                or raw.startswith(ALLOWED_URL_PREFIXES)
            ):
                fail(errors, f"{path}: {name} has a literal resource id {raw!r}; use a YOUR_* placeholder")
            return
        for item in value.values():
            _check_resource_locators(path, name, item, errors)
    elif isinstance(value, list):
        for item in value:
            _check_resource_locators(path, name, item, errors)


def check_workflow_json(path: Path, errors: list[str], allowed_urls: tuple[str, ...] = ALLOWED_URL_PREFIXES) -> dict | None:
    try:
        text = path.read_text()
        data = json.loads(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
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
    names: list = []
    node_ids: list = []
    code_blobs = []
    for node in nodes:
        if not isinstance(node, dict):
            fail(errors, f"{path}: a node is not an object")
            continue
        for key in ("id", "name", "type", "typeVersion", "position", "parameters"):
            if key not in node:
                fail(errors, f"{path}: node {node.get('name')} missing {key}")
        name = node.get("name")
        if not isinstance(name, str) or not name.strip():
            fail(errors, f"{path}: node name must be a non-empty string, got {name!r}")
        elif name in names:
            fail(errors, f"{path}: duplicate node name {name}")
        names.append(name)
        node_id = node.get("id")
        if node_id is not None and node_id in node_ids:
            fail(errors, f"{path}: duplicate node id {node_id}")
        node_ids.append(node_id)
        position = node.get("position")
        if not (isinstance(position, list) and len(position) == 2):
            fail(errors, f"{path}: {name} position must be [x, y]")
        credentials = node.get("credentials") or {}
        if not isinstance(credentials, dict):
            fail(errors, f"{path}: {name} credentials must be an object")
            credentials = {}
        for cred_type, cred in credentials.items():
            if not isinstance(cred, dict):
                fail(errors, f"{path}: {name} credential {cred_type} must be an object with id and name")
                continue
            extra = set(cred) - {"id", "name"}
            if extra:
                fail(errors, f"{path}: {name} credential {cred_type} carries values beyond id and name: {sorted(extra)}")
            if not PLACEHOLDER_ID_RE.match(str(cred.get("id", ""))):
                fail(errors, f"{path}: {name} credential {cred_type} is not a PLACEHOLDER_ id")
            cred_name = str(cred.get("name", ""))
            if not cred_name or "@" in cred_name:
                fail(errors, f"{path}: {name} credential {cred_type} name must be a generic label, not an account")
        _check_resource_locators(path, str(name), node.get("parameters"), errors)
        js = (node.get("parameters") or {}).get("jsCode") if isinstance(node.get("parameters"), dict) else None
        if isinstance(js, str):
            code_blobs.append((name, js))
    known = {name for name in names if isinstance(name, str)}
    connections = data.get("connections") or {}
    if not isinstance(connections, dict):
        fail(errors, f"{path}: connections must be an object")
    else:
        for source, outputs in connections.items():
            if source not in known:
                fail(errors, f"{path}: connection source {source} is not a node")
            if not isinstance(outputs, dict):
                fail(errors, f"{path}: connections of {source} must be an object")
                continue
            for conn_type, groups in outputs.items():
                if not isinstance(groups, list):
                    fail(errors, f"{path}: {source}.{conn_type} is not a list")
                    continue
                for group in groups:
                    if group is None:
                        continue
                    if not isinstance(group, list):
                        fail(errors, f"{path}: {source}.{conn_type} output is not a list")
                        continue
                    for link in group:
                        if not isinstance(link, dict):
                            fail(errors, f"{path}: {source}.{conn_type} has a link that is not an object")
                            continue
                        target = link.get("node")
                        if target not in known:
                            fail(errors, f"{path}: {source} links to missing node {target}")
                        if not isinstance(link.get("index", 0), int):
                            fail(errors, f"{path}: {source} -> {target} index must be an integer")
    if not any(node.get("type") == "n8n-nodes-base.manualTrigger" for node in nodes if isinstance(node, dict)):
        fail(errors, f"{path}: missing the Run demo manual trigger")
    if data.get("active") not in (False, None):
        fail(errors, f"{path}: workflow must import inactive")
    if data.get("pinData") not in ({}, None):
        fail(errors, f"{path}: pinData must be empty; pinned executions can carry real data")
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    if "instanceId" in meta:
        fail(errors, f"{path}: meta.instanceId identifies an n8n instance; remove it")
    check_identifiers(str(path), text, errors, allowed_urls)
    _check_javascript(path, code_blobs, errors)
    return data


def _check_javascript(path: Path, blobs: list[tuple[str, str]], errors: list[str]) -> None:
    if not blobs:
        return
    if shutil.which("node") is None:
        fail(errors, f"{path}: node is not installed, cannot syntax-check Code nodes")
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


def check_folders(root: Path, errors: list[str]) -> dict[str, list[str]]:
    """Every workflows/<category>/<id>/ folder holds the three files. Returns ids per category."""
    found: dict[str, list[str]] = {}
    base = root / "workflows"
    if not base.is_dir():
        fail(errors, "workflows/ folder is missing")
        return found
    for category_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        if category_dir.name not in CATEGORIES:
            fail(errors, f"workflows/{category_dir.name} is not a known category")
        if not (category_dir / "README.md").exists():
            fail(errors, f"workflows/{category_dir.name}: missing category README.md")
        ids = []
        for folder in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            ids.append(folder.name)
            rel = folder.relative_to(root).as_posix()
            for filename in FOLDER_FILES:
                if not (folder / filename).is_file():
                    fail(errors, f"{rel}: missing {filename}")
        found[category_dir.name] = ids
    return found


def check_readme_counts(root: Path, folders: dict[str, list[str]], titles: dict[str, str], errors: list[str]) -> None:
    """The root README table, its total, and each category README must match the folders."""
    readme_path = root / "README.md"
    readme = readme_path.read_text() if readme_path.exists() else ""
    rows = dict(re.findall(r"^\|\s*\[[^\]]+\]\(workflows/([\w-]+)/README\.md\)\s*\|\s*`[\w-]+`\s*\|\s*(\d+)\s*\|", readme, re.M))
    for category, ids in folders.items():
        listed = rows.get(category)
        if listed is None:
            fail(errors, f"README.md: no category row for {category}")
        elif int(listed) != len(ids):
            fail(errors, f"README.md: {category} lists {listed} workflows, folder has {len(ids)}")
    for category in sorted(set(rows) - set(folders)):
        fail(errors, f"README.md: category row {category} has no folder")
    total = sum(len(ids) for ids in folders.values())
    totals = re.findall(r"(\d+) workflows in total", readme)
    if not totals:
        fail(errors, "README.md: missing the 'N workflows in total' line")
    for value in totals:
        if int(value) != total:
            fail(errors, f"README.md: says {value} workflows in total, folders hold {total}")
    for category, ids in folders.items():
        path = root / "workflows" / category / "README.md"
        if not path.exists():
            continue
        links = re.findall(r"^\|\s*\[([^\]]+)\]\(([\w-]+)/README\.md\)", path.read_text(), re.M)
        listed_ids = [link_id for _, link_id in links]
        for link_id in sorted(set(ids) - set(listed_ids)):
            fail(errors, f"workflows/{category}/README.md: {link_id} is not listed")
        for link_id in sorted(set(listed_ids) - set(ids)):
            fail(errors, f"workflows/{category}/README.md: lists {link_id}, which has no folder")
        if len(listed_ids) != len(set(listed_ids)):
            fail(errors, f"workflows/{category}/README.md: a workflow is listed twice")
        for title, link_id in links:
            expected = titles.get(link_id)
            if expected is not None and title != expected:
                fail(errors, f"workflows/{category}/README.md: {link_id} title {title!r} differs from catalog {expected!r}")


def validate(root: Path, min_workflows: int = MIN_WORKFLOWS) -> tuple[list[str], int]:
    errors: list[str] = []
    catalog_path = root / "catalog.json"
    if not catalog_path.exists():
        return ["catalog.json is missing. Run scripts/build_library.py."], 0
    try:
        catalog = json.loads(catalog_path.read_text())
    except json.JSONDecodeError as exc:
        return [f"catalog.json: invalid JSON ({exc})"], 0
    if catalog.get("schema_version") != "1.0.0":
        fail(errors, "schema_version must stay 1.0.0")
    author = catalog.get("author") if isinstance(catalog.get("author"), dict) else {}
    allowed_urls = ALLOWED_URL_PREFIXES
    if author.get("github"):
        allowed_urls += (f"https://github.com/{author['github']}",)
    workflows = catalog.get("workflows")
    if not isinstance(workflows, list):
        fail(errors, "workflows must be a list")
        workflows = []
    workflows = [item for item in workflows if isinstance(item, dict)] or workflows
    ids = [item.get("id") for item in workflows]
    if len(ids) != len(set(ids)):
        fail(errors, "duplicate workflow ids in catalog.json")
    folders = check_folders(root, errors)
    folder_paths = {f"workflows/{category}/{wid}" for category, wids in folders.items() for wid in wids}
    catalog_paths = set()
    titles: dict[str, str] = {}
    for item in workflows:
        for field in REQUIRED_WORKFLOW_FIELDS:
            if field not in item:
                fail(errors, f"{item.get('id')}: missing catalog field {field}")
        titles[str(item.get("id"))] = item.get("title")
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
        if path != f"workflows/{item.get('category')}/{item.get('id')}":
            fail(errors, f"{item.get('id')}: path {path} must be workflows/<category>/<id>")
        folder = root / path if isinstance(path, str) else None
        if folder is None or not folder.is_dir():
            fail(errors, f"{item.get('id')}: folder {path} does not exist")
            continue
        workflow_path = folder / "workflow.json"
        if workflow_path.exists():
            data = check_workflow_json(workflow_path, errors, allowed_urls)
            if data and data.get("name") != item.get("title"):
                fail(errors, f"{path}: workflow name does not match catalog title")
        readme_path = folder / "README.md"
        readme = readme_path.read_text() if readme_path.exists() else ""
        if readme_path.exists():
            for heading in README_HEADINGS:
                if heading not in readme:
                    fail(errors, f"{path}: README missing {heading}")
            if "Portfolio demo" not in readme:
                fail(errors, f"{path}: README missing the portfolio disclaimer")
            check_identifiers(f"{path}/README.md", readme, errors, allowed_urls)
        sample_path = folder / "sample-input.json"
        if sample_path.exists():
            sample_text = sample_path.read_text()
            try:
                sample = json.loads(sample_text)
                if not isinstance(sample, dict):
                    fail(errors, f"{sample_path}: sample payload must be a JSON object")
            except json.JSONDecodeError as exc:
                fail(errors, f"{sample_path}: invalid JSON ({exc})")
            check_identifiers(str(sample_path), sample_text, errors, allowed_urls)
        screenshot = item.get("screenshot")
        if screenshot is not None:
            if not isinstance(screenshot, str) or not (root / screenshot).exists():
                fail(errors, f"{item.get('id')}: screenshot {screenshot} is missing")
    for path in sorted(folder_paths - catalog_paths):
        fail(errors, f"folder {path} is not in catalog.json")
    for path in sorted(p for p in catalog_paths - folder_paths if p):
        fail(errors, f"catalog path {path} has no workflow folder")
    check_readme_counts(root, folders, titles, errors)
    if len(workflows) < min_workflows:
        fail(errors, f"expected at least {min_workflows} workflows, found {len(workflows)}")
    return errors, len(workflows)


# --------------------------------------------------------------------------- self-test


def _fixture(root: Path) -> None:
    """Write a one-workflow library that passes every check."""
    wid, category, title = "demo-flow", "ops", "Demo flow"
    folder = root / "workflows" / category / wid
    folder.mkdir(parents=True)
    workflow = {
        "name": title,
        "nodes": [
            {"id": "n1", "name": "Run demo", "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1, "position": [0, 0], "parameters": {}},
            {
                "id": "n2",
                "name": "Post to Slack",
                "type": "n8n-nodes-base.slack",
                "typeVersion": 2,
                "position": [200, 0],
                "parameters": {"channelId": {"__rl": True, "mode": "id", "value": "YOUR_SLACK_CHANNEL_ID"}, "text": "Hi ada@northwind.example"},
                "credentials": {"slackApi": {"id": "PLACEHOLDER_SLACKAPI", "name": "Slack bot"}},
            },
        ],
        "connections": {"Run demo": {"main": [[{"node": "Post to Slack", "type": "main", "index": 0}]]}},
        "pinData": {},
        "meta": {"templateCredsSetupCompleted": False},
        "active": False,
    }
    (folder / "workflow.json").write_text(json.dumps(workflow, indent=2))
    (folder / "sample-input.json").write_text(json.dumps({"demo": True, "phone": "+15555550123", "site": "https://example.com"}))
    (folder / "README.md").write_text("Portfolio demo.\n" + "\n".join(f"{h}\n\ntext\n" for h in README_HEADINGS))
    (root / "workflows" / category / "README.md").write_text(f"# Ops\n\n| Workflow | Difficulty | Apps |\n| --- | --- | --- |\n| [{title}]({wid}/README.md) | beginner | Slack |\n")
    (root / "README.md").write_text(
        f"| Category | Folder | Workflows |\n| --- | --- | ---: |\n| [Ops](workflows/{category}/README.md) | `{category}` | 1 |\n\n1 workflows in total.\n"
    )
    catalog = {
        "schema_version": "1.0.0",
        "author": {"github": "someone"},
        "workflows": [
            {
                "id": wid,
                "title": title,
                "category": category,
                "apps": ["Slack"],
                "difficulty": "beginner",
                "tags": ["demo"],
                "path": f"workflows/{category}/{wid}",
                "description": "Demo.",
                "test_status": "untested",
                "screenshot": None,
            }
        ],
    }
    (root / "catalog.json").write_text(json.dumps(catalog, indent=2))


def _edit_json(path: Path, change) -> None:
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data, indent=2))


def _mutations() -> list[tuple[str, str, object]]:
    """(description, expected error fragment, mutation(root)) for every check this script adds."""
    wf = Path("workflows/ops/demo-flow/workflow.json")
    sample = Path("workflows/ops/demo-flow/sample-input.json")

    def json_edit(rel: Path, change):
        return lambda root: _edit_json(root / rel, change)

    def nodes(fn):
        return json_edit(wf, lambda d: fn(d["nodes"]))

    def write(rel: str, text: str):
        return lambda root: (root / rel).write_text(text)

    def append(rel: str, text: str):
        return lambda root: (root / rel).write_text((root / rel).read_text() + text)

    def remove(rel: str):
        return lambda root: (root / rel).unlink()

    def add_folder(root: Path) -> None:
        (root / "workflows/ops/orphan").mkdir()
        (root / "workflows/ops/orphan/README.md").write_text("x")

    return [
        ("dangling connection", "links to missing node Ghost", json_edit(wf, lambda d: d["connections"]["Run demo"]["main"][0].append({"node": "Ghost", "type": "main", "index": 0}))),
        ("unknown connection source", "connection source Ghost is not a node", json_edit(wf, lambda d: d["connections"].update({"Ghost": {"main": [[]]}}))),
        ("malformed link", "link that is not an object", json_edit(wf, lambda d: d["connections"]["Run demo"]["main"][0].append("Post to Slack"))),
        ("duplicate node name", "duplicate node name Run demo", nodes(lambda n: n[1].update({"name": "Run demo"}))),
        ("duplicate node id", "duplicate node id n1", nodes(lambda n: n[1].update({"id": "n1"}))),
        ("real credential id", "is not a PLACEHOLDER_ id", nodes(lambda n: n[1]["credentials"]["slackApi"].update({"id": "aB3dE5fG7hJ9"}))),
        ("credential value inline", "beyond id and name", nodes(lambda n: n[1]["credentials"]["slackApi"].update({"accessToken": "abc"}))),
        ("credential named after an account", "generic label", nodes(lambda n: n[1]["credentials"]["slackApi"].update({"name": "ops@acme.io"}))),
        ("secret token", "secret pattern", nodes(lambda n: n[1]["parameters"].update({"text": "xoxb-1234-5678"}))),
        ("real email", "email domain acme.io", nodes(lambda n: n[1]["parameters"].update({"text": "jane@acme.io"}))),
        ("real phone", "outside the fictional", json_edit(sample, lambda d: d.update({"phone": "+14155552671"}))),
        ("real host", "URL https://hooks.acme.io/x", json_edit(sample, lambda d: d.update({"site": "https://hooks.acme.io/x"}))),
        ("Slack channel id", "real account id: C0123ABCD45", nodes(lambda n: n[1]["parameters"].update({"text": "see C0123ABCD45"}))),
        ("literal resource id", "literal resource id '10000'", nodes(lambda n: n[1]["parameters"]["channelId"].update({"value": "10000"}))),
        ("instance id", "meta.instanceId", json_edit(wf, lambda d: d["meta"].update({"instanceId": "abc"}))),
        ("pinned data", "pinData must be empty", json_edit(wf, lambda d: d.update({"pinData": {"Run demo": [{"json": {}}]}}))),
        ("broken workflow JSON", "invalid JSON", write(str(wf), "{")),
        ("missing sample", "missing sample-input.json", remove(str(sample))),
        ("folder without workflow.json", "workflows/ops/orphan: missing workflow.json", add_folder),
        ("catalog path without folder", "has no workflow folder", json_edit(Path("catalog.json"), lambda d: d["workflows"][0].update({"path": "workflows/ops/gone"}))),
        ("root README count", "ops lists 1 workflows, folder has 2", add_folder),
        ("root README total", "says 9 workflows in total", lambda root: (root / "README.md").write_text((root / "README.md").read_text().replace("1 workflows in total", "9 workflows in total"))),
        ("category README row missing", "demo-flow is not listed", write("workflows/ops/README.md", "# Ops\n")),
        ("category README stale row", "lists old-flow, which has no folder", append("workflows/ops/README.md", "| [Old](old-flow/README.md) | beginner | Slack |\n")),
        ("category README title drift", "differs from catalog", lambda root: (root / "workflows/ops/README.md").write_text((root / "workflows/ops/README.md").read_text().replace("[Demo flow]", "[Old name]"))),
    ]


def self_test() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp) / "clean"
        _fixture(clean)
        errors, _ = validate(clean, min_workflows=1)
        if errors:
            failures.append("clean fixture should pass but got:\n  " + "\n  ".join(errors))
        for index, (label, expected, mutate) in enumerate(_mutations()):
            case = Path(tmp) / f"case{index}"
            _fixture(case)
            mutate(case)
            try:
                errors, _ = validate(case, min_workflows=1)
            except Exception as exc:  # a crash is a failed check, not a pass
                failures.append(f"{label}: validator crashed with {exc!r}")
                continue
            if not any(expected in error for error in errors):
                failures.append(f"{label}: expected an error containing {expected!r}, got {errors}")
    total = len(_mutations()) + 1
    if failures:
        print(f"self-test: {len(failures)} of {total} case(s) failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"self-test: all {total} cases passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-test", action="store_true", help="run the validator against built-in broken fixtures")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    errors, count = validate(ROOT)
    if errors:
        print(f"{len(errors)} problem(s):")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Validated {count} workflows against catalog.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
