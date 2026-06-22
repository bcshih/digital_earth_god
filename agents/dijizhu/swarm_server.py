"""集中式地基主 A2A Swarm Server.

Loads all NGSI-LD agents and exposes them via a single FastAPI server with dynamic routing.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_REPO_ROOT / ".env")

import uvicorn  # noqa: E402
import starlette.applications  # noqa: E402
from starlette.routing import Mount  # noqa: E402
from a2a.server.request_handlers import DefaultRequestHandler  # noqa: E402
from a2a.server.tasks import InMemoryTaskStore  # noqa: E402
from a2a.server.apps import A2AStarletteApplication  # noqa: E402

from deg.seed.loader import load_agents  # noqa: E402
from dijizhu.a2a_server import build_dijizhu_card, DijizhuA2aExecutor  # noqa: E402
from dijizhu.agent import create_dijizhu  # noqa: E402

def build_swarm_app(port: int = 9000) -> starlette.applications.Starlette:
    """Build a single Starlette app that routes to 20 different A2A endpoints."""
    routes = []
    agents = load_agents()
    
    for li_data in agents:
        street = li_data.to_street()
        card = build_dijizhu_card(street.street_id, street.name, port)
        # Update URL to include the mount path
        card.url = f"http://127.0.0.1:{port}/{street.street_id}/"
        
        executor = DijizhuA2aExecutor(street.street_id, street.name, street.agent_id)
        # We need to inject the specific agent loaded from NGSI-LD
        executor._agent = create_dijizhu(street.street_id, street.name, street.agent_id, li_data=li_data)
        
        handler = DefaultRequestHandler(
            agent_executor=executor,
            task_store=InMemoryTaskStore(),
        )
        app = A2AStarletteApplication(agent_card=card, http_handler=handler).build()
        routes.append(Mount(f"/{street.street_id}", app=app))
        
    return starlette.applications.Starlette(routes=routes)


if __name__ == "__main__":
    app = build_swarm_app(port=9000)
    uvicorn.run(app, host="127.0.0.1", port=9000)
