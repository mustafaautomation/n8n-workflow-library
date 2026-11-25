# Failed payment dunning sequence

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `finance` |
| Difficulty | intermediate |
| Apps | Stripe, Gmail, Slack |
| Time saved | The dunning emails, and the revenue that a day-three reminder still saves |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

Failed cards are noticed when the customer has already churned.

## Who it is for

Subscription businesses on Stripe.

## What the workflow does

A failed charge is placed on step 1, 2, or 3 from how many days have passed. The email is drafted. The last step is marked final.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

The dunning emails, and the revenue that a day-three reminder still saves. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/failed-payment-dunning`. Responds with the last node's JSON.
4. **Stripe trigger.** Stripe trigger for charge and payout events.
5. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
6. **Apply rules.** Steps at day 0, day 3, and day 7. The sample failed on the 22nd, so the step depends on the clock when you run it.
7. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
8. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
9. **Create Gmail draft.** Gmail draft using the subject and body on the record.
10. **Post #billing.** Posts slackText to #billing.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Stripe trigger"]
  n3["Normalize input"]
  n4["Apply rules"]
  n5["Demo mode?"]
  n6["Package demo result"]
  n7["Create Gmail draft"]
  n8["Post #billing"]
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
  "email": "billing@brightline.example",
  "customer": "Brightline Studio",
  "amount": 149,
  "currency": "USD",
  "failedAt": "2026-11-22T08:00:00.000Z"
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/failed-payment-dunning` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Stripe account** (`stripeApi`), placeholder id `PLACEHOLDER_STRIPEAPI`
- **Gmail account** (`gmailOAuth2`), placeholder id `PLACEHOLDER_GMAILOAUTH2`
- **Slack account** (`slackOAuth2Api`), placeholder id `PLACEHOLDER_SLACKOAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Stop the sequence when a later charge succeeds. Key the sheet on the customer.
- Match on amount and currency within the tolerance, then review the leftovers by hand.
- Never store card numbers. The samples use charge ids and amounts only.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/failed-payment-dunning` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
