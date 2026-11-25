# Flag a booking that breaks the buffer

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `booking` |
| Difficulty | advanced |
| Apps | Calendly, Slack, Google Calendar |
| Time saved | The scramble of a double book, which is worse than the few minutes of setup |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

Back-to-back calls get booked across the 10-minute buffer the host thought was protected.

## Who it is for

Hosts who sell 25-minute calls and need 10 minutes between them.

## What the workflow does

A new booking is summarized and Slack is warned when the payload says it overlaps the previous meeting's buffer.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

The scramble of a double book, which is worse than the few minutes of setup. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/buffer-conflict-check`. Responds with the last node's JSON.
4. **Calendly trigger.** Calendly trigger for invitee created and canceled. Cal.com bookings can use the inbound webhook.
5. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
6. **Apply rules.** Builds the reminder plan. Compare start with previousEnd on the payload and page Slack when the gap is under 10 minutes.
7. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
8. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
9. **Post #calendar-conflicts.** Posts slackText to #calendar-conflicts.
10. **Create calendar event.** Creates the calendar event from record.start and record.end.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Calendly trigger"]
  n3["Normalize input"]
  n4["Apply rules"]
  n5["Demo mode?"]
  n6["Package demo result"]
  n7["Post #calendar-conflicts"]
  n8["Create calendar event"]
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
  "email": "nora@brightline.example",
  "phone": "+15555550123",
  "title": "Ops audit with Brightline",
  "start": "2026-12-02T15:00:00.000Z",
  "end": "2026-12-02T15:30:00.000Z",
  "status": "booked",
  "previousEnd": "2026-12-02T14:55:00.000Z"
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/buffer-conflict-check` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Calendly account** (`calendlyOAuth2Api`), placeholder id `PLACEHOLDER_CALENDLYOAUTH2API`
- **Slack account** (`slackOAuth2Api`), placeholder id `PLACEHOLDER_SLACKOAUTH2API`
- **Google Calendar account** (`googleCalendarOAuth2Api`), placeholder id `PLACEHOLDER_GOOGLECALENDAROAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Do the gap math in Apply rules once you trust the timestamp format your calendar sends.
- Convert reminder offsets to the guest's timezone before you send the SMS.
- A cancellation should stop the remaining reminders. The route field is there for that branch.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/buffer-conflict-check` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
