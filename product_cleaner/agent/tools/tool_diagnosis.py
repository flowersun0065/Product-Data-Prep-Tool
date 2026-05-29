"""Tool: 诊断汇总 — 精简集群 + 统计 + 打包结果"""

from ..tool_registry import ToolRegistry, BaseTool
from ...core.brand_cluster import lean_clusters


@ToolRegistry.register
class ToolDiagnosis(BaseTool):
    name = "diagnosis"
    description = "汇总品牌聚类和分类分析结果，生成最终诊断报告"

    def execute(self, brand_clusters: list, category_result: dict, total_rows: int) -> dict:
        lean_data = lean_clusters(brand_clusters)

        stats = category_result.get("stats", {})
        brand_missing = sum(c.get("count", 0) for c in brand_clusters if c.get("type") == "missing")
        brand_mismatch = sum(c.get("count", 0) for c in brand_clusters if c.get("type") == "mismatch")
        need_ai = brand_missing + brand_mismatch + stats.get("missing_count", 0)

        diagnosis = {
            "total": total_rows,
            "valid": total_rows - need_ai,
            "brand_missing": brand_missing,
            "brand_mismatch": brand_mismatch,
            "marketing": stats.get("pure_marketing_count", 0) + stats.get("conflict_count", 0),
            "need_ai": need_ai,
            "brand_clusters": lean_data,
            "conflict_groups": category_result.get("conflict_groups", []),
            "marketing_groups": category_result.get("marketing_groups", []),
            "standard_groups": category_result.get("standard_groups", []),
            "missing_items": category_result.get("missing_items", []),
            "cleaned_paths": category_result.get("cleaned_paths", {}),
            "path_classifications": category_result.get("path_classifications", {}),
            "category_options": category_result.get("category_options", {}),
        }

        return diagnosis
