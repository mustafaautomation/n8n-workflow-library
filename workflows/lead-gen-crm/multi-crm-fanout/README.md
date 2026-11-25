# Fan a lead out to HubSpot, Pipedrive, and Sheets

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `lead-gen-crm` |
| Difficulty | advanced |
| Apps | Webhook, HubSpot, Pipedrive, Google Sheets |
| Time saved | The second manual copy, about 5 minutes per lead |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

During a CRM move, leads land in whichever tool the last automation was pointed at.

## Who it is for

Operators running HubSpot and Pipedrive in parallel for a quarter.

## What the workflow does

One scored lead is written to a sheet and to two CRMs. Useful when a studio is mid-migration and both systems must stay current.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

The second manual copy, about 5 minutes per lead. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/multi-crm-fanout`. Responds with the last node's JSON.
4. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
5. **Apply rules.** One score feeds both CRMs. The sheet is the audit log of what was sent.
6. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
7. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
8. **Append Fanout log.** Appends the record to the Fanout log tab. Map columns explicitly once the sheet exists.
9. **Upsert HubSpot contact.** Writes a HubSpot contact from the record.
10. **Create Pipedrive person.** Creates a Pipedrive person.
11. **Create Pipedrive deal.** Creates a Pipedrive deal.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Normalize input"]
  n3["Apply rules"]
  n4["Demo mode?"]
  n5["Package demo result"]
  n6["Append Fanout log"]
  n7["Upsert HubSpot contact"]
  n8["Create Pipedrive person"]
  n9["Create Pipedrive deal"]
  n0 --> n2
  n1 --> n2
  n2 --> n3
  n3 --> n4
  n4 -->|demo| n5
  n4 -->|live| n6
  n6 --> n7
  n7 --> n8
  n8 --> n9
```

## Sample input

Save as the webhook body, or rely on the manual trigger, which loads the same object from **Normalize input**.

```json
{
  "demo": true,
  "firstName": "Nora",
  "lastName": "Rahman",
  "email": "nora@brightline.example",
  "company": "Brightline Studio",
  "title": "Head of Operations",
  "employees": 42,
  "budget": 8000,
  "source": "demo",
  "utmSource": "linkedin",
  "utmMedium": "cpc",
  "utmCampaign": "ops-audit-q1"
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/multi-crm-fanout` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Google Sheets account** (`googleSheetsOAuth2Api`), placeholder id `PLACEHOLDER_GOOGLESHEETSOAUTH2API`
- **HubSpot account** (`hubspotOAuth2Api`), placeholder id `PLACEHOLDER_HUBSPOTOAUTH2API`
- **Pipedrive account** (`pipedriveApi`), placeholder id `PLACEHOLDER_PIPEDRIVEAPI`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Turn one CRM off by disabling its node rather than deleting it, so the migration is reversible.
- Stamp the score and the reason string onto the CRM contact so a human can see why the lead was ranked.
- Keep free-inbox leads in a nurture list instead of deleting them. The score already separates them from SQLs.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/multi-crm-fanout` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
