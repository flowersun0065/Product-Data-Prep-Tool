"""Tool: 可用品牌类型列表"""

from ..tool_registry import ToolRegistry, BaseTool
from ...brands.database import BRAND_DATABASE_V6


@ToolRegistry.register
class ToolReadBrandTypes(BaseTool):
    name = "read_brand_types"
    description = "返回系统所有可用的品牌类型列表"

    def execute(self) -> dict:
        types = sorted(set(
            info.get("type", "") for info in BRAND_DATABASE_V6.values()
            if isinstance(info, dict) and info.get("type")
        ))
        return {"types": types, "total": len(types)}
