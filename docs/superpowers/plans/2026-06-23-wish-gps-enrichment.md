# Wish GPS Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓許願流程真正使用 GPS 座標——前端提供地圖選點器（可拖動）、後端查詢附近地基主並將其本地資料注入五營兵將的分析 prompt，使許願分析具備真實的地理脈絡。

**Architecture:** 新增 `deg/seed/geo.py` 提供 Haversine 距離計算與最近地基主查詢；`gateway.py` 在呼叫許願分類器前先查出最近 3 個里並序列化 layer_2/layer_4 資料注入 payload；前端以 Leaflet 地圖取代純 GPS 自動定位，允許使用者拖動 marker 修改位置。

**Tech Stack:** Python Pydantic + math.radians (no new deps), Leaflet + next/dynamic (already in project), FastAPI WebSocket.

---

## Files

| 狀態 | 路徑 | 負責 |
|------|------|------|
| 新建 | `deg/seed/geo.py` | Haversine 距離 + 最近地基主查詢 |
| 修改 | `agents/wuying/wish_agent.py` | instruction 加入 `nearby_li` 欄位說明 |
| 修改 | `apps/api/gateway.py` | `_process_wish` 注入附近里資料 |
| 新建 | `apps/web/components/WishLocationPickerInner.tsx` | Leaflet 地圖 + 可拖動 marker |
| 新建 | `apps/web/components/WishLocationPicker.tsx` | `next/dynamic ssr:false` 包裝器 |
| 修改 | `apps/web/app/wish/page.tsx` | 顯示選點器、用選中座標提交 |
| 新建 | `tests/test_geo.py` | Haversine / centroid / nearest_li 單元測試 |

---

## Task 1 — `deg/seed/geo.py`：地理工具

**Files:**
- Create: `deg/seed/geo.py`
- Test: `tests/test_geo.py`

- [ ] **Step 1.1：寫失敗的測試**

```python
# tests/test_geo.py
import math
import pytest

from deg.seed.geo import haversine_m, li_centroid, nearest_li
from deg.seed.loader import load_agents, LiAgentData, GeoJsonPolygon


def _make_li(lng: float, lat: float, name: str = "TestLi") -> LiAgentData:
    from deg.seed.loader import Metadata, GeoProperty
    poly = GeoJsonPolygon(
        type="Polygon",
        coordinates=[[[lng, lat], [lng + 0.001, lat], [lng + 0.001, lat + 0.001], [lng, lat + 0.001], [lng, lat]]],
    )
    return LiAgentData(
        id=f"urn:test:{name}",
        type="EarthGodAgent",
        metadata=Metadata(agent_name=name),
        spatial_boundary=GeoProperty(type="GeoProperty", value=poly),
    )


def test_haversine_same_point():
    assert haversine_m(22.999, 120.196, 22.999, 120.196) == pytest.approx(0.0, abs=1e-6)


def test_haversine_known_distance():
    # 1 degree latitude ≈ 111,195 m
    d = haversine_m(0.0, 0.0, 1.0, 0.0)
    assert 111_000 < d < 112_000


def test_li_centroid_simple_square():
    li = _make_li(120.196, 22.999)
    lat_c, lng_c = li_centroid(li)
    assert lat_c == pytest.approx(22.9995, abs=1e-4)
    assert lng_c == pytest.approx(120.1965, abs=1e-4)


def test_nearest_li_returns_n_closest():
    agents = [
        _make_li(120.196, 22.999, "Near"),
        _make_li(120.300, 23.100, "Far"),
        _make_li(120.197, 23.000, "Medium"),
    ]
    result = nearest_li(lat=22.999, lng=120.196, n=2, agents=agents)
    assert len(result) == 2
    first_li, first_dist = result[0]
    assert first_li.metadata.agent_name == "Near"
    assert first_dist < 200  # meters


def test_nearest_li_with_no_boundary_skips():
    li_no_boundary = LiAgentData(
        id="urn:test:NoBoundary",
        type="EarthGodAgent",
        metadata=__import__("deg.seed.loader", fromlist=["Metadata"]).Metadata(agent_name="NoBoundary"),
    )
    agents = [li_no_boundary, _make_li(120.196, 22.999, "HasBoundary")]
    result = nearest_li(lat=22.999, lng=120.196, n=3, agents=agents)
    names = [li.metadata.agent_name for li, _ in result]
    assert "NoBoundary" not in names
    assert "HasBoundary" in names
```

- [ ] **Step 1.2：跑測試確認失敗**

```bash
python -m pytest tests/test_geo.py -v
```

Expected: `ImportError: cannot import name 'haversine_m' from 'deg.seed.geo'`

- [ ] **Step 1.3：實作 `deg/seed/geo.py`**

```python
"""Geographic utilities: Haversine distance and nearest-li lookup."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deg.seed.loader import LiAgentData


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return great-circle distance in metres between two WGS-84 points."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def li_centroid(li: "LiAgentData") -> tuple[float, float] | None:
    """Return (lat, lng) centroid of a li's spatial_boundary polygon, or None."""
    if not li.spatial_boundary:
        return None
    val = li.spatial_boundary.value
    if not val or val.type != "Polygon" or not val.coordinates:
        return None
    ring = val.coordinates[0]
    if not ring:
        return None
    avg_lng = sum(p[0] for p in ring) / len(ring)
    avg_lat = sum(p[1] for p in ring) / len(ring)
    return avg_lat, avg_lng


def nearest_li(
    lat: float,
    lng: float,
    n: int = 3,
    agents: "list[LiAgentData] | None" = None,
) -> list[tuple["LiAgentData", float]]:
    """Return the n nearest LiAgentData objects and their distance in metres.

    Agents without a valid spatial_boundary are silently skipped.
    If agents is None, loads from the default dijizu_agent/ directory.
    """
    if agents is None:
        from deg.seed.loader import load_agents
        agents = load_agents()

    scored: list[tuple[LiAgentData, float]] = []
    for li in agents:
        c = li_centroid(li)
        if c is None:
            continue
        dist = haversine_m(lat, lng, c[0], c[1])
        scored.append((li, dist))

    scored.sort(key=lambda x: x[1])
    return scored[:n]
```

- [ ] **Step 1.4：跑測試確認全過**

```bash
python -m pytest tests/test_geo.py -v
```

Expected: 5 passed

- [ ] **Step 1.5：Commit**

```bash
git add deg/seed/geo.py tests/test_geo.py
git commit -m "feat: add geographic utilities for nearest-li lookup (Haversine)"
```

---

## Task 2 — `wish_agent.py`：instruction 加入地理脈絡

**Files:**
- Modify: `agents/wuying/wish_agent.py`

- [ ] **Step 2.1：更新 `_WISH_INSTRUCTION`（不改 output_schema）**

把現有 instruction 中的「【輸入】」區塊改為下列版本（其餘不動）：

```python
_WISH_INSTRUCTION = f"""你是五營兵將，土地公麾下體察民情的基層兵將。
收到凡人的「許願」（對社區的期望、抱怨或建議）後，將它歸納為治理情報。

【輸入】JSON 欄位：
- raw_text：願望原文
- lat、lng：許願者的地理座標
- nearby_li：最近 3 個里的在地資訊陣列，每筆包含：
    - street_name：里名
    - distance_m：與許願者的距離（公尺）
    - activities：當前活動摘要（來自 layer_2）
    - opinions：居民輿情摘要（來自 layer_4）

【分析步驟】
1. category：從以下選一個最貼切的分類：{_CATEGORIES}。
2. tags：抽取 2~4 個關鍵字標籤（可含里名或在地地名）。
3. summary：用一句繁體中文中性地重述這個願望，**優先結合距離最近的里的在地脈絡**（例如：提到附近的活動、設施或民情）。
4. sentiment：判斷情緒，從 正面 / 中性 / 負面 / 急迫 擇一。

【回傳】完整的 WishAnalysis JSON：category、tags、summary、sentiment。"""
```

- [ ] **Step 2.2：手動確認 instruction 可正常序列化（不需整合測試）**

```bash
python -c "from wuying.wish_agent import create_wish_categorizer; a = create_wish_categorizer(); print('OK:', a.name)"
```

Expected: `OK: wuying_wish`

- [ ] **Step 2.3：Commit**

```bash
git add agents/wuying/wish_agent.py
git commit -m "feat: update wish_agent instruction to consume nearby_li geographic context"
```

---

## Task 3 — `gateway.py`：注入附近里資料

**Files:**
- Modify: `apps/api/gateway.py`

- [ ] **Step 3.1：在 gateway import 區塊加入 `nearest_li`**

在已有的 `from deg.seed.loader import ...` 行附近加入：

```python
from deg.seed.geo import nearest_li  # noqa: E402
```

- [ ] **Step 3.2：新增 `_nearby_li_payload` 輔助函式**

在 `_process_wish` 定義之前加入：

```python
def _nearby_li_payload(lat: float, lng: float, n: int = 3) -> list[dict]:
    """Return serialisable nearby-li context for the wish categoriser."""
    results = nearest_li(lat=lat, lng=lng, n=n)
    out = []
    for li, dist_m in results:
        activities_raw = li.layer_2_dynamic_activities
        opinions_raw = li.layer_4_citizen_opinions
        out.append({
            "street_name": li.metadata.agent_name,
            "distance_m": round(dist_m),
            "activities": activities_raw.get("value", []) if isinstance(activities_raw, dict) else [],
            "opinions": opinions_raw.get("value", {}) if isinstance(opinions_raw, dict) else {},
        })
    return out
```

- [ ] **Step 3.3：在 `_process_wish` 中注入 `nearby_li`**

找到現有這行：
```python
payload = json.dumps({"raw_text": wish_text, "lat": lat, "lng": lng}, ensure_ascii=False)
```

改為：
```python
nearby = _nearby_li_payload(lat, lng)
payload = json.dumps(
    {"raw_text": wish_text, "lat": lat, "lng": lng, "nearby_li": nearby},
    ensure_ascii=False,
)
```

- [ ] **Step 3.4：確認 gateway 仍可啟動**

```bash
python -c "from apps.api.gateway import create_app; app = create_app(); print('routes:', [r.path for r in app.routes])"
```

Expected: routes list 包含 `/ws/wish/a2ui`，無 ImportError

- [ ] **Step 3.5：Commit**

```bash
git add apps/api/gateway.py
git commit -m "feat: inject nearest-li geographic context into wish categoriser payload"
```

---

## Task 4 — 前端：`WishLocationPicker` Leaflet 元件

**Files:**
- Create: `apps/web/components/WishLocationPickerInner.tsx`
- Create: `apps/web/components/WishLocationPicker.tsx`

- [ ] **Step 4.1：建立 `WishLocationPickerInner.tsx`**

```tsx
// apps/web/components/WishLocationPickerInner.tsx
"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix Leaflet default icon paths broken by bundlers.
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const TAINAN_CENTER: [number, number] = [22.9971, 120.201];

export default function WishLocationPickerInner({
  lat,
  lng,
  onChange,
}: {
  lat: number;
  lng: number;
  onChange: (lat: number, lng: number) => void;
}) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  useEffect(() => {
    if (!elRef.current || mapRef.current) return;

    const map = L.map(elRef.current, {
      center: [lat, lng],
      zoom: 15,
      scrollWheelZoom: false,
    });
    mapRef.current = map;

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 20,
    }).addTo(map);

    const marker = L.marker([lat, lng], { draggable: true }).addTo(map);
    markerRef.current = marker;

    marker.on("dragend", () => {
      const pos = marker.getLatLng();
      onChange(pos.lat, pos.lng);
    });

    map.on("click", (e: L.LeafletMouseEvent) => {
      marker.setLatLng(e.latlng);
      onChange(e.latlng.lat, e.latlng.lng);
    });

    const t = setTimeout(() => map.invalidateSize(), 200);
    return () => {
      clearTimeout(t);
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync marker when parent pushes a new initial position (e.g. after GPS resolves).
  useEffect(() => {
    if (markerRef.current) {
      markerRef.current.setLatLng([lat, lng]);
      mapRef.current?.panTo([lat, lng]);
    }
  }, [lat, lng]);

  return (
    <div
      ref={elRef}
      style={{ width: "100%", height: "220px" }}
      role="region"
      aria-label="選擇許願地點"
    />
  );
}
```

- [ ] **Step 4.2：建立 SSR-safe 包裝器 `WishLocationPicker.tsx`**

```tsx
// apps/web/components/WishLocationPicker.tsx
"use client";

import dynamic from "next/dynamic";

const Inner = dynamic(() => import("./WishLocationPickerInner"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        width: "100%",
        height: "220px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "12px",
        color: "var(--color-dim, #888)",
        border: "1px dashed currentColor",
      }}
    >
      展開地圖中…
    </div>
  ),
});

export function WishLocationPicker({
  lat,
  lng,
  onChange,
}: {
  lat: number;
  lng: number;
  onChange: (lat: number, lng: number) => void;
}) {
  return <Inner lat={lat} lng={lng} onChange={onChange} />;
}

export default WishLocationPicker;
```

- [ ] **Step 4.3：確認 TypeScript 編譯無誤**

```bash
cd apps/web && npx tsc --noEmit
```

Expected: 無錯誤輸出

- [ ] **Step 4.4：Commit**

```bash
git add apps/web/components/WishLocationPickerInner.tsx apps/web/components/WishLocationPicker.tsx
git commit -m "feat: add WishLocationPicker Leaflet map component with draggable marker"
```

---

## Task 5 — `wish/page.tsx`：整合地圖選點器

**Files:**
- Modify: `apps/web/app/wish/page.tsx`

- [ ] **Step 5.1：在 `WishLive` 加入位置狀態與地圖**

在 `WishLive` 頂端加入 `import { WishLocationPicker }` 與位置 state：

```tsx
// 在現有 import 群組中加入（"use client" 區塊之後）
import { WishLocationPicker } from "@/components/WishLocationPicker";
```

在 `WishLive` 函式內，`wsRef` 等 ref 宣告的正下方加入：

```tsx
const [pickerLat, setPickerLat] = useState(DEFAULT_LAT);
const [pickerLng, setPickerLng] = useState(DEFAULT_LNG);
const locationReady = useRef(false);
```

在現有的 WebSocket `useEffect` **之後**加入 GPS 初始化 effect：

```tsx
useEffect(() => {
  if (locationReady.current) return;
  getLatLng().then(({ lat, lng }) => {
    locationReady.current = true;
    setPickerLat(lat);
    setPickerLng(lng);
  });
}, []);
```

- [ ] **Step 5.2：`onEvent` 改用 picker 座標**

找到現有的 `onEvent`：

```tsx
const onEvent = useCallback(async (name: string, context: EventContext) => {
  if (name !== "submit_wish") return;
  const fromCtx = typeof context.text === "string" ? context.text : null;
  const fromModel = getAtPointer(stateRef.current.dataModel, "/wish/text");
  const wishText = (fromCtx ?? (typeof fromModel === "string" ? fromModel : "")) || "";
  if (!wishText.trim()) return;

  const { lat, lng } = await getLatLng();         // ← 舊：提交時才抓 GPS
  const ws = wsRef.current;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ wish_text: wishText, lat, lng }));
    setConn("submitted");
  }
}, []);
```

改為（拿掉 `async`，改用 picker state；`pickerLat/Lng` 要放進 deps）：

```tsx
const pickerLatRef = useRef(DEFAULT_LAT);
const pickerLngRef = useRef(DEFAULT_LNG);
```

在 `setPickerLat` / `setPickerLng` 呼叫旁同步更新這兩個 ref（放在 GPS effect 和 `onChange` callback 裡）。

```tsx
const onEvent = useCallback((name: string, context: EventContext) => {
  if (name !== "submit_wish") return;
  const fromCtx = typeof context.text === "string" ? context.text : null;
  const fromModel = getAtPointer(stateRef.current.dataModel, "/wish/text");
  const wishText = (fromCtx ?? (typeof fromModel === "string" ? fromModel : "")) || "";
  if (!wishText.trim()) return;

  const ws = wsRef.current;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      wish_text: wishText,
      lat: pickerLatRef.current,
      lng: pickerLngRef.current,
    }));
    setConn("submitted");
  }
}, []);
```

- [ ] **Step 5.3：在渲染區插入地圖元件**

在 `WishShell` 的 `{children}` 之前、`Renderer` 之外，找到 `{!offline && ...}` 條件渲染的上方，加入選點器。

找到渲染部分的 `<Renderer .../>` 所在的 JSX 區塊（在 `offline` 分支的 else 內），改為：

```tsx
<>
  {conn === "open" && (
    <div style={{ marginBottom: "1rem" }}>
      <p
        className="a2-text a2-text--caption"
        style={{ marginBottom: "0.4rem" }}
      >
        許願地點（可拖動圖釘或點擊地圖調整）
      </p>
      <WishLocationPicker
        lat={pickerLat}
        lng={pickerLng}
        onChange={(lat, lng) => {
          setPickerLat(lat);
          setPickerLng(lng);
          pickerLatRef.current = lat;
          pickerLngRef.current = lng;
        }}
      />
    </div>
  )}
  <Renderer
    state={state}
    onEvent={onEvent}
    onDataModelChange={onDataModelChange}
    decorate={decorate}
  />
</>
```

- [ ] **Step 5.4：TypeScript 編譯確認**

```bash
cd apps/web && npx tsc --noEmit
```

Expected: 無錯誤

- [ ] **Step 5.5：Production build 確認**

```bash
cd apps/web && npm run build
```

Expected: `✓ Compiled successfully`，`/wish` 仍列為靜態路由

- [ ] **Step 5.6：Commit**

```bash
git add apps/web/app/wish/page.tsx
git commit -m "feat: add location picker map to wish page; use pin coordinates on submit"
```

---

## 驗收測試（手動）

在全部 task 完成後執行：

```bash
# Terminal 1
uvicorn apps.api.gateway:app --host 127.0.0.1 --port 8080 --reload

# Terminal 2
cd apps/web && npm run dev
```

1. 開啟 `http://localhost:3000/wish`
2. 確認：地圖在許願表單上方出現，marker 在台南中西區預設位置
3. 拖動 marker 到不同位置，確認 marker 可移動
4. 輸入心願文字送出，觀察 gateway log：應有 `nearby_li` 出現在 wish categoriser 的輸出（`analysis.summary` 應帶有在地地名或里名）
5. 點擊地圖空白處，marker 應跳至點擊位置

---

## 自我審查

**Spec coverage check:**
- [x] GPS 地圖選點（Task 4, 5）
- [x] 預設使用者位置（Task 5 Step 5.1 — GPS effect on mount）
- [x] 五營兵將蒐集 GPS（Task 3 injects into payload）
- [x] 將資料庫轉成真實地理資訊（Task 3 `_nearby_li_payload` loads layer_2/layer_4）
- [x] 地基主 centroid 計算（Task 1 `li_centroid`）

**Type consistency:**
- `haversine_m(lat1, lng1, lat2, lng2)` — consistent across test + impl
- `nearest_li(lat, lng, n, agents)` — consistent across test + gateway
- `_nearby_li_payload` returns `list[dict]` — matches `nearby_li` key in payload JSON
- `pickerLatRef.current` / `pickerLngRef.current` — synced in both GPS effect and onChange

**Placeholder scan:** 無 TBD / TODO / placeholder
