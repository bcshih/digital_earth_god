# 數位土地公 (Digital Earth God)

MAS 微觀治理系統 — 在地 Agent 動態協商（Contract Net）+ 神學科技 A2UI + Warm Data。
詳見 `docs/superpowers/specs/` 設計與 `docs/superpowers/plans/` 實作計畫。

## Dev bootstrap (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

## 資料說明
`data/seed/streets.json` 為示意用 seed 資料（台南中西區三條街），非真實營業資訊。
