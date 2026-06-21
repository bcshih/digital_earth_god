"""地基主 A2A HTTP server (a2a-sdk v0.3).

Each 地基主 street node exposes an A2A JSON-RPC endpoint.
The server wraps the ADK LlmAgent via Runner and returns BiddingProposal as artifact.

Run a specific street server:
    python -m dijizhu.a2a_server shennong    # port 9001
    python -m dijizhu.a2a_server haian       # port 9002
    python -m dijizhu.a2a_server zhengxing   # port 9003
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Ensure repo root on sys.path when launched standalone.
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
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types as genai_types  # noqa: E402

from dijizhu.agent import create_dijizhu  # noqa: E402

# Street → (display name, agent_id, port)
STREET_CONFIGS: dict[str, tuple[str, str, int]] = {
    "shennong": ("神農街", "street_shennong_node", 9001),
    "haian": ("海安路", "street_haian_node", 9002),
    "zhengxing": ("正興街", "street_zhengxing_node", 9003),
}


def build_dijizhu_card(street_id: str, street_name: str, port: int) -> AgentCard:
    """Build the A2A AgentCard for a 地基主 server."""
    return AgentCard(
        name=f"dijizhu_{street_id}",
        description=f"台南{street_name}的地基主，專責該街廓的空間情報投標。接受 TaskBroadcast JSON，回傳 BiddingProposal JSON。",
        version="1.0.0",
        url=f"http://127.0.0.1:{port}/",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="bid",
                name="Contract Net Bidding",
                description="收到 TaskBroadcast 後調查轄區、計算 fitness_score，回傳 BiddingProposal",
                tags=["bidding", "spatial", "tainan", street_id],
                examples=['{"task_id":"t1","intent":"find_cafe","user_location":{"lat":22.999,"lng":120.222},"constraints":["咖啡"]}'],
            )
        ],
    )


class DijizhuA2aExecutor(AgentExecutor):
    """A2A executor that runs the 地基主 ADK LlmAgent and returns a BiddingProposal artifact."""

    def __init__(self, street_id: str, street_name: str, agent_id: str) -> None:
        self._agent = create_dijizhu(street_id, street_name, agent_id)
        self._session_service = InMemorySessionService()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        await updater.submit()
        await updater.start_work()

        user_input = context.get_user_input()
        session_id = context.context_id or str(uuid.uuid4())

        try:
            await self._session_service.create_session(
                app_name="deg", user_id="a2a_caller", session_id=session_id
            )
        except Exception:
            pass  # session may already exist for resumed tasks

        runner = Runner(
            agent=self._agent, app_name="deg", session_service=self._session_service
        )
        msg = genai_types.Content(
            role="user", parts=[genai_types.Part(text=user_input)]
        )

        final_text = ""
        async for event in runner.run_async(
            user_id="a2a_caller", session_id=session_id, new_message=msg
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text
                break

        await updater.add_artifact(
            parts=[Part(root=TextPart(text=final_text))],
            name="bidding_proposal",
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id or "",
            context_id=context.context_id or "",
        )
        await updater.cancel()


def build_dijizhu_app(
    street_id: str, street_name: str, agent_id: str, port: int
) -> starlette.applications.Starlette:
    """Build the Starlette A2A app for a specific 地基主 street."""
    card = build_dijizhu_card(street_id, street_name, port)
    executor = DijizhuA2aExecutor(street_id, street_name, agent_id)
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(agent_card=card, http_handler=handler).build()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a 地基主 A2A server")
    parser.add_argument(
        "street_id",
        choices=list(STREET_CONFIGS.keys()),
        help="Which street to serve",
    )
    args = parser.parse_args()
    street_name, agent_id, port = STREET_CONFIGS[args.street_id]
    app = build_dijizhu_app(args.street_id, street_name, agent_id, port)
    uvicorn.run(app, host="127.0.0.1", port=port)
