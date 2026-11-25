# Pipedrive deal from a web form

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `lead-gen-crm` |
| Difficulty | beginner |
| Apps | n8n Form, Pipedrive, Slack |
| Time saved | About 8 minutes per inquiry, and the deal exists before the rep reads the email |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

Website forms arrive as email. Deals get created tomorrow, after the buyer has already booked a competitor.

## Who it is for

Small B2B teams on Pipedrive who do not want a separate form tool just to open a deal.

## What the workflow does

A web form creates a Pipedrive person and a deal, then posts the new deal title to Slack. The rules node sets the stage from the budget and source.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

About 8 minutes per inquiry, and the deal exists before the rep reads the email. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/pipedrive-deal-from-web-form`. Responds with the last node's JSON.
4. **Web form.** Hosted n8n form whose fields match the sample. The submission is normalized like any other webhook.
5. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
6. **Apply rules.** Turns the form into a scored deal. Referrals and a stated budget push the stage toward appointmentscheduled.
7. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
8. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
9. **Create Pipedrive person.** Creates a Pipedrive person.
10. **Create Pipedrive deal.** Creates a Pipedrive deal.
11. **Post #pipeline.** Posts slackText to #pipeline.

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
  n7["Create Pipedrive person"]
  n8["Create Pipedrive deal"]
  n9["Post #pipeline"]
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
  "company": "Northwind Supplies",
  "title": "Head of Operations",
  "employees": 42,
  "budget": 12000,
  "source": "referral",
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
5. Optional HTTP check: POST `sample-input.json` to `/webhook/pipedrive-deal-from-web-form` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Pipedrive account** (`pipedriveApi`), placeholder id `PLACEHOLDER_PIPEDRIVEAPI`
- **Slack account** (`slackOAuth2Api`), placeholder id `PLACEHOLDER_SLACKOAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Pipedrive deal title uses record.dealName. Change the template in Apply rules if your pipeline wants a different pattern.
- Add the pipeline id on the deal node. The demo leaves it for you because pipelines are account-specific.
- Stamp the score and the reason string onto the CRM contact so a human can see why the lead was ranked.
- Keep free-inbox leads in a nurture list instead of deleting them. The score already separates them from SQLs.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/pipedrive-deal-from-web-form` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
