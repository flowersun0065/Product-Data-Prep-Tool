"""Tool: 品牌聚类分析"""

from ..tool_registry import ToolRegistry, BaseTool
from ...core.brand_cluster import BrandClusterEngine


@ToolRegistry.register
class ToolBrandCluster(BaseTool):
    name = "brand_cluster"
    description = "对商品进行品牌聚类分析，识别缺失/异常/有效品牌"

    def execute(self, df, col_mapping: dict) -> dict:
        name_col = col_mapping.get("org_spu_name")
        brand_col = col_mapping.get("brand_name")
        code_col = col_mapping.get("org_spu_code")

        if not name_col:
            return {"error": "缺少 org_spu_name 列映射"}

        clusters = BrandClusterEngine.cluster(
            df, name_col, brand_col, code_col, col_mapping
        )

        stats = {
            "valid": sum(c.get("count", 0) for c in clusters if c.get("type") == "valid"),
            "missing": sum(c.get("count", 0) for c in clusters if c.get("type") == "missing"),
            "mismatch": sum(c.get("count", 0) for c in clusters if c.get("type") == "mismatch"),
            "unbranded": sum(c.get("count", 0) for c in clusters if c.get("type") == "unbranded"),
            "total_clusters": len(clusters),
        }

        return {
            "clusters": clusters,
            "stats": stats,
        }
