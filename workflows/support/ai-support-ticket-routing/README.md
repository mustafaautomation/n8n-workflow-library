# AI support ticket classification and routing

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `support` |
| Difficulty | intermediate |
| Apps | Webhook, Zendesk, Freshdesk, Slack |
| Time saved | About 1 minute of triage per ticket, which is the whole first touch on a busy desk |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

New tickets land in a single queue. Billing and outages wait behind password resets.

## Who it is for

Support leads and freelancers implementing Zendesk or Freshdesk for a small team.

## What the workflow does

A ticket is classed as billing, technical, account, or general. The same decision opens a Zendesk ticket and a Freshdesk ticket so you can keep the desk you actually use, and Slack hears about technical and billing.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

About 1 minute of triage per ticket, which is the whole first touch on a busy desk. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/ai-support-ticket-routing`. Responds with the last node's JSON.
4. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
5. **Apply rules.** The words broken and 500 route the ticket to technical. Billing, account, and general stay available for other wording. Disable the desk you do not use.
6. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
7. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
8. **Create Zendesk ticket.** Opens a Zendesk ticket with the subject, body, and priority on the record.
9. **Create Freshdesk ticket.** Opens a Freshdesk ticket with the same fields.
10. **Post #support.** Posts slackText to #support.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Normalize input"]
  n3["Apply rules"]
  n4["Demo mode?"]
  n5["Package demo result"]
  n6["Create Zendesk ticket"]
  n7["Create Freshdesk ticket"]
  n8["Post #support"]
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
  "from": "ada@northwind.example",
  "subject": "Checkout returns 500",
  "body": "The checkout is broken and returns a 500 after submit.",
  "email": "ada@northwind.example"
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/ai-support-ticket-routing` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Zendesk account** (`zendeskApi`), placeholder id `PLACEHOLDER_ZENDESKAPI`
- **Freshdesk account** (`freshdeskApi`), placeholder id `PLACEHOLDER_FRESHDESKAPI`
- **Slack account** (`slackOAuth2Api`), placeholder id `PLACEHOLDER_SLACKOAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Disable the desk you do not use. Both are on the canvas so a buyer can pick Zendesk or Freshdesk.
- Write the route into the ticket tag. The record label is the tag.
- Password resets should not page Slack. Filter the Slack node to technical and billing.
- Write the chosen queue back onto the ticket so reporting matches the route.
- After-hours acknowledgements should promise a window, not a resolution.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/ai-support-ticket-routing` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
