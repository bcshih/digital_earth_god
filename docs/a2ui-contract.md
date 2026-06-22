# 數位土地公 — A2UI Streaming Contract

This document is the durable, self-contained specification of the A2UI message stream
emitted by the 數位土地公 gateway. A third-party frontend can implement a fully working
renderer from this document alone.

## Transport

- **Endpoint:** WebSocket `GET /ws/explore/a2ui`
- **Encoding:** JSONL — exactly one JSON object per WebSocket text frame.
- **A2UI version:** `v0.9.1` (every server→client message carries `"version": "v0.9.1"`).
- **Catalog:** A2UI *basic* catalog
  (`https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json`).
- **Surface id:** `explore` (the only surface).

A2UI components form a **flat adjacency list**: every component is a top-level object
with a unique string `id`; parents reference children **by id string** (never by nested
object). A `updateComponents` fragment has exactly one *unreferenced root* container.

## Message Sequence

```
server → createSurface(explore, sendDataModel=true)
server → updateComponents(intent input)                # the 五營兵將 prompt surface
server → updateDataModel(/intent, {"text": ""})
        ── client sends {intent_text, lat, lng} ──      # the ONLY client→server message
server → updateComponents(negotiation skeleton)        # broadcast card + bids List + verdict placeholder
server → updateDataModel(/broadcast, {...})
server → updateDataModel(/bids, [])
server → updateDataModel(/bids/0, {...bid...})          # one per 地基主 (data append; no component msg)
server → updateDataModel(/bids/1, {...bid...})
server → updateDataModel(/bids/2, {...bid...})
server → updateComponents(verdict)                     # redefines verdict-card subtree in place
server → updateDataModel(/verdict, {...})
server → {"a2uiDone": true}
```

On error the server sends `{"a2uiError": "<message>"}` and closes. The client should
treat either `a2uiDone` or `a2uiError` as the terminal frame.

### Why bids are data, not components

The negotiation skeleton defines `bids-row` as a `List` bound to `/bids` with a
**template** `bid-card`. Each incoming bid is therefore a pure data-model append
(`updateDataModel /bids/<i>`) — no further `updateComponents` is sent for bids. This
keeps every `updateComponents` fragment self-contained (no cross-message id references).

The verdict starts as a placeholder inside the skeleton and is filled in place by a
later `updateComponents` that redefines only the `verdict-card` subtree; the root still
references `verdict-card`, so the broadcast card and bid list remain visible beneath it.

## Client → Server

After receiving the intent surface, the client sends exactly one JSON message:

```json
{ "intent_text": "找一間安靜的老宅咖啡", "lat": 22.999, "lng": 120.222 }
```

The A2UI intent surface's `submit_intent` event context carries the typed intent text
(bound from `/intent/text`); the client supplies `lat`/`lng` from device geolocation.

## Data-Model Paths

| Path           | Shape |
|----------------|-------|
| `/intent`      | `{ "text": string }` |
| `/broadcast`   | `{ "task_id": string, "intent": string, "constraints": object, "lat": number, "lng": number }` |
| `/bids`        | array; initialized to `[]`, then appended at `/bids/<i>` |
| `/bids/<i>`    | `{ "agent_id": string, "street": string, "fitness_score": number, "reasoning": string, "tags": string[], "sensor": object\|null, "social": object\|null, "candidate_pois": Poi[] }` |
| `/verdict`     | `{ "winner_agent_id": string, "winner_street": string, "recommendation": string, "reasoning": string, "ranked_agent_ids": string[], "recommended_pois": Poi[] }` |

`Poi` = `{ "name": string, "category": string, "lat": number, "lng": number, "tags": string[], "note": string\|null }`.

### Bids List template binding

`bids-row` is a `List` whose `children` is a template:
`{ "path": "/bids", "componentId": "bid-card" }`. Bindings **inside** the template are
**relative to the array item** — e.g. `{"path": "street"}` resolves to `/bids/<i>/street`.

## Concrete Message Examples

### createSurface
```json
{"version":"v0.9.1","createSurface":{"surfaceId":"explore","catalogId":"https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json","sendDataModel":true}}
```

### updateComponents — intent input surface
```json
{"version":"v0.9.1","updateComponents":{"surfaceId":"explore","components":[
  {"id":"root","component":"Column","children":["intent-title","intent-sub","intent-field","intent-submit"]},
  {"id":"intent-title","component":"Text","text":"向土地公稟報你的心願","variant":"h1"},
  {"id":"intent-sub","component":"Text","text":"五營兵將會將你的凡人語言轉成招標令","variant":"caption"},
  {"id":"intent-field","component":"TextField","label":"你想找什麼？（例如：安靜的老宅咖啡）","value":{"path":"/intent/text"},"textFieldType":"text"},
  {"id":"intent-submit-label","component":"Text","text":"上香稟報"},
  {"id":"intent-submit","component":"Button","child":"intent-submit-label","variant":"primary",
   "checks":[{"condition":{"call":"required","args":{"value":{"path":"/intent/text"}}},"message":"請先說出你的心願"}],
   "action":{"event":{"name":"submit_intent","context":{"text":{"path":"/intent/text"}}}}}
]}}
```

### updateDataModel — /intent
```json
{"version":"v0.9.1","updateDataModel":{"surfaceId":"explore","path":"/intent","value":{"text":""}}}
```

### updateComponents — negotiation skeleton
```json
{"version":"v0.9.1","updateComponents":{"surfaceId":"explore","components":[
  {"id":"root","component":"Column","children":["broadcast-card","bids-row","verdict-card"]},
  {"id":"broadcast-card","component":"Card","child":"broadcast-body"},
  {"id":"broadcast-body","component":"Column","children":["broadcast-title","broadcast-intent"]},
  {"id":"broadcast-title","component":"Text","text":"土地公發出招標令","variant":"h2"},
  {"id":"broadcast-intent","component":"Text","text":{"path":"/broadcast/intent"}},
  {"id":"bids-row","component":"List","children":{"path":"/bids","componentId":"bid-card"}},
  {"id":"bid-card","component":"Card","child":"bid-card-body"},
  {"id":"bid-card-body","component":"Column","children":["bid-card-street","bid-card-score","bid-card-reason"]},
  {"id":"bid-card-street","component":"Text","text":{"path":"street"},"variant":"h2"},
  {"id":"bid-card-score","component":"Text","text":{"path":"fitness_score"}},
  {"id":"bid-card-reason","component":"Text","text":{"path":"reasoning"}},
  {"id":"verdict-card","component":"Card","child":"verdict-wait"},
  {"id":"verdict-wait","component":"Text","text":"等待土地公擲筊裁決…","variant":"caption"}
]}}
```

### updateDataModel — /broadcast
```json
{"version":"v0.9.1","updateDataModel":{"surfaceId":"explore","path":"/broadcast","value":{
  "task_id":"a1b2c3","intent":"安靜的老宅咖啡","constraints":{"noise":"low"},"lat":22.999,"lng":120.222}}}
```

### updateDataModel — /bids init
```json
{"version":"v0.9.1","updateDataModel":{"surfaceId":"explore","path":"/bids","value":[]}}
```

### updateDataModel — one bid appended at /bids/0
```json
{"version":"v0.9.1","updateDataModel":{"surfaceId":"explore","path":"/bids/0","value":{
  "agent_id":"street_shennong_node","street":"神農街","fitness_score":0.87,
  "reasoning":"老屋密度高、人潮安靜","tags":["老宅","咖啡"],
  "sensor":{"noise_db":52},"social":{"mentions":120},
  "candidate_pois":[{"name":"某咖啡","category":"cafe","lat":22.998,"lng":120.198,"tags":["老宅"],"note":null}]}}}
```

### updateComponents — verdict (redefines verdict-card subtree in place)
```json
{"version":"v0.9.1","updateComponents":{"surfaceId":"explore","components":[
  {"id":"verdict-card","component":"Card","child":"verdict-body"},
  {"id":"verdict-body","component":"Column","children":["verdict-title","verdict-street","verdict-text"]},
  {"id":"verdict-title","component":"Text","text":"土地公的裁決","variant":"h1"},
  {"id":"verdict-street","component":"Text","text":{"path":"/verdict/winner_street"},"variant":"h2"},
  {"id":"verdict-text","component":"Text","text":{"path":"/verdict/recommendation"}}
]}}
```

### updateDataModel — /verdict
```json
{"version":"v0.9.1","updateDataModel":{"surfaceId":"explore","path":"/verdict","value":{
  "winner_agent_id":"street_shennong_node","winner_street":"神農街",
  "recommendation":"推薦神農街的某咖啡","reasoning":"最符合安靜老宅條件",
  "ranked_agent_ids":["street_shennong_node","street_zhengxing_node","street_haian_node"],
  "recommended_pois":[{"name":"某咖啡","category":"cafe","lat":22.998,"lng":120.198,"tags":["老宅"],"note":null}]}}}
```

### terminal
```json
{"a2uiDone": true}
```
