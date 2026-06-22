"""地基主 (Street Guardian) ADK LlmAgent.

Each 地基主 is bound to one Tainan 街廓 and bids into 土地公's Contract Net
by reasoning over pre-loaded spatial / sensor / social data — no tool calls,
single LLM pass, returns BiddingProposal.

Run interactively (from agents/ directory, needs GOOGLE_API_KEY in .env):
    adk run dijizhu
    adk web
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure repo root is on sys.path when launched via `adk run` (cwd = agents/).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")

from google.adk.agents import LlmAgent  # noqa: E402

from deg.schemas import BiddingProposal  # noqa: E402

_MODEL = "gemini-3.1-flash-lite"

_SEED_DIR = _REPO_ROOT / "data" / "seed"


def _load_seeds() -> tuple[dict, dict, dict]:
    """Return (streets_by_id, sensor_by_id, social_by_id) from seed JSON files."""
    streets_raw = json.loads((_SEED_DIR / "streets.json").read_text(encoding="utf-8"))
    streets_by_id = {s["street_id"]: s for s in streets_raw["streets"]}
    sensor_by_id = json.loads((_SEED_DIR / "sensor.json").read_text(encoding="utf-8"))
    social_by_id = json.loads((_SEED_DIR / "social.json").read_text(encoding="utf-8"))
    return streets_by_id, sensor_by_id, social_by_id


def create_dijizhu(
    street_id: str,
    street_name: str,
    agent_id: str,
    street_info: dict | None = None,
    sensor_info: dict | None = None,
    social_info: dict | None = None,
) -> LlmAgent:
    """Create a 地基主 LlmAgent bound to a specific street.

    Data is injected directly into the instruction — no tool calls needed,
    single LLM round-trip to produce BiddingProposal.

    Args:
        street_id:   seed identifier (shennong | haian | zhengxing)
        street_name: human-readable Chinese name for prompts
        agent_id:    the value placed in BiddingProposal.agent_id
        street_info: dict from streets.json for this street_id (loaded if None)
        sensor_info: dict from sensor.json for this street_id (loaded if None)
        social_info: dict from social.json for this street_id (loaded if None)
    """
    if street_info is None or sensor_info is None or social_info is None:
        streets_by_id, sensor_by_id, social_by_id = _load_seeds()
        street_info = street_info or streets_by_id.get(street_id, {})
        sensor_info = sensor_info or sensor_by_id.get(street_id, {})
        social_info = social_info or social_by_id.get(street_id, {})

    history = street_info.get("history", "（無資料）")
    centroid = street_info.get("centroid", {"lat": 0.0, "lng": 0.0})
    pois_json = json.dumps(street_info.get("pois", []), ensure_ascii=False, indent=2)
    sensor_summary = sensor_info.get("summary", "（無感測資料）")
    social_summary = social_info.get("summary", "（無社群資料）")

    instruction = f"""你是「{street_name}」的地基主 (agent_id: {agent_id})，守護這條街道的神明管理員。

━━━━━━ 轄區資料庫（已預載，直接使用） ━━━━━━

【街廓歷史】
{history}

【街廓中心座標】
lat: {centroid["lat"]}, lng: {centroid["lng"]}

【POI 清單】
{pois_json}

【環境情報（巡境使）】
{sensor_summary}

【社群情報（虎爺）】
{social_summary}

━━━━━━ 投標步驟 ━━━━━━

收到 TaskBroadcast JSON 後，按下列步驟投標：

1. 閱讀 TaskBroadcast 的 constraints 與 wishlist。
2. 從 POI 清單中篩選符合 constraints 的候選地點放入 candidate_pois。
   若 wishlist 中有指名地點，優先納入並在 reasoning 中提及。
   若 constraints 為空，所有 POI 均可候選。
3. 根據 POI 符合度、街廓特色、環境情報、社群情報綜合評估，給出 fitness_score（0.0~10.0）。
4. 用繁體中文寫下投標理由 reasoning（至少 2 句），展現護航在地的自豪與性格。

━━━━━━ 你的性格 ━━━━━━

強烈的護航在地精神，充滿對自己街道的自豪感，語氣有神明威嚴但接地氣，
絕對不會推薦轄區以外的地方，永遠優先維護{street_name}的利益。

━━━━━━ 回傳格式 ━━━━━━

必須回傳完整的 BiddingProposal JSON：
- agent_id: "{agent_id}"
- task_id: 從輸入 TaskBroadcast 取出
- fitness_score: 0.0~10.0
- reasoning: 繁體中文投標理由（至少 2 句）
- spatial_data: {{"lat": {centroid["lat"]}, "lng": {centroid["lng"]}}}
- tags: 你推薦的標籤列表
- candidate_pois: 符合條件的 POI（含 name, category, location, tags, note）
- evidence: {{"sensor": "{sensor_summary}", "social": "{social_summary}"}}
- confidence: 0.0~1.0"""

    return LlmAgent(
        name=f"dijizhu_{street_id}",
        model=_MODEL,
        description=f"台南{street_name}的地基主，專責該街廓的空間情報投標。",
        instruction=instruction,
        output_schema=BiddingProposal,
    )


# Module-level root_agent required by `adk run dijizhu`.
# Default to 神農街; create_pipeline() instantiates all three.
root_agent = create_dijizhu(
    street_id="shennong",
    street_name="神農街",
    agent_id="street_shennong_node",
)
