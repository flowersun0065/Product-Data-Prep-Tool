"""Tool: 可用国家代码列表"""

from ..tool_registry import ToolRegistry, BaseTool
from ...brands.database import BRAND_DATABASE_V6


@ToolRegistry.register
class ToolReadCountries(BaseTool):
    name = "read_countries"
    description = "返回系统所有可用的国家代码列表"

    def execute(self) -> dict:
        countries = sorted(set(
            info.get("country", "") for info in BRAND_DATABASE_V6.values()
            if isinstance(info, dict) and info.get("country")
        ))
        return {"countries": countries, "total": len(countries)}
