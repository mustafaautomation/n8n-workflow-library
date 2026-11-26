#!/usr/bin/env python3
"""Write workflow folders, catalog.json, and the root README."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.graph import Builder, render_readme  # noqa: E402
from lib.specs import CATEGORIES, all_specs  # noqa: E402

CATALOG_PATH = ROOT / "catalog.json"
SCHEMA_VERSION = "1.0.0"
AUTHOR = {
    "name": "Mustafa",
    "github": "mustafaautomation",
    "demos": "*.quvantic.com",
}
DISCLAIMER = (
    "Portfolio demos only. These workflows are original examples for demonstration. "
    "They are not client deliverables and do not represent work performed for any customer."
)


def _load_previous() -> dict[str, dict]:
    if not CATALOG_PATH.exists():
        return {}
    data = json.loads(CATALOG_PATH.read_text())
    return {item["id"]: item for item in data.get("workflows", [])}


def main() -> None:
    previous = _load_previous()
    specs = all_specs()
    workflows_meta = []
    for spec in specs:
        folder = ROOT / "workflows" / spec["category"] / spec["id"]
        folder.mkdir(parents=True, exist_ok=True)
        builder = Builder(spec)
        workflow = builder.build()
        (folder / "workflow.json").write_text(json.dumps(workflow, indent=2) + "\n")
        (folder / "sample-input.json").write_text(json.dumps(spec["sample"], indent=2) + "\n")
        (folder / "README.md").write_text(render_readme(spec, builder.explained))
        screenshot = f"workflows/{spec['category']}/{spec['id']}/screenshot.png"
        prior = previous.get(spec["id"], {})
        workflows_meta.append(
            {
                "id": spec["id"],
                "title": spec["title"],
                "category": spec["category"],
                "apps": spec["apps"],
                "difficulty": spec["difficulty"],
                "tags": spec["tags"],
                "path": f"workflows/{spec['category']}/{spec['id']}",
                "description": spec["description"],
                "test_status": prior.get("test_status", "untested"),
                "screenshot": screenshot if (ROOT / screenshot).exists() else prior.get("screenshot"),
                "_polished": bool(spec.get("polished")),
            }
        )

    public_workflows = []
    for item in workflows_meta:
        public = dict(item)
        public.pop("_polished", None)
        if not (ROOT / f"{item['path']}/screenshot.png").exists():
            public["screenshot"] = None
        public_workflows.append(public)

    catalog = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": date.today().isoformat(),
        "disclaimer": DISCLAIMER,
        "author": AUTHOR,
        "n8n_tested_with": "2.49.5",
        "workflows": public_workflows,
    }
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")
    _write_category_indexes(workflows_meta)
    (ROOT / "README.md").write_text(_root_readme(workflows_meta, catalog))
    print(f"Wrote {len(workflows_meta)} workflows")


def _write_category_indexes(items: list[dict]) -> None:
    grouped: dict[str, list] = defaultdict(list)
    for item in items:
        grouped[item["category"]].append(item)
    for category, rows in grouped.items():
        lines = [
            f"# {CATEGORIES[category]}",
            "",
            DISCLAIMER,
            "",
            "| Workflow | Difficulty | Apps |",
            "| --- | --- | --- |",
        ]
        for row in rows:
            apps = ", ".join(row["apps"])
            lines.append(f"| [{row['title']}]({row['id']}/README.md) | {row['difficulty']} | {apps} |")
        lines.append("")
        path = ROOT / "workflows" / category / "README.md"
        path.write_text("\n".join(lines))


def _root_readme(items: list[dict], catalog: dict) -> str:
    grouped: dict[str, list] = defaultdict(list)
    for item in items:
        grouped[item["category"]].append(item)
    flagship = [item for item in items if item.get("_polished")]
    category_rows = []
    for slug, label in CATEGORIES.items():
        rows = grouped.get(slug, [])
        category_rows.append(
            f"| [{label}](workflows/{slug}/README.md) | `{slug}` | {len(rows)} |"
        )
    flagship_rows = "\n".join(
        f"| {index} | [{item['title']}]({item['path']}/README.md) | `{item['category']}` |"
        for index, item in enumerate(flagship, start=1)
    )
    return f"""# n8n workflow library

Portfolio demos by Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Live demos are hosted under `*.quvantic.com`.

**Portfolio demo only.** Every workflow in this repository is an original example for demonstration. These are not client deliverables, not case studies, and not a record of work done for a customer. Product names belong to their owners. This project is not affiliated with n8n, HubSpot, Google, Shopify, or any other vendor named in the folders.

Buyers of automation work tend to skim a README and import the JSON. Each folder is built for that: a valid n8n export, a sample payload, a node-by-node README, and a canvas screenshot once the local n8n render has been captured.

## The twenty flagship workflows

These are the ones written to a higher bar: a specific problem, a rules engine you can execute with **Run demo**, and the live apps on a branch that stays quiet until you set `demo` to false.

| # | Workflow | Category |
| --- | --- | --- |
{flagship_rows}

## Categories

| Category | Folder | Workflows |
| --- | --- | ---: |
{chr(10).join(category_rows)}

{len(items)} workflows in total. The machine-readable index is [`catalog.json`](catalog.json). Its fields are documented in [`CATALOG_SCHEMA.md`](CATALOG_SCHEMA.md) and are the contract a gallery site can consume.

## Import one workflow

1. Install [n8n](https://docs.n8n.io/) 2.x, or use n8n cloud.
2. Open **Workflows → Import from File** and choose `workflow.json` from the folder you want.
3. Execute **Run demo**. **Package demo result** returns `status: "demo_ready"` plus a summary, a route, a record, and the actions the live apps would take.
4. Create the credentials named in that folder's README and select them on the nodes. Every credential id in the JSON is a `PLACEHOLDER_*` label, not a secret.
5. Replace `YOUR_*` resource ids (sheet, channel, list, calendar).
6. POST `sample-input.json` to the webhook path (the workflow id) if you want the same run over HTTP.
7. Send `"demo": false` only after the live credentials work. Then publish the workflow.

`n8n execute` starts at **Run demo**, so the offline path is what a test run exercises. The Gmail, Shopify, Calendly, and other triggers are on the canvas for the real entry point. They are not called by the demo.

## Regenerate and validate

The JSON and READMEs are generated so the catalog cannot drift from the folders.

```bash
python3 scripts/build_library.py
python3 scripts/validate_catalog.py
python3 scripts/validate_catalog.py --self-test
```

Validation checks that every `workflow.json` parses, that connections point at real nodes, that node names and ids are unique, that credentials carry only a `PLACEHOLDER_*` id and a generic name, that no secret, real account id, real email domain, real phone number, or unlisted host appears in a workflow, sample, or README, that `catalog.json` matches the folders, that the workflow counts in this README and each category README match the folders, and that each Code node is valid JavaScript. `--self-test` runs every check against broken fixtures to prove it fires. Importing into n8n 2.49.5 is what `scripts/import_and_test.py` does locally. GitHub Actions runs the parser and, on a Node 24 runner, an n8n import.

## Layout

```
workflows/<category>/<workflow-id>/
  workflow.json        import this
  sample-input.json    POST this, or let Run demo load it
  README.md
  screenshot.png       canvas, added after a local n8n render
catalog.json
CATALOG_SCHEMA.md
```

## License

[MIT](LICENSE). You can import, adapt, and republish the workflows. Crediting Mustafa is appreciated and not required.
"""


if __name__ == "__main__":
    main()
