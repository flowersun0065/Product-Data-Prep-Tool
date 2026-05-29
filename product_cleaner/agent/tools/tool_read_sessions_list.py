"""Tool: 列出所有可用的历史会话（与 API 返回格式一致）"""

from pathlib import Path
from datetime import datetime

from ..tool_registry import ToolRegistry, BaseTool
from ...constants import CACHE_FOLDER

SNAPSHOT_DIR = CACHE_FOLDER / "session_snapshots"


@ToolRegistry.register
class ToolReadSessionsList(BaseTool):
    name = "read_sessions_list"
    description = "列出所有可用的历史会话"

    def execute(self) -> dict:
        sessions = []
        if not SNAPSHOT_DIR.exists():
            return {"sessions": [], "total": 0}

        for group_dir in sorted(SNAPSHOT_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not group_dir.is_dir():
                continue
            for f in sorted(group_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if f.suffix != ".json" or f.name.startswith("."):
                    continue
                try:
                    import json
                    data = json.load(open(f))
                    created = data.get("created", "")
                    sessions.append({
                        "session_id": data.get("session_id", f.stem),
                        "group_id": group_dir.name,
                        "file_name": data.get("file_name", f.stem),
                        "display_name": Path(data.get("file_path", "")).name if data.get("file_path") else f.stem,
                        "status": data.get("status", ""),
                        "diagnosis_status": data.get("diagnosis_status", ""),
                        "diagnosis_stats": data.get("diagnosis_stats", {}),
                        "created": created,
                    })
                except Exception:
                    pass

        # 再读无 group 的独立文件
        for f in sorted(SNAPSHOT_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.suffix != ".json" or f.name.startswith(".") or f.is_dir():
                continue
            try:
                import json
                data = json.load(open(f))
                created = data.get("created", "")
                sessions.append({
                    "session_id": data.get("session_id", f.stem),
                    "group_id": "",
                    "file_name": data.get("file_name", f.stem),
                    "display_name": Path(data.get("file_path", "")).name if data.get("file_path") else f.stem,
                    "status": data.get("status", ""),
                    "diagnosis_status": data.get("diagnosis_status", ""),
                    "diagnosis_stats": data.get("diagnosis_stats", {}),
                    "created": created,
                })
            except Exception:
                pass

        sessions.sort(key=lambda x: x["created"], reverse=True)
        return {"sessions": sessions[:50], "total": len(sessions)}
