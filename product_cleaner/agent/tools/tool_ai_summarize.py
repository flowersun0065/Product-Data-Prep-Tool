"""Tool: 将审核结果归纳为人类可读的报告"""

from ..tool_registry import ToolRegistry, BaseTool


@ToolRegistry.register
class ToolAISummarize(BaseTool):
    name = "ai_summarize"
    description = "将结构化审核结果归纳为人类可读的汇总报告"
    input_schema = {
        "type": "object",
        "properties": {
            "actions": {"type": "array", "description": "ai_review_new_brands 输出的 actions"},
            "summary": {"type": "object", "description": "ai_review_new_brands 输出的 summary"},
        },
        "required": ["actions", "summary"],
    }

    def execute(self, actions: list, summary: dict) -> dict:
        if not actions:
            return {"report": "没有需要处理的数据。"}

        lines = []

        # 归纳 confirmed
        confirmed = [a for a in actions if a.get("action") == "confirm"]
        if confirmed:
            groups = {}
            for a in confirmed:
                t = a.get("brand_type", "未知")
                groups.setdefault(t, []).append(a["name"])
            lines.append("## 确认是品牌（建议入库）")
            for t, names in sorted(groups.items()):
                lines.append(f"- {t}: {', '.join(names)}")

        # 归纳 sub_brand / alias
        sub_brands = [a for a in actions if a.get("action") == "confirm_as_sub_brand"]
        if sub_brands:
            lines.append("## 确认是子品牌")
            for a in sub_brands:
                lines.append(f"- {a['name']} → 主品牌: {a['parent_brand']}")

        aliases = [a for a in actions if a.get("action") == "confirm_as_alias"]
        if aliases:
            lines.append("## 确认是别名")
            for a in aliases:
                lines.append(f"- {a['name']} → 主品牌: {a['parent_brand']}")

        # 归纳 corrected
        corrected = [a for a in actions if a.get("action") == "correct"]
        if corrected:
            lines.append("## 已修正")
            for a in corrected:
                lines.append(f"- {a['name']} → {a.get('brand_name', '')} ({a.get('reason', '')})")

        # 归纳 rejected
        rejected = [a for a in actions if a.get("action") == "reject"]
        if rejected:
            lines.append("## 跳过（不是品牌）")
            # 按 reason 分组
            groups = {}
            for a in rejected:
                r = a.get("reason", "其他")[:20]
                groups.setdefault(r, []).append(a["name"])
            for r, names in groups.items():
                lines.append(f"- {r}: {', '.join(names)}")

        # 归纳 uncertain
        uncertain = [a for a in actions if a.get("action") == "ask_user"]
        if uncertain:
            lines.append("## 需要您确认")
            for a in uncertain:
                lines.append(f"- {a['name']}: {a.get('reason', '')}")

        # 总览
        s = summary
        header = [
            f"共处理 {s.get('total', 0)} 条："
        ]
        parts = []
        if s.get("confirmed"):
            parts.append(f"确认 {s['confirmed']} 条")
        if s.get("corrected"):
            parts.append(f"修正 {s['corrected']} 条")
        if s.get("sub_brand"):
            parts.append(f"子品牌 {s['sub_brand']} 条")
        if s.get("rejected"):
            parts.append(f"跳过 {s['rejected']} 条")
        if s.get("uncertain"):
            parts.append(f"需确认 {s['uncertain']} 条")
        if parts:
            header.append("、".join(parts))

        return {"report": "\n\n".join(header + lines)}
