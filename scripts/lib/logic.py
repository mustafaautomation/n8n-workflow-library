"""Deterministic rules engines embedded in each workflow's Apply rules node.

Each function returns a JavaScript function body that reads `item` and returns
an object with summary, route, record, actions, and slackText.
"""

from __future__ import annotations


def _js_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def lead_score(cfg: dict) -> str:
    free = cfg.get("free_domains", ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"])
    intent = cfg.get("intent_sources", ["demo", "pricing", "referral"])
    hot = cfg.get("hot", 75)
    warm = cfg.get("warm", 45)
    headcount = cfg.get("headcount_bonus", 50)
    budget_line = cfg.get("budget_line", 5000)
    destination = cfg.get("destination", "HubSpot")
    free_js = ", ".join(_js_string(d) for d in free)
    intent_js = ", ".join(_js_string(s) for s in intent)
    return f"""
const email = String(item.email || '').trim().toLowerCase();
const company = String(item.company || 'Unknown company').trim();
const source = String(item.source || 'unknown').trim().toLowerCase();
const employees = Number(item.employees || item.headcount || 0);
const budget = Number(item.budget || 0);
const title = String(item.title || '').toLowerCase();
const domain = email.includes('@') ? email.split('@')[1] : '';
const freeDomains = [{free_js}];
const intentSources = [{intent_js}];
let score = 15;
const reasons = [];
if (email && !freeDomains.includes(domain)) {{
  score += 15;
  reasons.push('work email');
}} else if (email) {{
  reasons.push('free inbox, keep it in nurture');
}}
if (employees >= {headcount}) {{
  score += 20;
  reasons.push('headcount at or above {headcount}');
}} else if (employees >= 10) {{
  score += 10;
  reasons.push('team of 10 or more');
}}
if (intentSources.includes(source)) {{
  score += 25;
  reasons.push('high-intent source: ' + source);
}}
if (budget >= {budget_line}) {{
  score += 15;
  reasons.push('budget at or above {budget_line}');
}}
if (/(founder|owner|vp|head|director|ceo|cto|cmo)/.test(title)) {{
  score += 10;
  reasons.push('buyer title');
}}
score = Math.max(0, Math.min(100, score));
let tier = score >= {hot} ? 'sql' : score >= {warm} ? 'mql' : 'nurture';
const known = Array.isArray(item.knownEmails) ? item.knownEmails.map((value) => String(value).toLowerCase()) : [];
if (email && known.includes(email)) tier = 'duplicate';
const record = {{
  email,
  firstName: item.firstName || '',
  lastName: item.lastName || '',
  company,
  title: item.title || '',
  source,
  employees,
  budget,
  score,
  tier,
  reasons: reasons.join('; '),
  dealName: company + ' — ' + tier.toUpperCase(),
  amount: budget,
  stage: tier === 'sql' ? 'appointmentscheduled' : 'qualifiedtobuy',
}};
return {{
  summary: tier === 'duplicate'
    ? email + ' is already on file. No new {destination} record is required.'
    : company + ' (' + email + ') scored ' + score + ' and landed in ' + tier + ' for {destination}.',
  route: tier,
  record,
  slackText: tier.toUpperCase() + ' lead ' + email + ' at ' + company + ' scored ' + score + '. ' + reasons[0],
  actions: [
    {{ app: '{destination}', operation: 'upsert', payload: record }},
  ],
}};
"""


def speed_to_lead(cfg: dict) -> str:
    minutes = cfg.get("minutes", 1)
    channel = cfg.get("channel", "sms")
    owner_pool = cfg.get("owners", ["Amina", "Leo", "Priya"])
    owners_js = ", ".join(_js_string(o) for o in owner_pool)
    return f"""
const received = Date.parse(item.receivedAt || new Date().toISOString());
const ageSeconds = Math.max(0, Math.round((Date.now() - received) / 1000));
const withinWindow = ageSeconds <= {minutes} * 60;
const owners = [{owners_js}];
const bucket = Math.abs(hash(String(item.email || item.phone || 'lead'))) % owners.length;
const owner = item.owner || owners[bucket];
const first = item.firstName || 'there';
const company = item.company || 'your team';
const message = withinWindow
  ? 'Hi ' + first + ', this is ' + owner + ' at Northwind. I just saw the ' + (item.source || 'request') + ' from ' + company + ' and can reply right now.'
  : 'Hi ' + first + ', this is ' + owner + '. Sorry we missed the first minute. I can still help ' + company + ' today.';
const record = {{
  to: item.phone || '',
  email: item.email || '',
  from: '+15555550100',
  owner,
  message,
  subject: 'Re: ' + (item.source || 'your request'),
  body: message,
  ageSeconds,
  withinWindow,
  channel: '{channel}',
}};
return {{
  summary: (withinWindow ? 'Inside' : 'Outside') + ' the {minutes}-minute window. ' + owner + ' owns the {channel} reply.',
  route: withinWindow ? 'instant' : 'late',
  record,
  slackText: owner + ' should answer ' + (item.email || item.phone) + ' (' + ageSeconds + 's old).',
  actions: [{{ app: '{channel}', operation: 'send', payload: record }}],
}};
function hash(value) {{
  let h = 0;
  for (let i = 0; i < value.length; i++) h = (h * 31 + value.charCodeAt(i)) >>> 0;
  return h;
}}
"""


def classify_labels(cfg: dict) -> str:
    labels = cfg["labels"]
    default = cfg.get("default", labels[0]["id"])
    field = cfg.get("field", "text")
    noun = cfg.get("noun", "item")
    arms = []
    for label in labels:
        words = ", ".join(_js_string(w) for w in label["words"])
        arms.append(
            f"if ([{words}].some((word) => haystack.includes(word))) {{\n"
            f"  hits.push({{ id: {_js_string(label['id'])}, label: {_js_string(label['label'])}, weight: {label.get('weight', 1)} }});\n"
            f"}}"
        )
    joined = "\n".join(arms)
    return f"""
const haystack = String(item.{field} || item.body || item.subject || item.summary || '').toLowerCase();
const hits = [];
{joined}
hits.sort((a, b) => b.weight - a.weight);
const winner = hits[0] || {{ id: {_js_string(default)}, label: {_js_string(default)}, weight: 0 }};
const draft = item.draft || ('Thanks for the note. We logged this as ' + winner.label + ' and will follow up shortly.');
const record = {{
  label: winner.id,
  labelName: winner.label,
  confidence: hits.length ? Math.min(0.95, 0.45 + hits.length * 0.15) : 0.3,
  subject: item.subject || winner.label,
  body: draft,
  email: item.from || item.email || '',
  priority: winner.id,
  title: (item.subject || winner.label),
}};
return {{
  summary: '{noun} classified as ' + winner.label + ' (' + record.confidence.toFixed(2) + ').',
  route: winner.id,
  record,
  slackText: winner.label + ': ' + (item.subject || haystack.slice(0, 80)),
  actions: [{{ app: 'mailbox', operation: 'label-and-draft', payload: record }}],
}};
"""


def extract_invoice(cfg: dict) -> str:
    currency = cfg.get("default_currency", "USD")
    tolerance = cfg.get("tax_tolerance", 0.02)
    destination = cfg.get("destination", "Google Sheets")
    return f"""
const text = String(item.text || item.body || '');
const vendor = item.vendor || (text.match(/vendor[:\\s]+([^\\n]+)/i) || [])[1] || 'Unknown vendor';
const invoiceNumber = item.invoiceNumber || (text.match(/inv(?:oice)?\\s*#?\\s*([A-Z0-9-]+)/i) || [])[1] || 'UNKNOWN';
const currency = item.currency || {_js_string(currency)};
const total = Number(item.total ?? matchAmount(text, 'total') ?? 0);
const tax = Number(item.tax ?? matchAmount(text, 'tax') ?? 0);
const subtotal = Number(item.subtotal ?? matchAmount(text, 'subtotal') ?? (total - tax));
const dueDate = item.dueDate || (text.match(/due[:\\s]+(\\d{{4}}-\\d{{2}}-\\d{{2}})/i) || [])[1] || '';
const expected = Math.round((subtotal + tax) * 100) / 100;
const balanced = Math.abs(expected - total) <= Math.max(0.5, total * {tolerance});
const record = {{
  vendor: String(vendor).trim(),
  invoiceNumber,
  currency,
  subtotal,
  tax,
  total,
  dueDate,
  balanced,
  mailbox: item.from || '',
  filename: item.filename || 'invoice.pdf',
  destination: {_js_string(destination)},
}};
return {{
  summary: record.vendor + ' ' + invoiceNumber + ' for ' + total + ' ' + currency + (balanced ? ' balances.' : ' does not balance.'),
  route: balanced ? 'post' : 'review',
  record,
  slackText: (balanced ? 'Post' : 'Review') + ' invoice ' + invoiceNumber + ' from ' + record.vendor + ' (' + total + ' ' + currency + ').',
  actions: [{{ app: {_js_string(destination)}, operation: balanced ? 'create' : 'flag', payload: record }}],
}};
function matchAmount(source, label) {{
  const pattern = new RegExp(label + '[:\\\\s]*\\\\$?([0-9,]+(?:\\\\.[0-9]{{2}})?)', 'i');
  const found = source.match(pattern);
  return found ? Number(found[1].replace(/,/g, '')) : null;
}}
"""


def order_route(cfg: dict) -> str:
    high = cfg.get("high_value", 250)
    store = cfg.get("store", "Shopify")
    return f"""
const total = Number(item.total || item.amount || 0);
const country = String(item.country || item.shippingCountry || 'US');
const financial = String(item.financialStatus || item.status || 'paid').toLowerCase();
const tags = [];
let route = 'fulfill';
if (financial === 'refunded' || financial === 'voided') route = 'refund';
else if (financial === 'pending' || financial === 'cod') route = 'verify-payment';
else if (total >= {high}) route = 'vip';
else if (['BR', 'IN', 'NG'].includes(country) && item.shippingMethod === 'express') route = 'fraud-review';
if (Number(item.itemCount || 1) >= 8) tags.push('bulk');
if (route === 'vip') tags.push('vip');
const record = {{
  orderId: item.orderId || item.id,
  store: {_js_string(store)},
  email: item.email || '',
  total,
  currency: item.currency || 'USD',
  country,
  financialStatus: financial,
  route,
  tags: tags.join(','),
  title: {_js_string(store)} + ' ' + (item.orderId || ''),
}};
return {{
  summary: {_js_string(store)} + ' order ' + record.orderId + ' routed to ' + route + ' (' + total + ' ' + record.currency + ').',
  route,
  record,
  slackText: route.toUpperCase() + ' ' + record.orderId + ' for ' + (item.email || 'guest') + ' — ' + total,
  actions: [{{ app: {_js_string(store)}, operation: route, payload: record }}],
}};
"""


def kpi_rollup(cfg: dict) -> str:
    metrics = cfg.get("metrics", ["mrr", "newLeads", "churned", "tickets"])
    keys = ", ".join(_js_string(m) for m in metrics)
    name = cfg.get("report", "Weekly KPI")
    return f"""
const rows = Array.isArray(item.rows) ? item.rows : [item];
const keys = [{keys}];
const totals = {{}};
for (const key of keys) totals[key] = 0;
for (const row of rows) {{
  for (const key of keys) totals[key] += Number(row[key] || 0);
}}
const previous = item.previous || {{}};
const deltas = {{}};
for (const key of keys) {{
  const before = Number(previous[key] || 0);
  deltas[key] = before === 0 ? null : Math.round(((totals[key] - before) / before) * 1000) / 10;
}}
const lines = keys.map((key) => key + ': ' + totals[key] + (deltas[key] === null ? '' : ' (' + (deltas[key] > 0 ? '+' : '') + deltas[key] + '%)'));
const record = {{ report: {_js_string(name)}, period: item.period || 'last-7-days', totals, deltas, narrative: lines.join('\\n') }};
return {{
  summary: {_js_string(name)} + ' for ' + record.period + '. ' + lines[0] + '.',
  route: 'send',
  record,
  slackText: {_js_string(name)} + '\\n' + lines.join('\\n'),
  actions: [{{ app: 'Slack', operation: 'post', payload: record }}],
}};
"""


def task_from_message(cfg: dict) -> str:
    dest = cfg.get("destination", "ClickUp")
    return f"""
const text = String(item.text || item.message || '').trim();
const owner = (text.match(/@([a-z0-9._-]+)/i) || [])[1] || item.owner || 'unassigned';
const due = (text.match(/due\\s+(\\d{{4}}-\\d{{2}}-\\d{{2}})/i) || [])[1] || item.due || '';
const urgent = /urgent|asap|today|blocker|sev-?1/i.test(text);
const title = text.split('\\n')[0].slice(0, 100) || 'Untitled task';
const record = {{
  title,
  body: text,
  owner,
  due,
  priority: urgent ? 'high' : 'normal',
  source: item.source || 'slack',
  channel: item.channel || '',
}};
return {{
  summary: 'Task for ' + owner + (due ? ' due ' + due : '') + ': ' + title,
  route: urgent ? 'urgent' : 'normal',
  record,
  slackText: 'Created a {dest} task for ' + owner + ': ' + title,
  actions: [{{ app: '{dest}', operation: 'create task', payload: record }}],
}};
"""


def scrape_record(cfg: dict) -> str:
    fields = cfg.get("fields", ["company", "email", "phone"])
    field_js = ", ".join(_js_string(f) for f in fields)
    return f"""
const html = String(item.html || '');
const wanted = [{field_js}];
const record = {{ url: item.url || '', fetchedAt: item.fetchedAt || new Date().toISOString() }};
for (const field of wanted) {{
  if (item[field]) record[field] = item[field];
}}
if (!record.email) {{
  const found = html.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{{2,}}/i);
  if (found) record.email = found[0].toLowerCase();
}}
if (!record.phone) {{
  const found = html.match(/\\+?[0-9][0-9()\\-\\s]{{8,}}/);
  if (found) record.phone = found[0].trim();
}}
if (!record.title) {{
  const found = html.match(/<title>([^<]+)<\\/title>/i);
  if (found) record.title = found[1].trim();
}}
const missing = wanted.filter((field) => !record[field]);
const route = missing.length === 0 ? 'complete' : missing.length < wanted.length ? 'partial' : 'empty';
return {{
  summary: (record.title || record.url || 'Page') + ' extracted with route ' + route + '.',
  route,
  record: {{ ...record, missing: missing.join(',') }},
  slackText: route.toUpperCase() + ' scrape ' + (record.url || ''),
  actions: [{{ app: 'Google Sheets', operation: 'append', payload: record }}],
}};
"""


def reconcile(cfg: dict) -> str:
    tolerance = cfg.get("tolerance", 0.5)
    left = cfg.get("left", "stripe")
    right = cfg.get("right", "bank")
    return f"""
const leftRows = item.{left} || item.left || [];
const rightRows = item.{right} || item.right || [];
const used = new Set();
const matched = [];
const onlyLeft = [];
for (const row of leftRows) {{
  const amount = Number(row.amount);
  const hit = rightRows.findIndex((other, index) => !used.has(index) && Math.abs(Number(other.amount) - amount) <= {tolerance} && String(other.currency || row.currency || 'USD') === String(row.currency || 'USD'));
  if (hit >= 0) {{
    used.add(hit);
    matched.push({{ id: row.id, amount, pair: rightRows[hit].id }});
  }} else {{
    onlyLeft.push(row);
  }}
}}
const onlyRight = rightRows.filter((_, index) => !used.has(index));
const record = {{
  matched: matched.length,
  unmatchedLeft: onlyLeft.length,
  unmatchedRight: onlyRight.length,
  onlyLeft,
  onlyRight,
  tolerance: {tolerance},
}};
const route = onlyLeft.length || onlyRight.length ? 'exceptions' : 'clean';
return {{
  summary: matched.length + ' pairs matched. ' + onlyLeft.length + ' {left} and ' + onlyRight.length + ' {right} rows still open.',
  route,
  record,
  slackText: route.toUpperCase() + ' reconciliation: ' + matched.length + ' matched, ' + (onlyLeft.length + onlyRight.length) + ' exceptions.',
  actions: [{{ app: 'Sheets', operation: 'write exceptions', payload: record }}],
}};
"""


def repurpose(cfg: dict) -> str:
    return f"""
const title = String(item.title || 'Untitled').trim();
const source = String(item.transcript || item.body || item.summary || '').replace(/\\s+/g, ' ').trim();
const sentence = source.split(/(?<=\\.)\\s/)[0] || source.slice(0, 180);
const linkedin = sentence.slice(0, 420) + (sentence.length > 420 ? '…' : '') + '\\n\\nFull piece: ' + (item.url || 'link in comments');
const x = (title + ' — ' + sentence).slice(0, 240);
const shorts = source.split(/(?<=\\.)\\s/).slice(0, 3).map((line, index) => (index + 1) + '. ' + line.trim());
const record = {{
  title,
  url: item.url || '',
  linkedin,
  x,
  carousel: shorts,
  status: 'draft',
}};
return {{
  summary: 'Drafted LinkedIn, X, and a 3-beat carousel from "' + title + '".',
  route: 'draft',
  record,
  slackText: 'Social drafts ready for "' + title + '".',
  actions: [
    {{ app: 'LinkedIn', operation: 'draft', payload: {{ text: linkedin }} }},
    {{ app: 'X', operation: 'draft', payload: {{ text: x }} }},
  ],
}};
"""


def candidate_score(cfg: dict) -> str:
    must = cfg.get("must", ["javascript", "sql"])
    nice = cfg.get("nice", ["n8n", "hubspot"])
    years = cfg.get("years", 3)
    must_js = ", ".join(_js_string(s) for s in must)
    nice_js = ", ".join(_js_string(s) for s in nice)
    return f"""
const text = String(item.resumeText || item.cv || '').toLowerCase();
const must = [{must_js}];
const nice = [{nice_js}];
const haveMust = must.filter((skill) => text.includes(skill));
const haveNice = nice.filter((skill) => text.includes(skill));
const experience = Number(item.years || (text.match(/(\\d+)\\s+\\+?\\s*years/) || [])[1] || 0);
let score = haveMust.length * 20 + haveNice.length * 8;
if (experience >= {years}) score += 15;
if (item.workAuth === false) score -= 25;
score = Math.max(0, Math.min(100, score));
const route = haveMust.length < Math.ceil(must.length / 2) ? 'reject' : score >= 70 ? 'screen' : 'hold';
const record = {{
  name: item.name || 'Candidate',
  email: item.email || '',
  role: item.role || 'Open role',
  score,
  route,
  haveMust: haveMust.join(', '),
  haveNice: haveNice.join(', '),
  experience,
  title: (item.name || 'Candidate') + ' — ' + (item.role || 'role'),
}};
return {{
  summary: record.name + ' scored ' + score + ' for ' + record.role + ' (' + route + ').',
  route,
  record,
  slackText: route.toUpperCase() + ' ' + record.name + ' (' + score + ') for ' + record.role,
  actions: [{{ app: 'ATS', operation: route, payload: record }}],
}};
"""


def reminder_plan(cfg: dict) -> str:
    offsets = cfg.get("offsets", ["24h", "2h"])
    offsets_js = ", ".join(_js_string(o) for o in offsets)
    return f"""
const start = Date.parse(item.start || item.startsAt || '');
const status = String(item.status || 'booked').toLowerCase();
const offsets = [{offsets_js}];
const hours = {{ '24h': 24, '2h': 2, '1h': 1, '15m': 0.25 }};
const reminders = offsets.map((offset) => ({{
  offset,
  sendAt: Number.isNaN(start) ? null : new Date(start - (hours[offset] || 1) * 3600 * 1000).toISOString(),
  channel: item.phone ? 'sms' : 'email',
}}));
let route = 'schedule';
if (status === 'canceled' || status === 'cancelled') route = 'reschedule';
else if (status === 'no-show') route = 'recover';
else if (Number.isNaN(start)) route = 'missing-time';
const record = {{
  email: item.email || '',
  phone: item.phone || '',
  to: item.phone || '',
  title: item.title || 'Appointment',
  start: item.start || item.startsAt || '',
  end: item.end || '',
  status,
  reminders,
  message: 'Reminder: ' + (item.title || 'your appointment') + ' at ' + (item.start || item.startsAt || 'the scheduled time') + '.',
}};
return {{
  summary: record.title + ' for ' + (record.email || record.phone || 'the guest') + ' is ' + route + '.',
  route,
  record,
  slackText: route.toUpperCase() + ' — ' + record.title + ' (' + (record.start || 'unscheduled') + ')',
  actions: reminders.map((reminder) => ({{ app: reminder.channel, operation: 'remind', payload: reminder }})),
}};
"""


def ticket_route(cfg: dict) -> str:
    return classify_labels({
        "field": cfg.get("field", "body"),
        "noun": cfg.get("noun", "Ticket"),
        "default": cfg.get("default", "general"),
        "labels": cfg["labels"],
    })


def local_answer(cfg: dict) -> str:
    book = cfg.get("book", {"pricing": "Starter is 49, Growth is 149, Scale is 399 USD per month."})
    pairs = ",\n".join(f"  {_js_string(k)}: {_js_string(v)}" for k, v in book.items())
    persona = cfg.get("persona", "operations assistant")
    return f"""
const book = {{
{pairs}
}};
const prompt = String(item.prompt || item.question || item.text || '').toLowerCase();
const keys = Object.keys(book);
const hit = keys.find((key) => prompt.includes(key)) || null;
const answer = hit ? book[hit] : 'I do not have a grounded answer for that in the demo knowledge set. Ask about: ' + keys.join(', ') + '.';
const record = {{ answer, topic: hit, persona: {_js_string(persona)}, sessionId: item.sessionId || 'portfolio-demo' }};
return {{
  summary: answer,
  route: hit ? 'answered' : 'fallback',
  prompt: item.prompt || item.question || item.text || '',
  record,
  slackText: (hit ? 'Answered' : 'Fallback') + ': ' + answer,
  actions: [{{ app: 'agent', operation: 'reply', payload: record }}],
}};
"""


def rag_answer(cfg: dict) -> str:
    return local_answer({
        "persona": cfg.get("persona", "support librarian"),
        "book": cfg.get("book", {}),
    })


def dunning(cfg: dict) -> str:
    steps = cfg.get("steps", [0, 3, 7])
    steps_js = ", ".join(str(s) for s in steps)
    return f"""
const failedAt = Date.parse(item.failedAt || item.created || new Date().toISOString());
const days = Math.floor((Date.now() - failedAt) / 86400000);
const steps = [{steps_js}];
const step = steps.filter((value) => days >= value).pop();
const attempt = steps.indexOf(step) + 1;
const amount = Number(item.amount || 0);
const record = {{
  customer: item.customer || item.email,
  email: item.email || '',
  amount,
  currency: item.currency || 'USD',
  days,
  attempt,
  subject: 'Payment attempt ' + attempt + ' for ' + amount + ' ' + (item.currency || 'USD'),
  body: 'The latest charge failed ' + days + ' days ago. Update the card to keep the workspace active.',
}};
const route = attempt >= steps.length ? 'final' : 'retry';
return {{
  summary: 'Dunning step ' + attempt + ' for ' + record.customer + ' (' + amount + ' ' + record.currency + ', ' + days + ' days).',
  route,
  record,
  slackText: route.toUpperCase() + ' dunning for ' + record.customer,
  actions: [{{ app: 'email', operation: 'send', payload: record }}],
}};
"""


def inventory(cfg: dict) -> str:
    floor = cfg.get("floor", 5)
    return f"""
const sku = item.sku || 'SKU';
const onHand = Number(item.onHand || 0);
const inbound = Number(item.inbound || 0);
const velocity = Number(item.dailyVelocity || 1);
const coverDays = velocity === 0 ? 999 : Math.round(((onHand + inbound) / velocity) * 10) / 10;
let route = 'ok';
if (onHand <= 0) route = 'stockout';
else if (onHand <= {floor}) route = 'reorder';
else if (coverDays < 7) route = 'watch';
const record = {{ sku, onHand, inbound, velocity, coverDays, reorderQty: Math.max({floor} * 4 - onHand, 0), title: 'Stock ' + sku }};
return {{
  summary: sku + ' has ' + onHand + ' on hand (' + coverDays + ' days of cover) — ' + route + '.',
  route,
  record,
  slackText: route.toUpperCase() + ' ' + sku + ' cover ' + coverDays + ' days',
  actions: [{{ app: 'Sheets', operation: 'append', payload: record }}],
}};
"""


def attribution(cfg: dict) -> str:
    return f"""
const touch = String(item.utmSource || item.source || 'direct');
const medium = String(item.utmMedium || 'unknown');
const campaign = String(item.utmCampaign || '(none)');
const value = Number(item.value || item.budget || 0);
let weight = 1;
if (medium === 'cpc') weight = 1.2;
if (medium === 'email') weight = 0.8;
if (touch === 'direct' && item.priorSource) weight = 0.5;
const credited = Math.round(value * weight);
const record = {{
  email: item.email || '',
  company: item.company || '',
  touch, medium, campaign, value, weight, credited,
  model: {_js_string(cfg.get('model', 'last-touch'))},
}};
return {{
  summary: record.model + ' credits ' + credited + ' to ' + campaign + ' (' + touch + '/' + medium + ').',
  route: medium === 'cpc' ? 'paid' : 'organic',
  record,
  slackText: campaign + ' credited ' + credited + ' via ' + touch,
  actions: [{{ app: 'CRM', operation: 'stamp attribution', payload: record }}],
}};
"""


def expense_policy(cfg: dict) -> str:
    meal = cfg.get("meal_cap", 75)
    ride = cfg.get("ride_cap", 120)
    return f"""
const category = String(item.category || 'other').toLowerCase();
const amount = Number(item.amount || 0);
const caps = {{ meal: {meal}, rideshare: {ride}, lodging: 350, software: 200, other: 150 }};
const cap = caps[category] ?? caps.other;
const receipt = Boolean(item.receipt || item.filename);
let route = 'approve';
const reasons = [];
if (amount > cap) {{ route = 'exception'; reasons.push('over the ' + cap + ' ' + category + ' cap'); }}
if (!receipt && amount >= 25) {{ route = 'needs-receipt'; reasons.push('missing receipt'); }}
if (item.merchant && /casino|gift card/i.test(item.merchant)) {{ route = 'reject'; reasons.push('merchant is out of policy'); }}
const record = {{
  employee: item.employee || item.email || '',
  merchant: item.merchant || '',
  category, amount, currency: item.currency || 'USD', cap, receipt, route,
  reasons: reasons.join('; ') || 'within policy',
  title: (item.merchant || category) + ' ' + amount,
}};
return {{
  summary: record.title + ' is ' + route + '. ' + record.reasons + '.',
  route,
  record,
  slackText: route.toUpperCase() + ' expense ' + record.title,
  actions: [{{ app: 'Sheets', operation: 'append', payload: record }}],
}};
"""


def content_queue(cfg: dict) -> str:
    return repurpose(cfg)


GENERATORS = {
    "lead_score": lead_score,
    "speed_to_lead": speed_to_lead,
    "classify_labels": classify_labels,
    "extract_invoice": extract_invoice,
    "order_route": order_route,
    "kpi_rollup": kpi_rollup,
    "task_from_message": task_from_message,
    "scrape_record": scrape_record,
    "reconcile": reconcile,
    "repurpose": repurpose,
    "candidate_score": candidate_score,
    "reminder_plan": reminder_plan,
    "ticket_route": ticket_route,
    "local_answer": local_answer,
    "rag_answer": rag_answer,
    "dunning": dunning,
    "inventory": inventory,
    "attribution": attribution,
    "expense_policy": expense_policy,
    "content_queue": content_queue,
}
