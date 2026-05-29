"""Tool: 读取诊断结果 — 从 session 快照中获取"""

from pathlib import Path
import json

from ..tool_registry import ToolRegistry, BaseTool
from ...constants import CACHE_FOLDER

SNAPSHOT_DIR = CACHE_FOLDER / "session_snapshots"


@ToolRegistry.register
class ToolReadDiagnosisResult(BaseTool):
    name = "read_diagnosis_result"
    description = "读取当前诊断结果：品牌聚类、新品牌、分类分析、统计"
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

        # 根据 session_id 定位快照文件
        snapshot_file = self._find_snapshot(session_id)
        if not snapshot_file:
            return {"error": f"会话 {session_id} 不存在"}

        try:
            data = json.load(open(snapshot_file))
        except Exception as e:
            return {"error": f"读取失败: {e}"}

        diagnosis_result = data.get("diagnosis_result")
        if not diagnosis_result:
            return {"error": "该会话没有诊断结果"}

        diagnosis_stats = data.get("diagnosis_stats", {})
        new_brands = data.get("new_brands", [])

        # 返回关键元数据概览 + 完整诊断结果
        return {
            "session_id": session_id,
            "file_name": Path(data.get("file_path", "")).name if data.get("file_path") else "",
            "stats": diagnosis_stats,
            "new_brand_count": len(new_brands),
            "diagnosis_result": {
                "brand_clusters_count": len(diagnosis_result.get("brand_clusters", [])),
                "conflict_groups_count": len(diagnosis_result.get("conflict_groups", [])),
                "marketing_groups_count": len(diagnosis_result.get("marketing_groups", [])),
                "missing_items_count": len(diagnosis_result.get("missing_items", [])),
                "all_codes_count": len(diagnosis_result.get("all_codes", [])),
                "cleaned_paths_count": len(diagnosis_result.get("cleaned_paths", {})),
            },
            "full_data": diagnosis_result,
        }

    def _find_snapshot(self, session_id: str) -> Path:
        """在快照目录中查找 session_id 对应的文件"""
        if not SNAPSHOT_DIR.exists():
            return None

        # 直接匹配：session_xxx.json
        for path in [SNAPSHOT_DIR / f"{session_id}.json",
                     SNAPSHOT_DIR / f"{session_id[:12]}.json"]:
            if path.exists():
                return path

        # 按 group_id 分目录查找
        for group_dir in SNAPSHOT_DIR.iterdir():
            if not group_dir.is_dir():
                continue
            for f in group_dir.iterdir():
                if f.suffix != ".json":
                    continue
                try:
                    data = json.load(open(f))
                    if data.get("session_id") == session_id:
                        return f
                    if f.stem == session_id or f.stem == session_id[:12]:
                        return f
                except Exception:
                    pass
        return None
