"""巡境使 A2A server (a2a-sdk v0.3, mock sensor data, no LLM).

Returns real-time environment summary (crowd/weather) for a requested street.

Run:
    python -m xunjingshi.a2a_server    # port 9011
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")

import starlette.applications  # noqa: E402
import uvicorn  # noqa: E402
from a2a.server.agent_execution import AgentExecutor, RequestContext  # noqa: E402
from a2a.server.apps import A2AStarletteApplication  # noqa: E402
from a2a.server.events import EventQueue  # noqa: E402
from a2a.server.request_handlers import DefaultRequestHandler  # noqa: E402
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater  # noqa: E402
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Part, TextPart  # noqa: E402

from deg.adapters.sensor_adapter import get_sensor_summary  # noqa: E402

_PORT = 9011
_HOST = "127.0.0.1"


def build_xunjingshi_card() -> AgentCard:
    return AgentCard(
        name="xunjingshi",
        description="巡境使：台南中西區即時環境斥候，回報人流、天氣、交通狀況摘要。",
        version="1.0.0",
        url=f"http://{_HOST}:{_PORT}/",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="env_sensor",
                name="Environment Sensor",
                description="輸入 street_id，回傳該街廓的即時環境摘要（人流/天氣）",
                tags=["sensor", "environment", "tainan"],
                examples=["shennong", "haian", "zhengxing"],
            )
        ],
    )


class XunjingshiExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        await updater.submit()
        await updater.start_work()
        street_id = context.get_user_input().strip()
        summary = get_sensor_summary(street_id)
        await updater.add_artifact(
            parts=[Part(root=TextPart(text=summary))],
            name="sensor_summary",
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id or "",
            context_id=context.context_id or "",
        )
        await updater.cancel()


def build_xunjingshi_app() -> starlette.applications.Starlette:
    card = build_xunjingshi_card()
    handler = DefaultRequestHandler(
        agent_executor=XunjingshiExecutor(),
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(agent_card=card, http_handler=handler).build()


if __name__ == "__main__":
    app = build_xunjingshi_app()
    uvicorn.run(app, host=_HOST, port=_PORT)
