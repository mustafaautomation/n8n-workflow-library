# Missed-call text-back

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `speed-to-lead` |
| Difficulty | beginner |
| Apps | Twilio, Slack, Google Sheets |
| Time saved | A same-minute text instead of a next-day callback, on every missed call |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

Missed calls go to voicemail and get returned the next morning, after the caller hired someone who picked up.

## Who it is for

Local service businesses and any sales line that still relies on voicemail.

## What the workflow does

A missed inbound call becomes an immediate text from a named owner, a sheet row, and a Slack alert. The copy changes if the call arrived after hours.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

A same-minute text instead of a next-day callback, on every missed call. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/missed-call-text-back`. Responds with the last node's JSON.
4. **Twilio voice trigger.** Twilio trigger standing in for the missed-call or voice webhook.
5. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
6. **Apply rules.** Treats the missed call as a lead with a two-minute window. The SMS names the front desk.
7. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
8. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
9. **Send SMS.** Sends the SMS (or places the call) using the phone and message on the record.
10. **Append Missed calls.** Appends the record to the Missed calls tab. Map columns explicitly once the sheet exists.
11. **Post #calls.** Posts slackText to #calls.

## Diagram

```mermaid
flowchart LR
  n0["Run demo"]
  n1["Inbound webhook"]
  n2["Twilio voice trigger"]
  n3["Normalize input"]
  n4["Apply rules"]
  n5["Demo mode?"]
  n6["Package demo result"]
  n7["Send SMS"]
  n8["Append Missed calls"]
  n9["Post #calls"]
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
  "firstName": "there",
  "phone": "+15555550198",
  "company": "the caller",
  "source": "missed-call",
  "receivedAt": "2026-11-25T08:01:00.000Z",
  "afterHours": false
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/missed-call-text-back` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Twilio account** (`twilioApi`), placeholder id `PLACEHOLDER_TWILIOAPI`
- **Google Sheets account** (`googleSheetsOAuth2Api`), placeholder id `PLACEHOLDER_GOOGLESHEETSOAUTH2API`
- **Slack account** (`slackOAuth2Api`), placeholder id `PLACEHOLDER_SLACKOAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Gate the SMS on a duration of zero or a no-answer status from the Twilio payload.
- After-hours copy can mention the next open window. Add that sentence in Apply rules when afterHours is true.
- Measure from the form timestamp, not from when n8n woke up. The sample's receivedAt field is that timestamp.
- Put the on-call owner in the message body so the lead sees a name, not a no-reply inbox.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/missed-call-text-back` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
