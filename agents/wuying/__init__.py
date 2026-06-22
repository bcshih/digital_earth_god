"""五營兵將 ADK agent — 凡人意圖萃取為 TaskBroadcast.

Required by `adk run wuying` (ADK discovers agents through package import).
"""

from . import agent as agent  # noqa: F401 — re-exported for `adk run wuying`
