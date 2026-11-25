# AI invoice and receipt extraction from Gmail to Sheets, Xero, and QuickBooks

> Portfolio demo only. This workflow is an original example for demonstration. It is not client work and it does not represent a deployment for any customer.

| | |
| --- | --- |
| Category | `invoices-docs` |
| Difficulty | advanced |
| Apps | Gmail, Google Sheets, Xero, QuickBooks |
| Time saved | About 4 minutes per invoice, around 4 hours a week at 60 bills |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

AP still downloads PDFs from Gmail and retypes the total. The ones with a tax line that does not add up get posted anyway and found at month end.

## Who it is for

Bookkeepers and the freelancers who productize 'Gmail invoices into a sheet' for agencies and trades.

## What the workflow does

A mailbox attachment is read as text, the vendor, invoice number, tax, and total are checked against each other, and a balanced bill is ready for Sheets plus either Xero or QuickBooks.

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

About 4 minutes per invoice, around 4 hours a week at 60 bills. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

1. **Overview.** Sticky note with the portfolio-demo disclaimer and how to run the offline path.
2. **Run demo.** Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.
3. **Inbound webhook.** Production-style POST webhook at `/webhook/ai-invoice-gmail-to-sheets`. Responds with the last node's JSON.
4. **Gmail trigger.** Gmail trigger for new mail. Swap the query filter in the node for the mailbox you actually use.
5. **Normalize input.** Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.
6. **Apply rules.** Pulls vendor, number, subtotal, tax, and total from the text. Route is post when the parts add up within 2 percent, otherwise review.
7. **Demo mode?.** Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.
8. **Package demo result.** Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.
9. **Append Invoices.** Appends the record to the Invoices tab. Map columns explicitly once the sheet exists.
10. **Create Xero invoice.** Creates a Xero invoice from the extracted bill.
11. **Create QuickBooks bill.** Creates a QuickBooks bill.

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
  n7["Append Invoices"]
  n8["Create Xero invoice"]
  n9["Create QuickBooks bill"]
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
  "from": "ap@northwind.example",
  "filename": "northwind-inv-2041.pdf",
  "vendor": "Northwind Supplies",
  "invoiceNumber": "INV-2041",
  "currency": "USD",
  "subtotal": 1100,
  "tax": 88,
  "total": 1188,
  "dueDate": "2026-12-15",
  "text": "Vendor: Northwind Supplies\nInvoice INV-2041\nSubtotal 1100.00\nTax 88.00\nTotal 1188.00\nDue 2026-12-15\n"
}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

1. Import `workflow.json` with n8n's Import from File. The workflow arrives inactive.
2. Select **Run demo** and execute it. **Package demo result** returns `status: demo_ready` plus the summary, route, record, and actions.
3. Create each credential listed below in n8n and choose it on the matching node. The `PLACEHOLDER_*` ids are labels, not secrets.
4. Replace every `YOUR_*` resource id (sheet, channel, list, parent page, calendar) with a resource you own.
5. Optional HTTP check: POST `sample-input.json` to `/webhook/ai-invoice-gmail-to-sheets` while the workflow is published. The default `demo: true` flag stays on the offline path.
6. Connect the live apps, send the same JSON with `"demo": false`, confirm one real record, then publish.

## Credentials

- **Gmail account** (`gmailOAuth2`), placeholder id `PLACEHOLDER_GMAILOAUTH2`
- **Google Sheets account** (`googleSheetsOAuth2Api`), placeholder id `PLACEHOLDER_GOOGLESHEETSOAUTH2API`
- **Xero account** (`xeroOAuth2Api`), placeholder id `PLACEHOLDER_XEROOAUTH2API`
- **QuickBooks account** (`quickBooksOAuth2Api`), placeholder id `PLACEHOLDER_QUICKBOOKSOAUTH2API`

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

- Use the Xero node or the QuickBooks node, not both, unless you are migrating. Disable the one you do not use.
- The Gmail trigger is the live entry. Tests start from Run demo so no mailbox is read.
- When you add a real extractor, keep the same record keys. The sheet and the ledger nodes already bind to them.
- Route unbalanced invoices to a review tab and only post the ones whose subtotal, tax, and total agree.
- Store the source filename and message id on the row so a bookkeeper can open the original PDF.

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/ai-invoice-gmail-to-sheets` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
