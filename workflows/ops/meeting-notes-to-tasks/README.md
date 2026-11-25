# Meeting notes to tasks

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `ops` |
| Difficulty | intermediate |
| Apps | Webhook, ClickUp, Notion, Slack |
| Time saved | About 10 minutes per meeting |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

Meeting notes contain actions that never become tasks.

## Who it is for

Project managers who paste notes into Slack after a call.

## What the workflow does

Notes pasted after a call are split into a task with an owner and a due date, then mirrored to Notion.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

About 10 minutes per meeting. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/meeting-notes-to-tasks`. Responds with the last node's JSON.
4. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
5. **Apply rules.** One task from the first line. Longer notes stay in the body for the person doing the work.
6. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
7. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
8. **Create ClickUp task.** Creates a ClickUp task in the list you configure.
9. **Create Notion page.** Creates a Notion page under the parent you configure.
10. **Post #clients.** Posts slackText to #clients.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Normalize input"]
  n3["Apply rules"]
  n4["Demo mode?"]
  n5["Package demo result"]
  n6["Create ClickUp task"]
  n7["Create Notion page"]
  n8["Post #clients"]
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
  "text": "@jonas Send the revised quote.\nDue 2026-12-01.\nAlso update the deck.",
  "source": "meet",
  "channel": "#clients"
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/meeting-notes-to-tasks` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **ClickUp account** (`clickUpOAuth2Api`), placeholder id `PLACEHOLDER_CLICKUPOAUTH2API`
- **Notion account** (`notionApi`), placeholder id `PLACEHOLDER_NOTIONAPI`
- **Slack account** (`slackOAuth2Api`), placeholder id `PLACEHOLDER_SLACKOAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- If a meeting produces three actions, split the notes into three webhook calls or extend the rules to emit several items.
- Require an owner and a due date before creating a task. The rules node already extracts both when they are present.
- Mirror the task id back to the Slack thread once the live branch returns it.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/meeting-notes-to-tasks` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
