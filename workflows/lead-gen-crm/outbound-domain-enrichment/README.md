# Outbound domain enrichment into the CRM

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `lead-gen-crm` |
| Difficulty | advanced |
| Apps | Webhook, HTTP Request, HubSpot, Google Sheets |
| Time saved | About 8 minutes of research per account |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

Outbound lists are company names and a domain. Reps research them one tab at a time.

## Who it is for

Appointment setters building a list from a directory, not from inbound forms.

## What the workflow does

A domain and a guessed contact are scored and queued. The live branch can call an enrichment HTTP API before the HubSpot upsert.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

About 8 minutes of research per account. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/outbound-domain-enrichment`. Responds with the last node's JSON.
4. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
5. **Apply rules.** Outbound has no budget, so budget points stay at zero. A founder title and headcount still produce a usable tier.
6. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
7. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
8. **HTTP POST.** Posts the record to an HTTP endpoint you control. Swap example.com for your API.
9. **Upsert HubSpot contact.** Writes a HubSpot contact from the record.
10. **Append Outbound.** Appends the record to the Outbound tab. Map columns explicitly once the sheet exists.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Normalize input"]
  n3["Apply rules"]
  n4["Demo mode?"]
  n5["Package demo result"]
  n6["HTTP POST"]
  n7["Upsert HubSpot contact"]
  n8["Append Outbound"]
  n0 --> n2
  n1 --> n2
  n2 --> n3
  n3 --> n4
  n4 -->|demo| n5
  n4 -->|live| n6
  n6 --> n7
  n7 --> n8
```

## Sample input

Save as the webhook body, or rely on the manual trigger, which loads the same object from **Normalize input**.

```json
{
  "demo": true,
  "email": "ada@northwind.example",
  "company": "Northwind Supplies",
  "domain": "northwind.example",
  "employees": 80,
  "title": "Founder",
  "source": "outbound",
  "budget": 0
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/outbound-domain-enrichment` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **HubSpot account** (`hubspotOAuth2Api`), placeholder id `PLACEHOLDER_HUBSPOTOAUTH2API`
- **Google Sheets account** (`googleSheetsOAuth2Api`), placeholder id `PLACEHOLDER_GOOGLESHEETSOAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Replace example.com/enrich with your enrichment vendor and map its JSON onto record before HubSpot.
- Stamp the score and the reason string onto the CRM contact so a human can see why the lead was ranked.
- Keep free-inbox leads in a nurture list instead of deleting them. The score already separates them from SQLs.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/outbound-domain-enrichment` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
