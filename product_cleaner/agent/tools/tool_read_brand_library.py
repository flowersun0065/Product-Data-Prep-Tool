"""Tool: 查询品牌库"""

from ..tool_registry import ToolRegistry, BaseTool
from ...brands.database import BRAND_DATABASE_V6, find_any_brand, get_all_brands


@ToolRegistry.register
class ToolReadBrandLibrary(BaseTool):
    name = "read_brand_library"
    description = "搜索品牌库，可按名称关键词/类型/国家筛选"
    input_schema = {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "品牌名称关键词（可选）"},
            "brand_type": {"type": "string", "description": "品牌类型筛选（可选）"},
            "country": {"type": "string", "description": "国家代码筛选（可选）"},
            "limit": {"type": "integer", "description": "返回数量限制（默认 20）"},
        },
    }

    def execute(self, keyword: str = "", brand_type: str = "",
                country: str = "", limit: int = 20) -> dict:
        brands = list(BRAND_DATABASE_V6.items())

        # 关键词搜索
        if keyword:
            kw = keyword.lower()
            # 用 find_any_brand 精确匹配
            match = find_any_brand(keyword)
            if match["found"]:
                standard = match["standard_name"]
                info = BRAND_DATABASE_V6.get(standard, {})
                return {
                    "found": True,
                    "brands": [{
                        "name": standard,
                        "type": info.get("type", ""),
                        "country": info.get("country", ""),
                        "aliases": info.get("aliases", []),
                    }],
                    "total": 1,
                }
            # 模糊匹配
            results = []
            for name, info in brands:
                if isinstance(info, dict) and kw in name.lower():
                    results.append({
                        "name": name,
                        "type": info.get("type", ""),
                        "country": info.get("country", ""),
                        "aliases": info.get("aliases", []),
                    })
            brands = results

        # 类型过滤
        if brand_type:
            brands = [b for b in brands if isinstance(b[1], dict) and b[1].get("type") == brand_type]

        # 国家过滤
        if country:
            brands = [b for b in brands if isinstance(b[1], dict) and b[1].get("country") == country]

        results = [
            {"name": name,
             "type": info.get("type", "") if isinstance(info, dict) else "",
             "country": info.get("country", "") if isinstance(info, dict) else "",
             "aliases": info.get("aliases", []) if isinstance(info, dict) else [],
             "sub_brands": list(info.get("sub_brands", {}).keys()) if isinstance(info, dict) and info.get("sub_brands") else [],
             }
            for name, info in brands[:limit]
        ]

        return {
            "found": len(results) > 0,
            "brands": results,
            "total": len(results),
        }
