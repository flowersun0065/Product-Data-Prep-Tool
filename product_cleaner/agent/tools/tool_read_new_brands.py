"""Tool: 从诊断结果中读取新品牌候选列表"""

import json
from pathlib import Path

from ..tool_registry import ToolRegistry, BaseTool
from ...constants import CACHE_FOLDER

SNAPSHOT_DIR = CACHE_FOLDER / "session_snapshots"


@ToolRegistry.register
class ToolReadNewBrands(BaseTool):
    name = "read_new_brands"
    description = "从诊断结果中读取新品牌候选列表"
    input_schema = {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "会话 ID"}
        },
        "required": ["session_id"],
    }

    def execute(self, session_id: str = "") -> dict:
        if not session_id:
            return {"error": "请提供 session_id"}

        # 从 diagnosis_result tool 复用的查找逻辑
        snapshot_file = self._find_snapshot(session_id)
        if not snapshot_file:
            return {"error": f"会话 {session_id} 不存在"}

        try:
            data = json.load(open(snapshot_file))
        except Exception as e:
            return {"error": f"读取失败: {e}"}

        new_brands = data.get("new_brands", [])
        if not new_brands:
            return {"error": "没有新品牌候选", "new_brands": []}

        stats = data.get("diagnosis_stats", {})
        return {
            "session_id": session_id,
            "total": len(new_brands),
            "unconfirmed": sum(1 for b in new_brands if not b.get("confirmed")),
            "has_metadata": sum(1 for b in new_brands if b.get("type") != "未知"),
            "types": list(set(b.get("type", "") for b in new_brands if b.get("type"))),
            "new_brands": new_brands,
            "stats": stats,
        }

    def _find_snapshot(self, session_id: str) -> Path:
        if not SNAPSHOT_DIR.exists():
            return None
        for path in [SNAPSHOT_DIR / f"{session_id}.json",
                     SNAPSHOT_DIR / f"{session_id[:12]}.json"]:
            if path.exists():
                return path
        for group_dir in SNAPSHOT_DIR.iterdir():
            if not group_dir.is_dir():
                continue
            for f in group_dir.iterdir():
                if f.suffix != ".json":
                    continue
                try:
                    data = json.load(open(f))
                    if data.get("session_id") == session_id or f.stem == session_id[:12]:
                        return f
                except Exception:
                    pass
        return None
