# Catalog schema 1.0.0

`catalog.json` is the index a gallery site can read without walking the repo. The schema version stays `1.0.0` until a required field is renamed, removed, or changes meaning. New optional fields may be added. Consumers must ignore object keys they do not recognize, both at the root and on each workflow.

## Root

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Always `1.0.0` for this document. |
| `updated_at` | string | yes | ISO date (`YYYY-MM-DD`) when the catalog file was generated. |
| `disclaimer` | string | yes | States that the workflows are portfolio demos, not client work. |
| `author` | object | yes | `name`, `github`, and `demos`. `demos` is the host pattern `*.quvantic.com`. |
| `n8n_tested_with` | string | no | n8n version used for the last import and execution pass. |
| `workflows` | array | yes | One object per workflow, defined below. |

## Workflow

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | string | yes | Stable kebab-case id. Matches the folder name and the webhook path. |
| `title` | string | yes | Human title. Matches the `name` inside `workflow.json`. |
| `category` | string | yes | One of the category slugs listed below. |
| `apps` | string[] | yes | Products a buyer will see on the canvas. Not a credential list. |
| `difficulty` | string | yes | `beginner`, `intermediate`, or `advanced`. |
| `tags` | string[] | yes | Short search tags. |
| `path` | string | yes | Repo-relative folder, forward slashes, no leading slash. Example: `workflows/invoices-docs/ai-invoice-gmail-to-sheets`. |
| `description` | string | yes | One paragraph on what the workflow does. |
| `test_status` | string | yes | Result of the latest local n8n pass. One of `untested`, `imported`, `executed`, `import_failed`, `execution_failed`. |
| `screenshot` | string or null | yes | Repo-relative PNG of the n8n canvas, or `null` when the render has not been captured yet. |

`test_status` meanings:

- `untested` — JSON is in the repo and has not been imported in the latest run.
- `imported` — n8n accepted the file and an execution was not attempted or did not finish cleanly enough to count.
- `executed` — n8n imported the file and `n8n execute` finished on the demo branch with `status: "demo_ready"`.
- `import_failed` — n8n rejected the file.
- `execution_failed` — import worked and the demo execution returned an error.

## Categories

`lead-gen-crm`, `speed-to-lead`, `invoices-docs`, `email`, `social`, `ecommerce`, `support`, `booking`, `reporting`, `ops`, `scraping-enrichment`, `ai-agents`, `hr-recruiting`, `finance`.

## Folder contract

`path` always contains:

- `workflow.json` — one inactive n8n workflow object. Credential ids, when present, start with `PLACEHOLDER_`.
- `sample-input.json` — the payload **Run demo** loads when the manual trigger is empty.
- `README.md` — problem, audience, node-by-node explanation, Mermaid diagram, setup, credentials, customization, and time saved.
- `screenshot.png` — present when `screenshot` is a string.

## Example

```json
{
  "id": "ai-invoice-gmail-to-sheets",
  "title": "AI invoice and receipt extraction from Gmail to Sheets, Xero, and QuickBooks",
  "category": "invoices-docs",
  "apps": ["Gmail", "Google Sheets", "Xero", "QuickBooks"],
  "difficulty": "advanced",
  "tags": ["invoice", "gmail", "xero", "quickbooks", "ai"],
  "path": "workflows/invoices-docs/ai-invoice-gmail-to-sheets",
  "description": "A mailbox attachment is read as text and checked before it is posted.",
  "test_status": "executed",
  "screenshot": "workflows/invoices-docs/ai-invoice-gmail-to-sheets/screenshot.png"
}
```
