"""
Tool: 执行品牌入库操作。

只接收 ai_review_new_brands 输出的 actions，不会自动发起审核。
用户确认后调此工具完成入库。
"""

import logging
from typing import List, Dict

from ..tool_registry import ToolRegistry, BaseTool

logger = logging.getLogger(__name__)


@ToolRegistry.register
class ToolExecuteBrandActions(BaseTool):
    name = "execute_brand_actions"
    description = "执行品牌入库操作。接收 ai_review_new_brands 的审核结果，按用户确认的 actions 执行。不会自动发起审核。"
    input_schema = {
        "type": "object",
        "properties": {
            "actions": {
                "type": "array",
                "description": "ai_review_new_brands 输出的 actions 列表",
            },
        },
        "required": ["actions"],
    }

    def execute(self, actions: List[Dict]) -> Dict:
        if not actions:
            return {"executed": [], "summary": {"total": 0, "success": 0, "error": 0}}

        from ...brands.database import add_brand, save_dismissed_brand

        results = []
        stats = {"total": len(actions), "success": 0, "skipped": 0, "error": 0}

        for action in actions:
            name = action.get("name", "")
            act = action.get("action", "")
            try:
                if act == "confirm":
                    add_brand(
                        brand_name=name,
                        aliases=[name],
                        brand_type=action.get("brand_type", "未知"),
                        country=action.get("country", "CN"),
                    )
                    stats["success"] += 1
                    results.append({"name": name, "action": "confirmed"})

                elif act == "confirm_as_sub_brand":
                    add_brand(
                        brand_name=name,
                        aliases=[name],
                        brand_type=action.get("brand_type", "未知"),
                        country=action.get("country", "CN"),
                        parent_brand=action["parent_brand"],
                        relation_type="sub_brand",
                    )
                    stats["success"] += 1
                    results.append({"name": name, "action": "confirmed_as_sub_brand",
                                    "parent_brand": action["parent_brand"]})

                elif act == "confirm_as_alias":
                    add_brand(
                        brand_name=name,
                        aliases=[name],
                        brand_type=action.get("brand_type", "未知"),
                        country=action.get("country", "CN"),
                        parent_brand=action["parent_brand"],
                        relation_type="alias",
                    )
                    stats["success"] += 1
                    results.append({"name": name, "action": "confirmed_as_alias",
                                    "parent_brand": action["parent_brand"]})

                elif act == "correct":
                    corrected = action.get("brand_name", name)
                    add_brand(
                        brand_name=corrected,
                        aliases=action.get("aliases", [corrected]),
                        brand_type=action.get("brand_type", "未知"),
                        country=action.get("country", "CN"),
                    )
                    if corrected != name:
                        save_dismissed_brand(name)
                    stats["success"] += 1
                    results.append({"name": name, "action": "corrected",
                                    "corrected_to": corrected})

                elif act == "reject":
                    save_dismissed_brand(name)
                    stats["success"] += 1
                    results.append({"name": name, "action": "rejected"})

                else:
                    # ask_user 或其他 → 跳过
                    stats["skipped"] += 1
                    results.append({"name": name, "action": "skipped"})

            except Exception as e:
                stats["error"] += 1
                results.append({"name": name, "action": "error", "error": str(e)})
                logger.warning(f"执行失败 [{name}]: {e}")

        return {"executed": results, "summary": stats}
