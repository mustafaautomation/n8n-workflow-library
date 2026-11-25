# Guarded email reply agent

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `ai-agents` |
| Difficulty | advanced |
| Apps | Gmail, AI Agent, Groq |
| Time saved | The first draft, a few minutes, with fewer policy mistakes |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

An unbounded email agent will promise a refund the policy does not allow.

## Who it is for

Teams experimenting with an inbox agent.

## What the workflow does

A reply is drafted from a policy book. The live agent may call Gmail only to create a draft, never to send.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

The first draft, a few minutes, with fewer policy mistakes. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/guarded-email-reply-agent`. Responds with the last node's JSON.
4. **Gmail trigger.** Gmail trigger for new mail. Swap the query filter in the node for the mailbox you actually use.
5. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
6. **Apply rules.** The refund topic returns the policy and an instruction to draft, not send.
7. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
8. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
9. **AI Agent.** n8n AI Agent. It receives the prompt built by Apply rules and may call the tools wired underneath it.
10. **Groq chat model.** Groq chat model on the free-tier friendly path. Swap the model name for the one your key can call.
11. **Window memory.** Keeps the last eight turns for this session id. Use a per-user session id in production.
12. **lookup_policy.** Return the refund or shipping policy. Implemented as a Code tool so the contract is visible in the canvas.
13. **Create Gmail draft.** Gmail draft using the subject and body on the record.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Gmail trigger"]
  n3["Normalize input"]
  n4["Apply rules"]
  n5["Demo mode?"]
  n6["Package demo result"]
  n7["AI Agent"]
  n8["Groq chat model"]
  n9["Window memory"]
  n10["lookup_policy"]
  n11["Create Gmail draft"]
  n0 --> n3
  n1 --> n3
  n2 --> n3
  n3 --> n4
  n4 --> n5
  n5 -->|demo| n6
  n5 -->|live| n7
  n7 --> n8
  n8 --> n9
  n9 --> n10
  n10 --> n11
```

## Sample input

Save as the webhook body, or rely on the manual trigger, which loads the same object from **Normalize input**.

```json
{
  "demo": true,
  "prompt": "Customer asked for a refund of last Tuesday's charge.",
  "sessionId": "inbox"
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/guarded-email-reply-agent` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Gmail account** (`gmailOAuth2`), placeholder id `PLACEHOLDER_GMAILOAUTH2`
- **Groq account** (`groqApi`), placeholder id `PLACEHOLDER_GROQAPI`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Do not put a Gmail send node on this canvas. Draft is the ceiling.
- Keep the system message strict: tools for facts, no invented prices or dates.
- The demo answer is a local lookup. The agent on the live branch is what you point at Groq or Claude.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/guarded-email-reply-agent` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
