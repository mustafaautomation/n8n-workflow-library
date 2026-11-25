# AI lead capture, enrichment, and scoring into HubSpot

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `lead-gen-crm` |
| Difficulty | intermediate |
| Apps | Web form, HubSpot, Slack, Google Sheets |
| Time saved | About 15 minutes per lead, roughly 6 hours a week at 25 leads |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

Inbound leads sit in a form inbox while someone copies them into HubSpot and guesses which ones deserve a same-day call. The ones with a work email, a real headcount, and a pricing or demo source get the same delay as a student Gmail address.

## Who it is for

Freelance automation builders and in-house ops leads who sell B2B services and already live in HubSpot.

## What the workflow does

A new lead is normalized, scored from firmographic and intent signals, written to HubSpot, mirrored to a sheet, and announced in Slack when the tier is SQL.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

About 15 minutes per lead, roughly 6 hours a week at 25 leads. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/ai-lead-enrich-score-hubspot`. Responds with the last node's JSON.
4. **Web form.** Hosted n8n form whose fields match the sample. The submission is normalized like any other webhook.
5. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
6. **Apply rules.** Scores the lead from work-email, headcount, source, budget, and title. SQL is 75 or above.
7. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
8. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
9. **Upsert HubSpot contact.** Writes a HubSpot contact from the record.
10. **Append Leads.** Appends the record to the Leads tab. Map columns explicitly once the sheet exists.
11. **Post #sales.** Posts slackText to #sales.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Web form"]
  n3["Normalize input"]
  n4["Apply rules"]
  n5["Demo mode?"]
  n6["Package demo result"]
  n7["Upsert HubSpot contact"]
  n8["Append Leads"]
  n9["Post #sales"]
  n0 --> n3
  n1 --> n3
  n2 --> n3
  n3 --> n4
  n4 --> n5
  n5 -->|demo| n6
  n5 -->|live| n7
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
5. Optional HTTP check: POST `sample-input.json` to `/webhook/ai-lead-enrich-score-hubspot` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **HubSpot account** (`hubspotOAuth2Api`), placeholder id `PLACEHOLDER_HUBSPOTOAUTH2API`
- **Google Sheets account** (`googleSheetsOAuth2Api`), placeholder id `PLACEHOLDER_GOOGLESHEETSOAUTH2API`
- **Slack account** (`slackOAuth2Api`), placeholder id `PLACEHOLDER_SLACKOAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Map HubSpot properties to score, tier, and reasons before you turn demo mode off. The record already uses those names.
- Only Slack the SQL tier if the channel is noisy. Filter on route inside the Slack node.
- Stamp the score and the reason string onto the CRM contact so a human can see why the lead was ranked.
- Keep free-inbox leads in a nurture list instead of deleting them. The score already separates them from SQLs.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/ai-lead-enrich-score-hubspot` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
