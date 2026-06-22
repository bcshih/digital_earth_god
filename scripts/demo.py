"""數位土地公 Demo Script

展示探索推薦（Contract Net）與上香許願（Warm Data）兩條流程。

用法：
    # 先啟動 gateway（另開終端）
    uvicorn apps.api.gateway:app --port 8080

    # 執行 demo
    python scripts/demo.py
    python scripts/demo.py --flow explore        # 只跑探索推薦
    python scripts/demo.py --flow wish           # 只跑許願
    python scripts/demo.py --host 0.0.0.0 --port 9000

需求：gateway 已在執行，GOOGLE_API_KEY 已設定於 .env。
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=150) as resp:
        return json.loads(resp.read().decode())


def _post(url: str, data: dict) -> dict:
    body = json.dumps(data, ensure_ascii=False).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=150) as resp:
        return json.loads(resp.read().decode())


def _bar(n: int, max_n: int = 20, char: str = "█") -> str:
    filled = round(n / max(max_n, n) * max_n)
    return char * filled + "░" * (max_n - filled)


def _hr(title: str = "") -> None:
    line = "═" * 62
    if title:
        print(f"\n  ╔{line}╗")
        print(f"  ║  {title:<59}║")
        print(f"  ╚{line}╝")
    else:
        print(f"  {'─' * 62}")


def demo_health(base: str) -> bool:
    try:
        result = _get(f"{base}/health")
        ok = result.get("status") == "ok"
        status = "✅ 正常" if ok else f"⚠️  {result}"
        print(f"  健康檢查：{status}")
        return ok
    except Exception as exc:
        print(f"  ❌ 無法連線：{exc}")
        return False


def demo_explore(base: str) -> None:
    _hr("流程 A — 探索推薦（Contract Net）")
    intent = "找一間安靜的老宅咖啡，有自己的故事，最好不用排隊"
    print(f"\n  【意圖】{intent}\n")
    print("  五營兵將傳訊中，土地公正在主持投標會議……（約 30–90 秒）")

    try:
        result = _post(f"{base}/intent", {
            "intent_text": intent,
            "lat": 22.9965,
            "lng": 120.2004,
        })
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"  ❌ 錯誤 {exc.code}：{body[:200]}")
        return
    except Exception as exc:
        print(f"  ❌ {exc}")
        return

    tb = result["task_broadcast"]
    j = result["judgment"]

    print(f"\n  招標令 task_id : {tb['task_id'][:12]}…")
    print(f"  意圖萃取       : {tb['intent']}")
    if tb.get("constraints"):
        print(f"  限制條件       : {', '.join(tb['constraints'])}")

    _hr()
    print(f"\n  🏆  土地公裁決：{j['winner_street']}")
    print(f"\n  「{j['recommendation']}」")
    print(f"\n  裁決理由：{j['reasoning'][:120]}…")

    ranked = j.get("ranked_agent_ids", [])
    _LABELS = {
        "street_shennong_node": "神農街",
        "street_haian_node":    "海安路",
        "street_zhengxing_node":"正興街",
    }
    if ranked:
        print("\n  排名：" + " > ".join(_LABELS.get(a, a) for a in ranked))

    pois = j.get("recommended_pois", [])
    if pois:
        print("\n  推薦地點：")
        for p in pois[:3]:
            print(f"    📍  {p['name']}  ({p['category']})  — {p.get('note', '')}")


def demo_wish(base: str) -> None:
    _hr("流程 B — 上香許願（Warm Data）")
    wish = "希望海安路多裝幾盞路燈，夜晚走路才安心"
    print(f"\n  【心願】{wish}\n")
    print("  上香中……（約 15–40 秒）")

    try:
        result = _post(f"{base}/wish", {
            "wish_text": wish,
            "lat": 22.9979,
            "lng": 120.1985,
        })
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"  ❌ 錯誤 {exc.code}：{body[:200]}")
        return
    except Exception as exc:
        print(f"  ❌ {exc}")
        return

    an = result["analysis"]
    bl = result["blessing"]

    print(f"\n  五營兵將歸類  : {an['category']}")
    print(f"  標籤          : {', '.join(an.get('tags', []))}")
    print(f"  摘要          : {an.get('summary', '')[:80]}")

    _hr()
    print("\n  🙏  土地公祝福")
    print(f"\n  「{bl['acknowledgment']}」")
    print(f"\n  ✨  {bl['blessing']}")


def demo_dashboard(base: str) -> None:
    _hr("治理儀表板 — 城市風向球")
    try:
        result = _get(f"{base}/dashboard/summary")
    except Exception as exc:
        print(f"  ❌ {exc}")
        return

    total = result.get("total_wishes", 0)
    print(f"\n  願望總數：{total}")

    cats: dict[str, int] = result.get("category_counts", {})
    if cats:
        print("\n  分類統計：")
        for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"    {cat:12s}  {_bar(cnt, max_n=max(cats.values()))} {cnt}")

    recent = result.get("recent_wishes", [])
    if recent:
        print(f"\n  最近 {len(recent)} 則心願：")
        for w in recent[:5]:
            short = w.get("raw_text", "")[:50]
            cat = w.get("category", "?")
            print(f"    [{cat}]  {short}")


def main() -> None:
    parser = argparse.ArgumentParser(description="數位土地公 Demo Script")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument(
        "--flow",
        choices=["all", "explore", "wish", "dashboard"],
        default="all",
        help="要展示的流程（預設 all）",
    )
    args = parser.parse_args()
    base = f"http://{args.host}:{args.port}"

    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║   🏯  數位土地公 (Digital Earth God)  Demo 腳本              ║")
    print("  ║       台南中西區 MAS 微觀治理平台                              ║")
    print(f"  ║       連接至：{base:<47}║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print()

    if not demo_health(base):
        print()
        print("  請先啟動 gateway：")
        print("    uvicorn apps.api.gateway:app --port 8080")
        print()
        sys.exit(1)

    if args.flow in ("all", "explore"):
        demo_explore(base)
    if args.flow in ("all", "wish"):
        demo_wish(base)
    if args.flow in ("all", "dashboard"):
        demo_dashboard(base)

    print()
    _hr("Demo 完成")
    print()
    print("  前端介面：http://localhost:3000")
    print("  探索推薦：http://localhost:3000/")
    print("  上香許願：http://localhost:3000/wish")
    print("  治理儀表板：http://localhost:3000/dashboard")
    print()


if __name__ == "__main__":
    main()
