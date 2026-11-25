# AI agent with memory, a pricing tool, and a sheet tool

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `ai-agents` |
| Difficulty | advanced |
| Apps | AI Agent, Groq, Google Sheets, Slack |
| Time saved | Repeated policy answers, several a day, at a couple of minutes each |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

People ask the same pricing and policy questions in Slack, and the answers drift depending on who is online.

## Who it is for

Freelancers selling an n8n AI agent, and teams who want the tool wiring visible before they add a key.

## What the workflow does

A question is answered from a local pricing book in demo mode. On the live branch an n8n AI Agent uses Groq, a short memory, a code tool for prices, an HTTP tool, and a Google Sheets tool, then posts the reply to Slack.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

Repeated policy answers, several a day, at a couple of minutes each. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/ai-agent-with-tools`. Responds with the last node's JSON.
4. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
5. **Apply rules.** Matches the word pricing and returns the three plan prices. Unknown questions list the topics the book contains.
6. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
7. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
8. **AI Agent.** n8n AI Agent. It receives the prompt built by Apply rules and may call the tools wired underneath it.
9. **Groq chat model.** Groq chat model on the free-tier friendly path. Swap the model name for the one your key can call.
10. **Window memory.** Keeps the last eight turns for this session id. Use a per-user session id in production.
11. **lookup_pricing.** Look up a plan price. Input should name starter, growth, or scale. Implemented as a Code tool so the contract is visible in the canvas.
12. **fetch_public_page.** Fetch a public page. Replace example.com with an API you are allowed to call. HTTP tool. Point the URL at your API before turning demo mode off.
13. **read_pricing_sheet.** Google Sheets tool the agent can read. Replace YOUR_SPREADSHEET_ID.
14. **Post #assistant.** Posts slackText to #assistant.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Normalize input"]
  n3["Apply rules"]
  n4["Demo mode?"]
  n5["Package demo result"]
  n6["AI Agent"]
  n7["Groq chat model"]
  n8["Window memory"]
  n9["lookup_pricing"]
  n10["fetch_public_page"]
  n11["read_pricing_sheet"]
  n12["Post #assistant"]
  n0 --> n2
  n1 --> n2
  n2 --> n3
  n3 --> n4
  n4 -->|demo| n5
  n4 -->|live| n6
  n6 --> n7
  n7 --> n8
  n8 --> n9
  n9 --> n10
  n10 --> n11
  n11 --> n12
```

## Sample input

Save as the webhook body, or rely on the manual trigger, which loads the same object from **Normalize input**.

```json
{
  "demo": true,
  "prompt": "What is growth pricing for a monthly plan?",
  "sessionId": "portfolio-demo"
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/ai-agent-with-tools` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Slack account** (`slackOAuth2Api`), placeholder id `PLACEHOLDER_SLACKOAUTH2API`
- **Groq account** (`groqApi`), placeholder id `PLACEHOLDER_GROQAPI`
- **Google Sheets account** (`googleSheetsOAuth2Api`), placeholder id `PLACEHOLDER_GOOGLESHEETSOAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Groq is on the live branch so a free-tier key can run the agent. Demo mode does not call it.
- The code tool is the source of truth for prices. Do not also paste prices into the system message.
- Memory is keyed by sessionId. Pass a user id in production so two people do not share a window.
- Keep the system message strict: tools for facts, no invented prices or dates.
- The demo answer is a local lookup. The agent on the live branch is what you point at Groq or Claude.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/ai-agent-with-tools` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
