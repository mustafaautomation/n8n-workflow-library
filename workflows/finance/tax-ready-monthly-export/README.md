# Tax-ready monthly export

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `finance` |
| Difficulty | intermediate |
| Apps | Schedule, Google Sheets, Gmail |
| Time saved | About an hour a month of reconstruction |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

Sales tax is reconstructed in March from memory and Stripe screenshots.

## Who it is for

Founders who owe an accountant a monthly packet.

## What the workflow does

A month of revenue and tax collected is rolled up and emailed as the packet an accountant asked for.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

About an hour a month of reconstruction. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/tax-ready-monthly-export`. Responds with the last node's JSON.
4. **Weekday schedule.** Schedule trigger for the recurring version of this workflow. Tests start from Run demo instead.
5. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
6. **Apply rules.** Sums revenue and tax collected. It does not file anything.
7. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
8. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
9. **Append Tax.** Appends the record to the Tax tab. Map columns explicitly once the sheet exists.
10. **Send Gmail.** Gmail send using the subject and body on the record.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Weekday schedule"]
  n3["Normalize input"]
  n4["Apply rules"]
  n5["Demo mode?"]
  n6["Package demo result"]
  n7["Append Tax"]
  n8["Send Gmail"]
  n0 --> n3
  n1 --> n3
  n2 --> n3
  n3 --> n4
  n4 --> n5
  n5 -->|demo| n6
  n5 -->|live| n7
  n7 --> n8
```

## Sample input

Save as the webhook body, or rely on the manual trigger, which loads the same object from **Normalize input**.

```json
{
  "demo": true,
  "period": "2026-11",
  "rows": [
    {
      "revenue": 4200,
      "taxCollected": 336
    }
  ],
  "previous": {
    "revenue": 3900,
    "taxCollected": 312
  }
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/tax-ready-monthly-export` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Google Sheets account** (`googleSheetsOAuth2Api`), placeholder id `PLACEHOLDER_GOOGLESHEETSOAUTH2API`
- **Gmail account** (`gmailOAuth2`), placeholder id `PLACEHOLDER_GMAILOAUTH2`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- This is a packet, not tax advice. Your accountant decides what is owed.
- Match on amount and currency within the tolerance, then review the leftovers by hand.
- Never store card numbers. The samples use charge ids and amounts only.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/tax-ready-monthly-export` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
