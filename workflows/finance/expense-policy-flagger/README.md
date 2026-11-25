# Flag an expense that breaks policy

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `finance` |
| Difficulty | intermediate |
| Apps | Webhook, Slack, Google Sheets |
| Time saved | A few minutes per expense, and fewer reimbursements that have to be reversed |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

Expense review is a Friday pile, and out-of-policy meals are found after they are reimbursed.

## Who it is for

Small companies with a written policy and a sheet instead of an expense product.

## What the workflow does

An expense is approved, sent back for a receipt, marked as an exception, or rejected based on category caps and the merchant.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

A few minutes per expense, and fewer reimbursements that have to be reversed. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/expense-policy-flagger`. Responds with the last node's JSON.
4. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
5. **Apply rules.** Meals over 75 are exceptions even with a receipt. Missing receipts over 25 need a receipt. Casino and gift-card merchants are rejected.
6. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
7. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
8. **Append Expenses.** Appends the record to the Expenses tab. Map columns explicitly once the sheet exists.
9. **Post #expenses.** Posts slackText to #expenses.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Normalize input"]
  n3["Apply rules"]
  n4["Demo mode?"]
  n5["Package demo result"]
  n6["Append Expenses"]
  n7["Post #expenses"]
  n0 --> n2
  n1 --> n2
  n2 --> n3
  n3 --> n4
  n4 -->|demo| n5
  n4 -->|live| n6
  n6 --> n7
```

## Sample input

Save as the webhook body, or rely on the manual trigger, which loads the same object from **Normalize input**.

```json
{
  "demo": true,
  "employee": "Leo",
  "merchant": "City Bistro",
  "category": "meal",
  "amount": 96,
  "currency": "USD",
  "receipt": true
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/expense-policy-flagger` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Google Sheets account** (`googleSheetsOAuth2Api`), placeholder id `PLACEHOLDER_GOOGLESHEETSOAUTH2API`
- **Slack account** (`slackOAuth2Api`), placeholder id `PLACEHOLDER_SLACKOAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Tune the caps in the rules node to the policy you actually published.
- Match on amount and currency within the tolerance, then review the leftovers by hand.
- Never store card numbers. The samples use charge ids and amounts only.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/expense-policy-flagger` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
