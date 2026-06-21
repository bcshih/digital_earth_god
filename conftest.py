"""Pytest configuration for 數位土地公.

Adds agents/ to sys.path so `from dijizhu.agent import ...` works the same
way as `adk run dijizhu` (which runs from agents/ directory).
Loads .env so GOOGLE_API_KEY is available to integration tests.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent
_AGENTS = _ROOT / "agents"

# agents/ on sys.path → `import dijizhu.agent` (consistent with adk run)
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

load_dotenv(_ROOT / ".env")
