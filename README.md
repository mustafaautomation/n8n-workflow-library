# n8n workflow library

Portfolio demos by Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Live demos are hosted under `*.quvantic.com`.

**Portfolio demo only.** Every workflow in this repository is an original example for demonstration. These are not client deliverables, not case studies, and not a record of work done for a customer. Product names belong to their owners. This project is not affiliated with n8n, HubSpot, Google, Shopify, or any other vendor named in the folders.

Buyers of automation work tend to skim a README and import the JSON. Each folder is built for that: a valid n8n export, a sample payload, a node-by-node README, and a canvas screenshot once the local n8n render has been captured.

## The twenty flagship workflows

These are the ones written to a higher bar: a specific problem, a rules engine you can execute with **Run demo**, and the live apps on a branch that stays quiet until you set `demo` to false.

| # | Workflow | Category |
| --- | --- | --- |
| 1 | [AI lead capture, enrichment, and scoring into HubSpot](workflows/lead-gen-crm/ai-lead-enrich-score-hubspot/README.md) | `lead-gen-crm` |
| 2 | [AI lead capture, enrichment, and scoring into GoHighLevel](workflows/lead-gen-crm/ai-lead-enrich-score-gohighlevel/README.md) | `lead-gen-crm` |
| 3 | [Pipedrive deal from a web form](workflows/lead-gen-crm/pipedrive-deal-from-web-form/README.md) | `lead-gen-crm` |
| 4 | [Speed-to-lead SMS and email inside 60 seconds](workflows/speed-to-lead/speed-to-lead-sms-email/README.md) | `speed-to-lead` |
| 5 | [Missed-call text-back](workflows/speed-to-lead/missed-call-text-back/README.md) | `speed-to-lead` |
| 6 | [AI invoice and receipt extraction from Gmail to Sheets, Xero, and QuickBooks](workflows/invoices-docs/ai-invoice-gmail-to-sheets/README.md) | `invoices-docs` |
| 7 | [AI email triage with Gmail labels and drafted replies](workflows/email/ai-gmail-triage-drafts/README.md) | `email` |
| 8 | [Repurpose a blog or YouTube piece into LinkedIn and X drafts](workflows/social/social-content-repurposing/README.md) | `social` |
| 9 | [Shopify order to Sheets, Slack, and fulfillment](workflows/ecommerce/shopify-order-sync/README.md) | `ecommerce` |
| 10 | [WooCommerce order sync to Sheets and Slack](workflows/ecommerce/woocommerce-order-sync/README.md) | `ecommerce` |
| 11 | [AI support ticket classification and routing](workflows/support/ai-support-ticket-routing/README.md) | `support` |
| 12 | [Appointment booking with SMS and email reminders](workflows/booking/appointment-booking-reminders/README.md) | `booking` |
| 13 | [Weekly KPI report to Slack and email](workflows/reporting/weekly-kpi-report/README.md) | `reporting` |
| 14 | [Claude-ready CRM summary for the Monday dashboard](workflows/reporting/claude-crm-summary-dashboard/README.md) | `reporting` |
| 15 | [Slack message to a Notion page and a ClickUp task](workflows/ops/slack-to-notion-clickup/README.md) | `ops` |
| 16 | [Web page scrape and enrichment into Sheets](workflows/scraping-enrichment/web-scrape-enrich-sheets/README.md) | `scraping-enrichment` |
| 17 | [AI agent with memory, a pricing tool, and a sheet tool](workflows/ai-agents/ai-agent-with-tools/README.md) | `ai-agents` |
| 18 | [RAG knowledge-base chatbot](workflows/ai-agents/rag-knowledge-base-chatbot/README.md) | `ai-agents` |
| 19 | [CV parsing and candidate scoring into a sheet](workflows/hr-recruiting/cv-parsing-candidate-scoring/README.md) | `hr-recruiting` |
| 20 | [Stripe charges versus the bank, with a sheet of exceptions](workflows/finance/stripe-bank-reconciliation/README.md) | `finance` |

## Categories

| Category | Folder | Workflows |
| --- | --- | ---: |
| [Lead gen and CRM](workflows/lead-gen-crm/README.md) | `lead-gen-crm` | 12 |
| [Speed to lead](workflows/speed-to-lead/README.md) | `speed-to-lead` | 8 |
| [Invoices and documents](workflows/invoices-docs/README.md) | `invoices-docs` | 8 |
| [Email](workflows/email/README.md) | `email` | 8 |
| [Social](workflows/social/README.md) | `social` | 8 |
| [E-commerce](workflows/ecommerce/README.md) | `ecommerce` | 8 |
| [Support](workflows/support/README.md) | `support` | 8 |
| [Booking](workflows/booking/README.md) | `booking` | 6 |
| [Reporting](workflows/reporting/README.md) | `reporting` | 8 |
| [Slack, Notion, and ClickUp](workflows/ops/README.md) | `ops` | 8 |
| [Scraping and enrichment](workflows/scraping-enrichment/README.md) | `scraping-enrichment` | 8 |
| [AI agents](workflows/ai-agents/README.md) | `ai-agents` | 8 |
| [HR and recruiting](workflows/hr-recruiting/README.md) | `hr-recruiting` | 6 |
| [Finance](workflows/finance/README.md) | `finance` | 8 |

112 workflows in total. The machine-readable index is [`catalog.json`](catalog.json). Its fields are documented in [`CATALOG_SCHEMA.md`](CATALOG_SCHEMA.md) and are the contract a gallery site can consume.

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
