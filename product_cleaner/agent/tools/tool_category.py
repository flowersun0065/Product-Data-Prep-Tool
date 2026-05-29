"""Tool: 分类分析"""

from ..tool_registry import ToolRegistry, BaseTool
from ...core.product_parser import build_entity_dict
from ...core.category_detector import CategoryDetector


@ToolRegistry.register
class ToolCategory(BaseTool):
    name = "category_analysis"
    description = "对商品进行分类归集分析，识别标准路径、营销路径、冲突"

    def execute(self, df, col_mapping: dict) -> dict:
        name_col = col_mapping.get("org_spu_name")
        if not name_col:
            return {"error": "缺少 org_spu_name 列映射"}

        entity_dict = build_entity_dict(
            df[name_col].dropna().astype(str).tolist()
        )
        category_result = CategoryDetector.analyze(df, col_mapping, entity_dict)

        stats = category_result.get("stats", {})
        cleaned_paths = category_result.get("cleaned_paths", {})

        return {
            "category_result": category_result,
            "entity_dict": entity_dict,
            "path_count": len(cleaned_paths),
            "conflict_count": stats.get("conflict_count", 0),
            "marketing_count": stats.get("pure_marketing_count", 0),
            "missing_count": stats.get("missing_count", 0),
        }
