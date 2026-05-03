# Vercel Dashboard

Field-tested against vercel.com on 2026-05-03/04 using a logged-in Chrome session and the browser cookie auth pattern below.

## Auth — browser cookies, no separate token needed

```python
import json
cookies = cdp("Network.getCookies", urls=["https://vercel.com"])
parts = [c["name"] + "=" + c["value"] for c in cookies.get("cookies", [])]
headers = {"Cookie": "; ".join(parts), "Accept": "application/json"}
```

## URL patterns

```
/dashboard                                            → redirects to /<team-slug>
/<team-slug>                                          → projects overview
/<team-slug>/<project>/deployments                   → deployment list
/<team-slug>/~/deployments                           → all-team deployments
/<team-slug>/<project>/<short-uid>                   → deployment inspector
/<team-slug>/<project>/<short-uid>/logs              → runtime logs (requests, not build)
/<team-slug>/<project>/logs?deploymentIds=dpl_<uid>  → runtime logs scoped to one deploy
```

`page_info()["url"]` after navigating `/dashboard` gives you the real `/<team-slug>` URL.

## REST API

### List deployments

```python
resp = http_get(
    "https://vercel.com/api/v6/deployments?limit=100&teamId=<team-slug>",
    headers=headers
)
data = json.loads(resp)
deps = data["deployments"]          # list of deployment objects
next_ts = data["pagination"]["next"] # pass as &until=<ts> to paginate; None when done
```

State filter: append `&state=READY|ERROR|CANCELED|BUILDING|QUEUED|INITIALIZING`
Target filter: append `&target=production|preview|development`

**Deployment object keys:** `uid`, `name`, `projectId`, `url`, `created`, `source`, `state`, `readyState`, `readySubstate`, `type`, `creator`, `inspectorUrl`, `meta`, `target`, `aliasError`, `aliasAssigned`, `isRollbackCandidate`, `createdAt`, `buildingAt`, `ready`, `projectSettings`

`dep["inspectorUrl"]` gives the full inspector URL. `dep["uid"]` is the full `dpl_<...>` ID used in API calls; the short display ID in the URL path has no prefix.

### List projects

```python
data = json.loads(http_get(
    "https://vercel.com/api/v9/projects?teamId=<team-slug>&limit=50",
    headers=headers
))
# data["projects"][i]["latestDeployments"] → recent deploys per project
```

### Build log

```python
import re

resp = http_get(
    "https://vercel.com/api/v3/deployments/dpl_<uid>/events?builds=1&limit=2000&teamId=<team-slug>",
    headers=headers
)
# Response is a JSON array, one object per line, separated by ",\n"
lines = [l.strip().rstrip(",") for l in resp.strip().split("\n") if l.strip() not in ("[", "]", "")]
events = [json.loads(l) for l in lines]
# Strip ANSI escape codes from text field
clean = "\n".join(re.sub(r"\x1b\[[0-9;]*m", "", e["text"]) for e in events)
```

Event schema: `{created, date, deploymentId, id, text, type: "stdout"|"stderr", serial, info: {type: "build", name: "bld_<id>", entrypoint: "."}}`

## Scraping projects and deployment status

Fastest approach — `document.body.innerText` is reliable; the Projects section renders near the end:

```python
new_tab("https://vercel.com/dashboard")
wait_for_load()
text = js("document.body.innerText")
# Each project block in innerText:
#   <project-name>\n<project>.vercel.app\n<owner>/<repo>\n<commit msg>\n<date>\n on\n<branch>
```

For structured data — grab all project/deployment links (filter by team slug present in every Vercel URL):

```python
links = js("Array.from(document.querySelectorAll('a[href]')).filter(a=>a.href.includes('vercel.com/') && !a.href.includes('vercel.com/docs')).map(a=>a.href+'|'+a.innerText.trim().slice(0,80)).join('||')")
```

## Deployment inspector page structure

URL: `/<team-slug>/<project>/<short-uid>` — title: `<project> – Deployment Overview`

Tabs across the top: **Deployment** | Logs | Resources | Source | Open Graph

Accordion sections (all expand on click):
1. **Deployment Settings** — build machine, Node.js version, protection, etc. Shows "N Recommendations" badge when Vercel has upsell suggestions.
2. **Build Logs** — header shows `⚠️ N` (warning count) + duration + ✅/❌. Content is a **virtual list — only visible rows are in the DOM**. Use the API endpoint above to get the full log.
3. **Deployment Summary** — resource breakdown
4. **Deployment Checks** — external check integrations
5. **Assigning Custom Domains** — alias assignment status

Bottom cards: Runtime Logs | Observability | Speed Insights | BotID

## Runtime logs page structure

URL: `/<team-slug>/<project>/<short-uid>/logs` — title: `<project> – Deployment Runtime Logs – Vercel`

This is **request/response logs** (serverless function traffic), not build output. Left panel filters: Timeline, Console Level (Warning/Error/Fatal with counts), Resource, Environment, Route, Request Path, Status Code, Request Type, Host, Request Method, Cache, Branch, Workflow Run, Workflow Step.

## Gotchas

- **`/dashboard` always redirects** — canonical URL is `/<team-slug>`. Always check `page_info()["url"]` after navigation.
- **Build logs are in a virtual list** — `document.body.innerText` only contains what's currently scrolled into view. Use `/api/v3/deployments/<uid>/events` to get all lines.
- **Build log text has ANSI escape codes** — strip with `re.sub(r"\x1b\[[0-9;]*m", "", text)` before displaying.
- **Short UID vs full UID** — URL paths use the short form (`2tySoj6ce`); the API always takes the full `dpl_<...>` form. `dep["uid"]` from the list API is the full form; `dep["inspectorUrl"]` gives you the inspector URL with the short form already embedded.
- **Preview deployment URLs** follow `<project>-git-<branch-slug>-<team-slug>.vercel.app`. The branch slug is truncated with a hex suffix (e.g. `vercel/install-analytics` → `vercel-install-v-f236ab`).
- **Status filter shows 5/6 by default** — Canceled is excluded from the deployments list by default. The 6 states in order: Ready (green), Error (red), Building (orange), Queued, Initializing, Canceled. DOM marker: `aria-label="N of 6 statuses selected"` on the badge.
- **"Error: Forbidden" in the preview thumbnail** = the deployed app requires auth, not a deployment failure.
- **Project card `!` icon** = Speed Insights performance alert, not a build error.
- **Page title prefix is a status signal** — `🟢 Vercel` / `🟢 <project>` = all systems nominal.
- **Hobby plan**: Alerts (anomaly monitoring) requires Pro. Deployment Settings shows "N Recommendations" for plan-upsell config suggestions.
