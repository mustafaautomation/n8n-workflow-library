"""Build importable n8n workflow JSON, READMEs, and Mermaid diagrams.

Workflows are portfolio demos. The manual trigger always feeds a local rules
engine so `n8n execute` can succeed without paid API credits. The false branch
of "Demo mode?" is the live path a buyer connects to real credentials.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

DISCLAIMER = (
    "Portfolio demo only. This workflow is an original example for demonstration. "
    "It is not client work and it does not represent a deployment for any customer."
)


def _id() -> str:
    return str(uuid.uuid4())


def _cred(cred_type: str, cred_name: str) -> dict[str, Any]:
    token = "".join(ch if ch.isalnum() else "_" for ch in cred_type).upper()
    return {
        cred_type: {
            "id": f"PLACEHOLDER_{token}",
            "name": cred_name,
        }
    }


class Builder:
    def __init__(self, spec: dict[str, Any]) -> None:
        self.spec = spec
        self.nodes: list[dict[str, Any]] = []
        self.connections: dict[str, dict[str, list]] = {}
        self.explained: list[tuple[str, str]] = []
        self._trigger_names: list[tuple[str, str]] = []

    def add(self, name: str, node_type: str, type_version: float | int, parameters: dict, x: int, y: int, *, credentials: dict | None = None, notes: str | None = None, webhook: bool = False, disabled: bool = False) -> str:
        node: dict[str, Any] = {
            "parameters": parameters,
            "id": _id(),
            "name": name,
            "type": node_type,
            "typeVersion": type_version,
            "position": [x, y],
        }
        if credentials:
            node["credentials"] = credentials
        if notes:
            node["notes"] = notes
            node["notesInFlow"] = True
        if webhook:
            node["webhookId"] = _id()
        if disabled:
            node["disabled"] = True
        self.nodes.append(node)
        return name

    def link(self, source: str, target: str, output: int = 0, conn_type: str = "main", input_index: int = 0) -> None:
        bucket = self.connections.setdefault(source, {}).setdefault(conn_type, [])
        while len(bucket) <= output:
            bucket.append([])
        bucket[output].append({"node": target, "type": conn_type, "index": input_index})

    def explain(self, name: str, text: str) -> None:
        self.explained.append((name, text))

    def build(self) -> dict[str, Any]:
        spec = self.spec
        title = spec["title"]
        sample = spec["sample"]
        pattern = spec.get("pattern", "linear")

        self.add(
            "Overview",
            "n8n-nodes-base.stickyNote",
            1,
            {
                "content": (
                    f"## {title}\n\n"
                    f"{DISCLAIMER}\n\n"
                    "Run **Run demo** to execute the offline rules engine. "
                    "The live branch is used only when the incoming item sets `demo` to false "
                    "and the placeholder credentials have been replaced."
                ),
                "height": 220,
                "width": 520,
                "color": 4,
            },
            -40,
            -40,
        )
        self.explain("Overview", "Sticky note with the portfolio-demo disclaimer and how to run the offline path.")

        self.add(
            "Run demo",
            "n8n-nodes-base.manualTrigger",
            1,
            {},
            40,
            280,
            notes="CLI and the n8n editor start here. An empty manual run loads the bundled sample.",
        )
        self.explain("Run demo", "Manual trigger used by the editor and by `n8n execute`. With no payload, the next node loads the sample.")

        webhook_path = spec["id"]
        self.add(
            "Inbound webhook",
            "n8n-nodes-base.webhook",
            2,
            {
                "httpMethod": "POST",
                "path": webhook_path,
                "authentication": "none",
                "responseMode": "lastNode",
                "responseData": "firstEntryJson",
                "options": {},
            },
            40,
            460,
            webhook=True,
            notes="POST JSON to this path. Include demo:false only after credentials are connected.",
        )
        self.explain(
            "Inbound webhook",
            f"Production-style POST webhook at `/webhook/{webhook_path}`. Responds with the last node's JSON.",
        )

        trigger_y = 640
        for trigger in spec.get("triggers", []):
            built = self._extra_trigger(trigger, 40, trigger_y)
            if built:
                trigger_y += 160

        self.add(
            "Normalize input",
            "n8n-nodes-base.code",
            2,
            {
                "mode": "runOnceForAllItems",
                "language": "javaScript",
                "jsCode": _normalize_js(sample),
            },
            340,
            360,
            notes="Merges the request over the bundled sample. demo stays true unless the caller explicitly turns it off.",
        )
        self.explain(
            "Normalize input",
            "Fills any missing fields from the checked-in sample and forces an explicit demo flag. An empty manual run therefore always has something valid to score.",
        )

        self.add(
            "Apply rules",
            "n8n-nodes-base.code",
            2,
            {
                "mode": "runOnceForAllItems",
                "language": "javaScript",
                "jsCode": _logic_wrapper(spec["logic_js"]),
            },
            620,
            360,
            notes="Deterministic stand-in for the model or enrichment API. Replace or precede this with a live model node when you turn demo mode off.",
        )
        self.explain("Apply rules", spec.get("logic_summary") or "Runs the workflow's deterministic rules and returns summary, route, record, and actions.")

        self.add(
            "Demo mode?",
            "n8n-nodes-base.if",
            2.2,
            {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "strict",
                        "version": 2,
                    },
                    "conditions": [
                        {
                            "id": _id(),
                            "leftValue": "={{ $json.demo }}",
                            "rightValue": True,
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            900,
            360,
            notes="True: package the offline result. False: run the credentialed apps.",
        )
        self.explain("Demo mode?", "Routes to the offline result while `demo` is true. The live apps run only when a caller sends demo:false.")

        self.add(
            "Package demo result",
            "n8n-nodes-base.code",
            2,
            {
                "mode": "runOnceForAllItems",
                "language": "javaScript",
                "jsCode": _package_js(spec["id"]),
            },
            1180,
            180,
        )
        self.explain(
            "Package demo result",
            "Shapes the object returned to the editor, the CLI, and the webhook: summary, route, record, and the actions the live branch would have taken.",
        )

        self.link("Run demo", "Normalize input")
        self.link("Inbound webhook", "Normalize input")
        for name, _ in self._trigger_names:
            self.link(name, "Normalize input")
        self.link("Normalize input", "Apply rules")
        self.link("Apply rules", "Demo mode?")
        self.link("Demo mode?", "Package demo result", 0)

        if pattern == "agent":
            self._build_agent()
        elif pattern == "rag":
            self._build_rag()
        else:
            self._build_linear_live()

        self.add(
            "Live path",
            "n8n-nodes-base.stickyNote",
            1,
            {
                "content": (
                    "## Live path\n\n"
                    "Replace every `PLACEHOLDER_*` credential, then POST the sample with `\"demo\": false`.\n\n"
                    "The nodes on this branch use the `record` and `actions` fields produced by Apply rules."
                ),
                "height": 180,
                "width": 420,
                "color": 6,
            },
            1120,
            520,
        )

        return {
            "name": title,
            "nodes": self.nodes,
            "connections": self.connections,
            "pinData": {},
            "settings": {"executionOrder": "v1"},
            "staticData": None,
            "meta": {
                "templateCredsSetupCompleted": False,
                "description": spec["description"],
            },
            "active": False,
        }

    def _extra_trigger(self, trigger: str, x: int, y: int) -> str | None:
        kind, _, arg = trigger.partition(":")
        name: str | None = None
        if kind == "schedule":
            name = "Weekday schedule"
            self.add(
                name,
                "n8n-nodes-base.scheduleTrigger",
                1.2,
                {"rule": {"interval": [{"field": "weeks", "triggerAtDay": [1], "triggerAtHour": 8, "triggerAtMinute": 15}]}},
                x,
                y,
                notes="Monday 08:15. The manual trigger and webhook remain available for tests.",
            )
            self.explain(name, "Schedule trigger for the recurring version of this workflow. Tests start from Run demo instead.")
        elif kind == "gmail":
            name = "Gmail trigger"
            self.add(
                name,
                "n8n-nodes-base.gmailTrigger",
                1.2,
                {"authentication": "oAuth2", "event": "messageReceived", "simple": True},
                x,
                y,
                credentials=_cred("gmailOAuth2", "Gmail account"),
                notes="Polls the mailbox once credentials replace the placeholder. Tests do not call Gmail.",
            )
            self.explain(name, "Gmail trigger for new mail. Swap the query filter in the node for the mailbox you actually use.")
        elif kind == "form":
            name = "Web form"
            self.add(
                name,
                "n8n-nodes-base.formTrigger",
                2.2,
                {
                    "formTitle": arg or self.spec["title"],
                    "formDescription": "Portfolio demo form. Submissions land in the same rules engine as the webhook.",
                    "responseMode": "lastNode",
                    "formFields": {"values": _form_fields(self.spec["sample"])},
                },
                x,
                y,
                webhook=True,
                notes="n8n Form trigger. Field names match the sample payload.",
            )
            self.explain(name, "Hosted n8n form whose fields match the sample. The submission is normalized like any other webhook.")
        elif kind == "shopify":
            name = "Shopify order trigger"
            self.add(
                name,
                "n8n-nodes-base.shopifyTrigger",
                1,
                {"topic": "orders/create"},
                x,
                y,
                credentials=_cred("shopifyAccessTokenApi", "Shopify access token"),
                notes="Fires on orders/create after the Shopify credential is connected.",
            )
            self.explain(name, "Shopify trigger for orders/create. The demo path uses the bundled order instead of calling Shopify.")
        elif kind == "woo":
            name = "WooCommerce order trigger"
            self.add(
                name,
                "n8n-nodes-base.wooCommerceTrigger",
                1,
                {"event": "order.created"},
                x,
                y,
                credentials=_cred("wooCommerceApi", "WooCommerce account"),
                notes="Fires on order.created after the store credential is connected.",
            )
            self.explain(name, "WooCommerce trigger for order.created.")
        elif kind == "stripe":
            name = "Stripe trigger"
            self.add(
                name,
                "n8n-nodes-base.stripeTrigger",
                1,
                {"events": ["charge.succeeded", "charge.failed", "payout.paid"]},
                x,
                y,
                credentials=_cred("stripeApi", "Stripe account"),
                notes="Listens for charge and payout events. The demo uses the sample event.",
            )
            self.explain(name, "Stripe trigger for charge and payout events.")
        elif kind == "twilio":
            name = "Twilio voice trigger"
            self.add(
                name,
                "n8n-nodes-base.twilioTrigger",
                1,
                {"updates": ["com.twilio.voice.insights.call-summary.complete"]},
                x,
                y,
                credentials=_cred("twilioApi", "Twilio account"),
                notes="Voice event source for missed-call flows. The demo posts the sample call instead.",
            )
            self.explain(name, "Twilio trigger standing in for the missed-call or voice webhook.")
        elif kind == "calendly":
            name = "Calendly trigger"
            self.add(
                name,
                "n8n-nodes-base.calendlyTrigger",
                1,
                {"events": ["invitee.created", "invitee.canceled"]},
                x,
                y,
                credentials=_cred("calendlyOAuth2Api", "Calendly account"),
                notes="invitee.created and invitee.canceled. Cal.com can hit the inbound webhook with the same payload shape.",
            )
            self.explain(name, "Calendly trigger for invitee created and canceled. Cal.com bookings can use the inbound webhook.")
        elif kind == "rss":
            name = "RSS feed"
            self.add(
                name,
                "n8n-nodes-base.rssFeedReadTrigger",
                1,
                {"feedUrl": "https://example.com/feed.xml"},
                x,
                y,
                notes="Point the feed URL at the blog or YouTube RSS before activating.",
            )
            self.explain(name, "RSS trigger. Set the feed URL on the node before publishing the workflow.")
        elif kind == "slack":
            name = "Slack trigger"
            self.add(
                name,
                "n8n-nodes-base.slackTrigger",
                1,
                {"trigger": ["message"], "watchWorkspace": False, "channelId": _rl("YOUR_SLACK_CHANNEL_ID")},
                x,
                y,
                credentials=_cred("slackApi", "Slack bot"),
                notes="Watches a channel for messages that should become tasks. Demo uses the sample message.",
            )
            self.explain(name, "Slack trigger for channel messages. Restrict it to the ops channel after you connect the bot.")
        else:
            return None
        self._trigger_names.append((name, kind))
        return name

    def _build_linear_live(self) -> None:
        previous = None
        x = 1180
        y = 760
        for index, action in enumerate(self.spec.get("live", [])):
            name, node = _live_node(action, x, y)
            # re-add via add() by unpacking the constructed node
            self.nodes.append(node)
            self.explain(name, _live_explanation(action))
            if previous is None:
                self.link("Demo mode?", name, 1)
            else:
                self.link(previous, name)
            previous = name
            x += 280
        if previous is None:
            self.add(
                "Live path not configured",
                "n8n-nodes-base.code",
                2,
                {
                    "mode": "runOnceForAllItems",
                    "language": "javaScript",
                    "jsCode": "throw new Error('Connect a destination app on this branch before turning demo mode off.');",
                },
                1180,
                760,
            )
            self.link("Demo mode?", "Live path not configured", 1)

    def _build_agent(self) -> None:
        agent = "AI Agent"
        self.add(
            agent,
            "@n8n/n8n-nodes-langchain.agent",
            3.1,
            {
                "promptType": "define",
                "text": "={{ $json.prompt || $json.summary }}",
                "options": {"systemMessage": self.spec.get("system_message") or "You are a careful operations assistant. Use tools for facts. Never invent prices, dates, or customer data."},
            },
            1220,
            780,
            notes="Live agent. Demo mode answers from Apply rules so tests do not spend model credits.",
        )
        self.explain(agent, "n8n AI Agent. It receives the prompt built by Apply rules and may call the tools wired underneath it.")
        self.link("Demo mode?", agent, 1)

        model_name = "Anthropic chat model" if self.spec.get("model") == "anthropic" else "Groq chat model"
        if self.spec.get("model") == "anthropic":
            self.add(
                model_name,
                "@n8n/n8n-nodes-langchain.lmChatAnthropic",
                1.6,
                {
                    "model": {"__rl": True, "mode": "list", "value": "claude-sonnet-5", "cachedResultName": "Claude Sonnet"},
                    "options": {"temperature": 0.2},
                },
                980,
                980,
                credentials=_cred("anthropicApi", "Anthropic account"),
            )
            self.explain(model_name, "Claude chat model attached to the agent. The demo path never calls it.")
        else:
            self.add(
                model_name,
                "@n8n/n8n-nodes-langchain.lmChatGroq",
                1,
                {"model": "llama-3.3-70b-versatile", "options": {"temperature": 0.2}},
                980,
                980,
                credentials=_cred("groqApi", "Groq account"),
            )
            self.explain(model_name, "Groq chat model on the free-tier friendly path. Swap the model name for the one your key can call.")
        self.link(model_name, agent, 0, "ai_languageModel")

        self.add(
            "Window memory",
            "@n8n/n8n-nodes-langchain.memoryBufferWindow",
            1.4,
            {"sessionIdType": "customKey", "sessionKey": "={{ $json.sessionId || 'portfolio-demo' }}", "contextWindowLength": 8},
            1220,
            1040,
        )
        self.explain("Window memory", "Keeps the last eight turns for this session id. Use a per-user session id in production.")
        self.link("Window memory", agent, 0, "ai_memory")

        tools = self.spec.get("tools") or [
            {"name": "lookup_policy", "description": "Look up a policy snippet by topic.", "code": "const topic = String(query.topic || query || '').toLowerCase();\nconst book = { refund: 'Refunds within 14 days.', shipping: 'Standard shipping is 3 business days.', pricing: 'Starter 49, Growth 149, Scale 399.' };\nconst hit = Object.keys(book).find((key) => topic.includes(key));\nreturn { topic: hit || topic, answer: hit ? book[hit] : 'No policy on file.' };"}
        ]
        tool_x = 1460
        for tool in tools:
            if tool.get("kind") == "http":
                tname = tool["name"]
                self.add(
                    tname,
                    "@n8n/n8n-nodes-langchain.toolHttpRequest",
                    1.1,
                    {
                        "toolDescription": tool["description"],
                        "method": tool.get("method", "GET"),
                        "url": tool.get("url", "https://example.com/tool"),
                        "authentication": "none",
                    },
                    tool_x,
                    1040,
                )
                self.explain(tname, tool["description"] + " HTTP tool. Point the URL at your API before turning demo mode off.")
            elif tool.get("kind") == "sheets":
                tname = tool["name"]
                self.add(
                    tname,
                    "n8n-nodes-base.googleSheetsTool",
                    4.7,
                    {
                        "descriptionType": "manual",
                        "toolDescription": tool["description"],
                        "resource": "sheet",
                        "operation": "read",
                        "documentId": {"__rl": True, "mode": "id", "value": "YOUR_SPREADSHEET_ID"},
                        "sheetName": {"__rl": True, "mode": "name", "value": tool.get("sheet", "Data")},
                    },
                    tool_x,
                    1040,
                    credentials=_cred("googleSheetsOAuth2Api", "Google Sheets account"),
                )
                self.explain(tname, "Google Sheets tool the agent can read. Replace YOUR_SPREADSHEET_ID.")
            else:
                tname = tool["name"]
                self.add(
                    tname,
                    "@n8n/n8n-nodes-langchain.toolCode",
                    1.3,
                    {
                        "name": tname.replace(" ", "_").lower(),
                        "description": tool["description"],
                        "language": "javaScript",
                        "jsCode": tool["code"],
                    },
                    tool_x,
                    1040,
                )
                self.explain(tname, tool["description"] + " Implemented as a Code tool so the contract is visible in the canvas.")
            self.link(tname, agent, 0, "ai_tool")
            tool_x += 260

        after = self.spec.get("live") or []
        previous = agent
        x = 1560
        y = 780
        for action in after:
            name, node = _live_node(action, x, y)
            self.nodes.append(node)
            self.explain(name, _live_explanation(action))
            self.link(previous, name)
            previous = name
            x += 280

    def _build_rag(self) -> None:
        chain = "Answer from knowledge base"
        self.add(
            chain,
            "@n8n/n8n-nodes-langchain.chainRetrievalQa",
            1.7,
            {"promptType": "define", "text": "={{ $json.question || $json.prompt }}"},
            1220,
            780,
            notes="Live retrieval chain. Demo mode answers from the local keyword matcher in Apply rules.",
        )
        self.explain(chain, "Question-and-answer chain. It only runs when demo mode is off.")
        self.link("Demo mode?", chain, 1)

        self.add(
            "Groq chat model",
            "@n8n/n8n-nodes-langchain.lmChatGroq",
            1,
            {"model": "llama-3.3-70b-versatile", "options": {"temperature": 0.1}},
            980,
            980,
            credentials=_cred("groqApi", "Groq account"),
        )
        self.explain("Groq chat model", "Chat model for the retrieval chain. Gemini or Claude can replace this node.")
        self.link("Groq chat model", chain, 0, "ai_languageModel")

        self.add(
            "Vector store retriever",
            "@n8n/n8n-nodes-langchain.retrieverVectorStore",
            1,
            {"topK": 4},
            1220,
            1020,
        )
        self.explain("Vector store retriever", "Turns the in-memory vector store into the retriever the Q&A chain expects.")
        self.link("Vector store retriever", chain, 0, "ai_retriever")

        self.add(
            "Knowledge vector store",
            "@n8n/n8n-nodes-langchain.vectorStoreInMemory",
            1.3,
            {
                "mode": "retrieve",
                "memoryKey": {"__rl": True, "mode": "list", "value": "portfolio_kb"},
                "topK": 4,
            },
            980,
            1220,
        )
        self.explain("Knowledge vector store", "Simple Vector Store in retrieve mode. Swap it for Supabase or Pinecone when the corpus outgrows one process.")
        self.link("Knowledge vector store", "Vector store retriever", 0, "ai_vectorStore")

        self.add(
            "Insert into knowledge base",
            "@n8n/n8n-nodes-langchain.vectorStoreInMemory",
            1.3,
            {
                "mode": "insert",
                "memoryKey": {"__rl": True, "mode": "list", "value": "portfolio_kb"},
                "clearStore": False,
            },
            1540,
            1220,
        )
        self.explain("Insert into knowledge base", "Insert path for the same memory key. Feed it documents before asking questions in production.")

        self.add(
            "Embeddings",
            "@n8n/n8n-nodes-langchain.embeddingsGoogleGemini",
            1,
            {"modelName": "models/gemini-embedding-001"},
            760,
            1420,
            credentials=_cred("googlePalmApi", "Google Gemini account"),
        )
        self.explain("Embeddings", "Gemini embeddings shared by the retrieve and insert stores. Any other embeddings node can replace it.")
        self.link("Embeddings", "Knowledge vector store", 0, "ai_embedding")
        self.link("Embeddings", "Insert into knowledge base", 0, "ai_embedding")

        self.add(
            "Default data loader",
            "@n8n/n8n-nodes-langchain.documentDefaultDataLoader",
            1.1,
            {"dataType": "json", "jsonMode": "expressionData", "jsonData": "={{ $json.documents }}", "textSplittingMode": "custom"},
            1760,
            1420,
        )
        self.explain("Default data loader", "Loads the documents array on the item. Point jsonData at your crawled pages or help-center export.")
        self.link("Default data loader", "Insert into knowledge base", 0, "ai_document")

        self.add(
            "Text splitter",
            "@n8n/n8n-nodes-langchain.textSplitterRecursiveCharacterTextSplitter",
            1,
            {"chunkSize": 800, "chunkOverlap": 120},
            1760,
            1620,
        )
        self.explain("Text splitter", "Recursive splitter, 800 characters with 120 overlap. Raise chunk size for policy PDFs.")
        self.link("Text splitter", "Default data loader", 0, "ai_textSplitter")

        # A manual document seed that is NOT on the demo path: connected as the main input of the insert store.
        self.add(
            "Document seed",
            "n8n-nodes-base.code",
            2,
            {
                "mode": "runOnceForAllItems",
                "language": "javaScript",
                "jsCode": "const docs = $input.first().json.documents || [];\nreturn docs.map((doc) => ({ json: { documents: doc } }));",
            },
            1540,
            980,
            notes="Wire a schedule or a crawl into this node to refresh the store. It is not on the demo execution path.",
        )
        self.explain("Document seed", "Splits a documents array into items for the insert store. Not connected to the demo branch, so tests do not embed anything.")
        self.link("Document seed", "Insert into knowledge base")


def _normalize_js(sample: dict) -> str:
    encoded = json.dumps(sample, indent=2)
    return f"""const sample = {encoded};
const incoming = $input.first()?.json ?? {{}};
const provided = Object.keys(incoming).filter((key) => incoming[key] !== undefined && incoming[key] !== null && incoming[key] !== '');
const base = provided.length ? {{ ...sample, ...incoming }} : {{ ...sample }};
const flag = incoming.demo;
base.demo = !(flag === false || flag === 'false' || flag === 0 || flag === '0');
return [{{ json: base }}];
"""


def _logic_wrapper(body: str) -> str:
    return f"""const item = $input.first().json;
const produced = (() => {{
{body}
}})();
if (!produced || typeof produced.summary !== 'string' || !produced.summary.trim()) {{
  throw new Error('Apply rules must return a summary string');
}}
return [{{
  json: {{
    ...item,
    ...produced,
    demo: item.demo !== false,
  }},
}}];
"""


def _package_js(workflow_id: str) -> str:
    return f"""const item = $input.first().json;
return [{{
  json: {{
    demo: true,
    status: 'demo_ready',
    workflow: '{workflow_id}',
    summary: item.summary,
    route: item.route ?? null,
    record: item.record ?? {{}},
    actions: item.actions ?? [],
    slackText: item.slackText ?? item.summary,
    notes: 'Demo mode did not call external apps. Send {{"demo": false}} after placeholder credentials are replaced.',
  }},
}}];
"""


def _form_fields(sample: dict) -> list[dict[str, Any]]:
    fields = []
    for key, value in sample.items():
        if key == "demo" or isinstance(value, (dict, list)):
            continue
        field_type = "number" if isinstance(value, (int, float)) and not isinstance(value, bool) else "text"
        fields.append({"fieldLabel": key, "fieldType": field_type, "requiredField": False})
        if len(fields) == 6:
            break
    if not fields:
        fields.append({"fieldLabel": "payload", "fieldType": "textarea", "requiredField": True})
    return fields


def _rl(value: str, mode: str = "id") -> dict[str, Any]:
    return {"__rl": True, "mode": mode, "value": value}


def _live_node(action: str, x: int, y: int) -> tuple[str, dict[str, Any]]:
    kind, _, arg = action.partition(":")
    arg = arg or "Data"
    builders = {
        "sheets": _node_sheets,
        "slack": _node_slack,
        "hubspot": _node_hubspot,
        "ghl": _node_ghl,
        "pipedrive": _node_pipedrive,
        "twilio": _node_twilio,
        "gmail": _node_gmail,
        "notion": _node_notion,
        "clickup": _node_clickup,
        "shopify": _node_shopify,
        "woo": _node_woo,
        "zendesk": _node_zendesk,
        "freshdesk": _node_freshdesk,
        "stripe": _node_stripe,
        "xero": _node_xero,
        "qbo": _node_qbo,
        "telegram": _node_telegram,
        "whatsapp": _node_whatsapp,
        "discord": _node_discord,
        "airtable": _node_airtable,
        "salesforce": _node_salesforce,
        "sendgrid": _node_sendgrid,
        "mailchimp": _node_mailchimp,
        "linkedin": _node_linkedin,
        "x": _node_x,
        "gcal": _node_gcal,
        "jira": _node_jira,
        "wordpress": _node_wordpress,
        "http": _node_http,
    }
    if kind not in builders:
        raise KeyError(f"Unknown live action {action}")
    return builders[kind](arg, x, y)


def _base(name: str, node_type: str, version: float, parameters: dict, x: int, y: int, credentials: dict | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {
        "parameters": parameters,
        "id": _id(),
        "name": name,
        "type": node_type,
        "typeVersion": version,
        "position": [x, y],
    }
    if credentials:
        node["credentials"] = credentials
    return node


def _node_sheets(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = f"Append {arg}"
    columns = {
        "mappingMode": "autoMapInputData",
        "value": {},
        "matchingColumns": [],
        "schema": [],
    }
    node = _base(
        name,
        "n8n-nodes-base.googleSheets",
        4.7,
        {
            "authentication": "oAuth2",
            "resource": "sheet",
            "operation": "append",
            "documentId": _rl("YOUR_SPREADSHEET_ID"),
            "sheetName": _rl(arg, "name"),
            "columns": columns,
            "options": {},
        },
        x,
        y,
        _cred("googleSheetsOAuth2Api", "Google Sheets account"),
    )
    return name, node


def _node_slack(arg: str, x: int, y: int) -> tuple[str, dict]:
    channel = arg if arg.startswith("#") or arg.startswith("C") else f"#{arg}"
    name = f"Post {channel}"
    node = _base(
        name,
        "n8n-nodes-base.slack",
        2.3,
        {
            "authentication": "oAuth2",
            "resource": "message",
            "operation": "post",
            "select": "channel",
            "channelId": _rl(channel, "name"),
            "text": "={{ $json.slackText || $json.summary }}",
            "otherOptions": {},
        },
        x,
        y,
        _cred("slackOAuth2Api", "Slack account"),
    )
    return name, node


def _node_hubspot(arg: str, x: int, y: int) -> tuple[str, dict]:
    if arg == "deal":
        name = "Create HubSpot deal"
        params = {
            "authentication": "oAuth2",
            "resource": "deal",
            "operation": "create",
            "stage": "appointmentscheduled",
            "additionalFields": {
                "dealName": "={{ $json.record.dealName || $json.record.company || $json.summary }}",
                "amount": "={{ $json.record.amount || $json.record.budget || 0 }}",
            },
        }
    else:
        name = "Upsert HubSpot contact"
        params = {
            "authentication": "oAuth2",
            "resource": "contact",
            "operation": "upsert",
            "email": "={{ $json.record.email || $json.email }}",
            "additionalFields": {
                "firstName": "={{ $json.record.firstName || $json.firstName }}",
                "lastName": "={{ $json.record.lastName || $json.lastName }}",
                "companyName": "={{ $json.record.company || $json.company }}",
            },
        }
    return name, _base(name, "n8n-nodes-base.hubspot", 2.2, params, x, y, _cred("hubspotOAuth2Api", "HubSpot account"))


def _node_ghl(arg: str, x: int, y: int) -> tuple[str, dict]:
    if arg == "opportunity":
        name = "Create HighLevel opportunity"
        params = {
            "resource": "opportunity",
            "operation": "create",
            "contactId": "={{ $json.record.email || $json.email || 'lead@example.com' }}",
            "name": "={{ $json.record.dealName || $json.record.company || $json.summary }}",
            "status": "open",
        }
    else:
        name = "Create HighLevel contact"
        params = {
            "resource": "contact",
            "operation": "create",
            "additionalFields": {
                "email": "={{ $json.record.email || $json.email }}",
                "name": "={{ $json.record.firstName || $json.summary }}",
            },
        }
    return name, _base(name, "n8n-nodes-base.highLevel", 2, params, x, y, _cred("highLevelOAuth2Api", "HighLevel account"))


def _node_pipedrive(arg: str, x: int, y: int) -> tuple[str, dict]:
    resource = "person" if arg == "person" else "deal"
    name = f"Create Pipedrive {resource}"
    params = {
        "authentication": "apiToken",
        "resource": resource,
        "operation": "create",
        "title": "={{ $json.record.dealName || $json.record.company || $json.summary }}",
        "name": "={{ $json.record.fullName || $json.record.email || 'Lead' }}",
        "associateWith": "organization",
        "org_id": 0,
        "additionalFields": {},
    }
    return name, _base(name, "n8n-nodes-base.pipedrive", 2, params, x, y, _cred("pipedriveApi", "Pipedrive account"))


def _node_twilio(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Send SMS" if arg != "call" else "Place call"
    resource = "call" if arg == "call" else "sms"
    operation = "make" if arg == "call" else "send"
    params = {
        "resource": resource,
        "operation": operation,
        "from": "={{ $json.record.from || '+15555550100' }}",
        "to": "={{ $json.record.to || $json.record.phone || $json.phone }}",
        "message": "={{ $json.record.message || $json.slackText || $json.summary }}",
        "twiml": "={{ $json.record.twiml || '<Response><Say>We will call you back shortly.</Say></Response>' }}",
    }
    return name, _base(name, "n8n-nodes-base.twilio", 1, params, x, y, _cred("twilioApi", "Twilio account"))


def _node_gmail(arg: str, x: int, y: int) -> tuple[str, dict]:
    operation = {"send": "send", "draft": "create", "label": "addLabels", "get": "getAll"}.get(arg, "send")
    resource = "draft" if arg == "draft" else "message"
    if arg == "label":
        resource = "message"
    name = {"send": "Send Gmail", "draft": "Create Gmail draft", "label": "Label Gmail thread", "get": "List Gmail messages"}.get(arg, "Send Gmail")
    params = {
        "authentication": "oAuth2",
        "resource": resource,
        "operation": operation,
        "sendTo": "={{ $json.record.email || $json.email || 'lead@example.com' }}",
        "subject": "={{ $json.record.subject || $json.summary }}",
        "message": "={{ $json.record.body || $json.record.message || $json.summary }}",
        "emailType": "text",
        "messageId": "={{ $json.record.messageId || 'MESSAGE_ID' }}",
        "labelIds": ["Label_1"],
    }
    return name, _base(name, "n8n-nodes-base.gmail", 2.1, params, x, y, _cred("gmailOAuth2", "Gmail account"))


def _node_notion(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create Notion page"
    params = {
        "authentication": "apiKey",
        "resource": "page",
        "operation": "create",
        "pageId": _rl("https://www.notion.so/0123456789abcdef0123456789abcdef", "url"),
        "title": "={{ $json.record.title || $json.summary }}",
        "blockUi": {"blockValues": []},
    }
    return name, _base(name, "n8n-nodes-base.notion", 2.2, params, x, y, _cred("notionApi", "Notion account"))


def _node_clickup(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create ClickUp task"
    params = {
        "authentication": "oAuth2",
        "resource": "task",
        "operation": "create",
        "team": "YOUR_TEAM_ID",
        "space": "YOUR_SPACE_ID",
        "folderless": True,
        "list": "YOUR_LIST_ID",
        "name": "={{ $json.record.title || $json.summary }}",
        "additionalFields": {"content": "={{ $json.record.body || $json.summary }}"},
    }
    return name, _base(name, "n8n-nodes-base.clickUp", 1.1, params, x, y, _cred("clickUpOAuth2Api", "ClickUp account"))


def _node_shopify(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Update Shopify order"
    params = {"authentication": "accessToken", "resource": "order", "operation": "update", "orderId": "={{ $json.record.orderId || $json.orderId }}"}
    return name, _base(name, "n8n-nodes-base.shopify", 1, params, x, y, _cred("shopifyAccessTokenApi", "Shopify access token"))


def _node_woo(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Update WooCommerce order"
    params = {"resource": "order", "operation": "update", "orderId": "={{ $json.record.orderId || $json.orderId }}"}
    return name, _base(name, "n8n-nodes-base.wooCommerce", 1, params, x, y, _cred("wooCommerceApi", "WooCommerce account"))


def _node_zendesk(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create Zendesk ticket"
    params = {
        "authentication": "apiToken",
        "resource": "ticket",
        "operation": "create",
        "description": "={{ $json.record.body || $json.summary }}",
        "jsonParameters": False,
        "additionalFields": {"subject": "={{ $json.record.subject || $json.summary }}"},
    }
    return name, _base(name, "n8n-nodes-base.zendesk", 1, params, x, y, _cred("zendeskApi", "Zendesk account"))


def _node_freshdesk(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create Freshdesk ticket"
    params = {
        "resource": "ticket",
        "operation": "create",
        "requester": "email",
        "requesterIdentificationValue": "={{ $json.record.email || $json.email || 'lead@example.com' }}",
        "status": "pending",
        "priority": "low",
        "source": "portal",
        "subject": "={{ $json.record.subject || $json.summary }}",
        "description": "={{ $json.record.body || $json.summary }}",
    }
    return name, _base(name, "n8n-nodes-base.freshdesk", 1, params, x, y, _cred("freshdeskApi", "Freshdesk account"))


def _node_stripe(arg: str, x: int, y: int) -> tuple[str, dict]:
    resource = "charge" if arg in ("charge", "charges") else "customer"
    name = f"Get Stripe {resource}"
    params = {"resource": resource, "operation": "getAll", "returnAll": False, "limit": 20}
    return name, _base(name, "n8n-nodes-base.stripe", 1, params, x, y, _cred("stripeApi", "Stripe account"))


def _node_xero(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create Xero invoice"
    params = {
        "resource": "invoice",
        "operation": "create",
        "organizationId": "YOUR_XERO_ORGANIZATION_ID",
        "type": "ACCREC",
        "contactId": "YOUR_XERO_CONTACT_ID",
    }
    return name, _base(name, "n8n-nodes-base.xero", 1.1, params, x, y, _cred("xeroOAuth2Api", "Xero account"))


def _node_qbo(arg: str, x: int, y: int) -> tuple[str, dict]:
    resource = "bill" if arg == "bill" else "invoice"
    name = f"Create QuickBooks {resource}"
    params = {
        "resource": resource,
        "operation": "create",
        "VendorRef": "YOUR_QUICKBOOKS_VENDOR_ID",
        "CustomerRef": "YOUR_QUICKBOOKS_CUSTOMER_ID",
    }
    return name, _base(name, "n8n-nodes-base.quickbooks", 1, params, x, y, _cred("quickBooksOAuth2Api", "QuickBooks account"))


def _node_telegram(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Send Telegram message"
    params = {"resource": "message", "operation": "sendMessage", "chatId": "={{ $json.record.chatId || 'YOUR_CHAT_ID' }}", "text": "={{ $json.slackText || $json.summary }}"}
    return name, _base(name, "n8n-nodes-base.telegram", 1.2, params, x, y, _cred("telegramApi", "Telegram bot"))


def _node_whatsapp(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Send WhatsApp message"
    params = {
        "resource": "message",
        "operation": "send",
        "messageType": "text",
        "phoneNumberId": "YOUR_PHONE_NUMBER_ID",
        "recipientPhoneNumber": "={{ $json.record.phone || $json.phone || '+15555550100' }}",
        "textBody": "={{ $json.record.message || $json.slackText || $json.summary }}",
    }
    return name, _base(name, "n8n-nodes-base.whatsApp", 1.1, params, x, y, _cred("whatsAppApi", "WhatsApp account"))


def _node_discord(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Send Discord message"
    params = {
        "authentication": "botToken",
        "resource": "message",
        "operation": "send",
        "sendTo": "channel",
        "guildId": _rl("YOUR_DISCORD_GUILD_ID"),
        "channelId": _rl("YOUR_DISCORD_CHANNEL_ID"),
        "content": "={{ $json.slackText || $json.summary }}",
    }
    return name, _base(name, "n8n-nodes-base.discord", 2, params, x, y, _cred("discordBotApi", "Discord bot"))


def _node_airtable(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create Airtable record"
    params = {
        "authentication": "airtableTokenApi",
        "resource": "record",
        "operation": "create",
        "base": _rl("YOUR_BASE_ID"),
        "table": _rl(arg or "Leads", "name"),
        "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []},
    }
    return name, _base(name, "n8n-nodes-base.airtable", 2.1, params, x, y, _cred("airtableTokenApi", "Airtable account"))


def _node_salesforce(arg: str, x: int, y: int) -> tuple[str, dict]:
    resource = "opportunity" if arg == "opportunity" else "lead"
    name = f"Create Salesforce {resource}"
    params = {
        "authentication": "oAuth2",
        "resource": resource,
        "operation": "create",
        "company": "={{ $json.record.company || $json.company || 'Example Co' }}",
        "lastname": "={{ $json.record.lastName || $json.lastName || 'Lead' }}",
        "name": "={{ $json.record.dealName || $json.summary }}",
        "closeDate": "2026-12-31",
        "stageName": "Prospecting",
    }
    return name, _base(name, "n8n-nodes-base.salesforce", 1.1, params, x, y, _cred("salesforceOAuth2Api", "Salesforce account"))


def _node_sendgrid(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Send SendGrid mail"
    params = {
        "resource": "mail",
        "operation": "send",
        "dynamicTemplate": False,
        "contentValue": "={{ $json.record.body || $json.summary }}",
    }
    return name, _base(name, "n8n-nodes-base.sendGrid", 1, params, x, y, _cred("sendGridApi", "SendGrid account"))


def _node_mailchimp(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Upsert Mailchimp member"
    params = {
        "authentication": "apiKey",
        "resource": "member",
        "operation": "create",
        "list": "YOUR_AUDIENCE_ID",
        "email": "={{ $json.record.email || $json.email || 'lead@example.com' }}",
        "status": "subscribed",
    }
    return name, _base(name, "n8n-nodes-base.mailchimp", 1.1, params, x, y, _cred("mailchimpApi", "Mailchimp account"))


def _node_linkedin(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create LinkedIn post"
    params = {
        "authentication": "standard",
        "resource": "post",
        "operation": "create",
        "postAs": "person",
        "person": "YOUR_LINKEDIN_PERSON_URN",
        "text": "={{ $json.record.linkedin || $json.summary }}",
    }
    return name, _base(name, "n8n-nodes-base.linkedIn", 1, params, x, y, _cred("linkedInOAuth2Api", "LinkedIn account"))


def _node_x(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create X post"
    params = {"resource": "tweet", "operation": "create", "text": "={{ $json.record.x || $json.summary }}"}
    return name, _base(name, "n8n-nodes-base.twitter", 2, params, x, y, _cred("twitterOAuth2Api", "X account"))


def _node_gcal(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create calendar event"
    params = {
        "resource": "event",
        "operation": "create",
        "calendar": _rl("calendar@example.com", "id"),
        "start": "={{ $json.record.start }}",
        "end": "={{ $json.record.end }}",
        "additionalFields": {"summary": "={{ $json.record.title || $json.summary }}"},
    }
    return name, _base(name, "n8n-nodes-base.googleCalendar", 1.3, params, x, y, _cred("googleCalendarOAuth2Api", "Google Calendar account"))


def _node_jira(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create Jira issue"
    params = {
        "resource": "issue",
        "operation": "create",
        "project": _rl("YOUR_JIRA_PROJECT_ID", "id"),
        "issueType": _rl("YOUR_JIRA_ISSUE_TYPE_ID", "id"),
        "summary": "={{ $json.record.title || $json.summary }}",
        "additionalFields": {"description": "={{ $json.record.body || $json.summary }}"},
    }
    return name, _base(name, "n8n-nodes-base.jira", 1, params, x, y, _cred("jiraSoftwareCloudApi", "Jira account"))


def _node_wordpress(arg: str, x: int, y: int) -> tuple[str, dict]:
    name = "Create WordPress post"
    params = {"resource": "post", "operation": "create", "title": "={{ $json.record.title || $json.summary }}", "additionalFields": {"status": "draft", "content": "={{ $json.record.body || $json.summary }}"}}
    return name, _base(name, "n8n-nodes-base.wordpress", 1, params, x, y, _cred("wordpressApi", "WordPress account"))


def _node_http(arg: str, x: int, y: int) -> tuple[str, dict]:
    method, _, url = arg.partition(":")
    if not url:
        url, method = method, "POST"
    if not url.startswith("http"):
        url = "https://example.com/" + url.lstrip("/")
    name = f"HTTP {method or 'POST'}"
    params = {
        "method": method or "POST",
        "url": url,
        "authentication": "none",
        "sendBody": True,
        "contentType": "json",
        "specifyBody": "json",
        "jsonBody": "={{ $json.record }}",
        "options": {},
    }
    return name, _base(name, "n8n-nodes-base.httpRequest", 4.2, params, x, y, None)


def _live_explanation(action: str) -> str:
    kind, _, arg = action.partition(":")
    labels = {
        "sheets": f"Appends the record to the {arg} tab. Map columns explicitly once the sheet exists.",
        "slack": f"Posts slackText to {arg}.",
        "hubspot": f"Writes a HubSpot {arg or 'contact'} from the record.",
        "ghl": f"Creates a HighLevel {arg or 'contact'}.",
        "pipedrive": f"Creates a Pipedrive {arg or 'deal'}.",
        "twilio": "Sends the SMS (or places the call) using the phone and message on the record.",
        "gmail": f"Gmail {arg or 'send'} using the subject and body on the record.",
        "notion": "Creates a Notion page under the parent you configure.",
        "clickup": "Creates a ClickUp task in the list you configure.",
        "shopify": "Updates the Shopify order referenced by record.orderId.",
        "woo": "Updates the WooCommerce order referenced by record.orderId.",
        "zendesk": "Opens a Zendesk ticket with the subject, body, and priority on the record.",
        "freshdesk": "Opens a Freshdesk ticket with the same fields.",
        "stripe": "Reads recent Stripe objects so the rules engine can be replaced by a live pull.",
        "xero": "Creates a Xero invoice from the extracted bill.",
        "qbo": f"Creates a QuickBooks {arg or 'invoice'}.",
        "telegram": "Sends the summary to the configured Telegram chat.",
        "whatsapp": "Sends the message to the lead's WhatsApp number.",
        "discord": "Posts the summary to a Discord channel.",
        "airtable": "Creates an Airtable record in the table you name.",
        "salesforce": f"Creates a Salesforce {arg or 'lead'}.",
        "sendgrid": "Sends the transactional email through SendGrid.",
        "mailchimp": "Upserts the address onto a Mailchimp audience.",
        "linkedin": "Publishes the LinkedIn variant of the drafted copy.",
        "x": "Publishes the short X variant of the drafted copy.",
        "gcal": "Creates the calendar event from record.start and record.end.",
        "jira": "Opens a Jira issue with the title and body.",
        "wordpress": "Creates a WordPress draft.",
        "http": "Posts the record to an HTTP endpoint you control. Swap example.com for your API.",
    }
    return labels.get(kind, f"Live action `{action}`.")


def mermaid(spec: dict[str, Any], explained: list[tuple[str, str]]) -> str:
    lines = ["flowchart LR"]
    ids: dict[str, str] = {}

    def nid(name: str) -> str:
        if name not in ids:
            ids[name] = f"n{len(ids)}"
        return ids[name]

    for name, _ in explained:
        if name in ("Overview", "Live path"):
            continue
        safe = name.replace('"', "'")
        lines.append(f'  {nid(name)}["{safe}"]')
    # connections are not passed here; infer from explained order plus known forks
    names = [name for name, _ in explained if name not in ("Overview", "Live path")]
    # A simple left-to-right of the main spine is documented in the README prose.
    # Draw the spine we always create, then list live/agent nodes off the IF.
    spine = [n for n in ["Run demo", "Inbound webhook", "Normalize input", "Apply rules", "Demo mode?", "Package demo result"] if n in ids]
    if "Run demo" in ids and "Normalize input" in ids:
        lines.append(f"  {nid('Run demo')} --> {nid('Normalize input')}")
    if "Inbound webhook" in ids and "Normalize input" in ids:
        lines.append(f"  {nid('Inbound webhook')} --> {nid('Normalize input')}")
    for name in names:
        if name in ("Run demo", "Inbound webhook", "Normalize input", "Apply rules", "Demo mode?", "Package demo result"):
            continue
        # extra triggers
        if name in ("Weekday schedule", "Gmail trigger", "Web form", "Shopify order trigger", "WooCommerce order trigger", "Stripe trigger", "Twilio voice trigger", "Calendly trigger", "RSS feed", "Slack trigger"):
            lines.append(f"  {nid(name)} --> {nid('Normalize input')}")
    if "Normalize input" in ids and "Apply rules" in ids:
        lines.append(f"  {nid('Normalize input')} --> {nid('Apply rules')}")
    if "Apply rules" in ids and "Demo mode?" in ids:
        lines.append(f"  {nid('Apply rules')} --> {nid('Demo mode?')}")
    if "Demo mode?" in ids and "Package demo result" in ids:
        lines.append(f"  {nid('Demo mode?')} -->|demo| {nid('Package demo result')}")
    live_names = [n for n in names if n not in ("Run demo", "Inbound webhook", "Normalize input", "Apply rules", "Demo mode?", "Package demo result", "Weekday schedule", "Gmail trigger", "Web form", "Shopify order trigger", "WooCommerce order trigger", "Stripe trigger", "Twilio voice trigger", "Calendly trigger", "RSS feed", "Slack trigger")]
    previous = "Demo mode?"
    for name in live_names:
        if previous == "Demo mode?":
            lines.append(f"  {nid('Demo mode?')} -->|live| {nid(name)}")
        else:
            lines.append(f"  {nid(previous)} --> {nid(name)}")
        previous = name
    return "\n".join(lines)


def render_readme(spec: dict[str, Any], explained: list[tuple[str, str]]) -> str:
    creds = credential_rows(spec)
    apps = ", ".join(spec["apps"])
    node_lines = "\n".join(f"{index}. **{name}.** {text}" for index, (name, text) in enumerate(explained, start=1))
    setup = "\n".join(f"{index}. {step}" for index, step in enumerate(spec["setup"], start=1))
    tips = "\n".join(f"- {tip}" for tip in spec["tips"])
    cred_lines = "\n".join(f"- **{name}** (`{cred_type}`), placeholder id `{placeholder_id(cred_type)}`" for cred_type, name in creds)
    if not cred_lines:
        cred_lines = "- No third-party credential is required for the demo path. Live nodes in this workflow call only public HTTP."
    diagram = mermaid(spec, explained)
    sample = json.dumps(spec["sample"], indent=2)
    return f"""# {spec['title']}

> {DISCLAIMER}

| | |
| --- | --- |
| Category | `{spec['category']}` |
| Difficulty | {spec['difficulty']} |
| Apps | {apps} |
| Time saved | {spec['time_saved']} |
| Demo status | Run **Run demo** in n8n. The live apps stay on the false branch until you send `demo: false`. |

## Problem

{spec['problem']}

## Who it is for

{spec['audience']}

## What the workflow does

{spec['description']}

The checked-in sample is the contract. **Apply rules** turns that payload into a `summary`, a `route`, a `record` for the destination apps, and an `actions` list describing each write the live branch would make. **Package demo result** returns that object when `demo` is true, which is the default.

## Estimated time saved

{spec['time_saved']}. The figure assumes the sample's volume and a person who currently does the same triage by hand. It is a planning number for a portfolio review, not a measured client result.

## Node by node

{node_lines}

## Diagram

```mermaid
{diagram}
```

## Sample input

Save as the webhook body, or rely on the manual trigger, which loads the same object from **Normalize input**.

```json
{sample}
```

The file next to this README, `sample-input.json`, is the same payload.

## Setup

{setup}

## Credentials

{cred_lines}

Placeholder ids are not real credentials. n8n will show them as missing until you create a credential of that type and select it on the node. Do not paste production secrets into the workflow JSON.

## Customization

{tips}

## Demo mode and the live branch

- Execute **Run demo** or POST the sample to `/webhook/{spec['id']}` with `demo` omitted or true. The run stops after **Package demo result**.
- POST the same JSON with `"demo": false` only after every placeholder credential on the live branch has been replaced.
- The rules engine is intentionally local so the workflow can be reviewed and tested without buying model or SaaS credits. When you want a live model, put it on the live branch in front of the app nodes, or replace **Apply rules** with an Information Extractor / AI Agent and keep the same output shape.

## Portfolio note

Built as a portfolio demo for Mustafa ([mustafaautomation](https://github.com/mustafaautomation)). Public demos live under `*.quvantic.com`. Vendor names belong to their owners. Nothing in this folder is a customer deliverable.
"""


def credential_rows(spec: dict[str, Any]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    seen: set[str] = set()

    def push(cred_type: str, name: str) -> None:
        if cred_type in seen:
            return
        seen.add(cred_type)
        found.append((cred_type, name))

    for trigger in spec.get("triggers", []):
        kind = trigger.split(":", 1)[0]
        mapping = {
            "gmail": ("gmailOAuth2", "Gmail account"),
            "shopify": ("shopifyAccessTokenApi", "Shopify access token"),
            "woo": ("wooCommerceApi", "WooCommerce account"),
            "stripe": ("stripeApi", "Stripe account"),
            "twilio": ("twilioApi", "Twilio account"),
            "calendly": ("calendlyOAuth2Api", "Calendly account"),
            "slack": ("slackApi", "Slack bot"),
        }
        if kind in mapping:
            push(*mapping[kind])
    for action in spec.get("live", []):
        kind = action.split(":", 1)[0]
        mapping = {
            "sheets": ("googleSheetsOAuth2Api", "Google Sheets account"),
            "slack": ("slackOAuth2Api", "Slack account"),
            "hubspot": ("hubspotOAuth2Api", "HubSpot account"),
            "ghl": ("highLevelOAuth2Api", "HighLevel account"),
            "pipedrive": ("pipedriveApi", "Pipedrive account"),
            "twilio": ("twilioApi", "Twilio account"),
            "gmail": ("gmailOAuth2", "Gmail account"),
            "notion": ("notionApi", "Notion account"),
            "clickup": ("clickUpOAuth2Api", "ClickUp account"),
            "shopify": ("shopifyAccessTokenApi", "Shopify access token"),
            "woo": ("wooCommerceApi", "WooCommerce account"),
            "zendesk": ("zendeskApi", "Zendesk account"),
            "freshdesk": ("freshdeskApi", "Freshdesk account"),
            "stripe": ("stripeApi", "Stripe account"),
            "xero": ("xeroOAuth2Api", "Xero account"),
            "qbo": ("quickBooksOAuth2Api", "QuickBooks account"),
            "telegram": ("telegramApi", "Telegram bot"),
            "whatsapp": ("whatsAppApi", "WhatsApp account"),
            "discord": ("discordBotApi", "Discord bot"),
            "airtable": ("airtableTokenApi", "Airtable account"),
            "salesforce": ("salesforceOAuth2Api", "Salesforce account"),
            "sendgrid": ("sendGridApi", "SendGrid account"),
            "mailchimp": ("mailchimpApi", "Mailchimp account"),
            "linkedin": ("linkedInOAuth2Api", "LinkedIn account"),
            "x": ("twitterOAuth2Api", "X account"),
            "gcal": ("googleCalendarOAuth2Api", "Google Calendar account"),
            "jira": ("jiraSoftwareCloudApi", "Jira account"),
            "wordpress": ("wordpressApi", "WordPress account"),
        }
        if kind in mapping:
            push(*mapping[kind])
    if spec.get("pattern") == "agent":
        if spec.get("model") == "anthropic":
            push("anthropicApi", "Anthropic account")
        else:
            push("groqApi", "Groq account")
        for tool in spec.get("tools") or []:
            if tool.get("kind") == "sheets":
                push("googleSheetsOAuth2Api", "Google Sheets account")
    if spec.get("pattern") == "rag":
        push("groqApi", "Groq account")
        push("googlePalmApi", "Google Gemini account")
    return found


def placeholder_id(cred_type: str) -> str:
    token = "".join(ch if ch.isalnum() else "_" for ch in cred_type).upper()
    return f"PLACEHOLDER_{token}"


def apps_from_spec(spec: dict[str, Any]) -> list[str]:
    return list(spec["apps"])
