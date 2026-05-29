"""Tool: 系统目录 — Agent 了解系统有什么"""

from ..tool_registry import ToolRegistry, BaseTool


@ToolRegistry.register
class ToolReadSystemCatalog(BaseTool):
    name = "read_system_catalog"
    description = "返回系统目录：所有可读数据、可用工具、AI 角色设定"

    def execute(self, workflow: str = "data_cleaning") -> dict:
        tools = ToolRegistry.list_tools()

        if workflow == "data_cleaning":
            read_tools = [t for t in tools if t["name"].startswith("read_")]
            ai_tools = [t for t in tools if t["name"].startswith("ai_") and t["name"] != "ai_summarize"]
            execute_tools = [t for t in tools if t["name"].startswith("execute_")]
        elif workflow == "data_analysis":
            read_tools = [t for t in tools if t["name"].startswith("read_")]
            ai_tools = [t for t in tools if t["name"].startswith("ai_")]
            execute_tools = [t for t in tools if t["name"].startswith("execute_")]
        else:
            read_tools = [t for t in tools if t["name"].startswith("read_")]
            ai_tools = [t for t in tools if t["name"].startswith("ai_")]
            execute_tools = [t for t in tools if t["name"].startswith("execute_")]

        return {
            "data": {
                "session": [
                    {"name": "diagnosis_result", "description": "当前诊断结果：品牌聚类、新品牌、分类分析、统计"},
                    {"name": "new_brands", "description": "新品牌候选列表"},
                    {"name": "stats", "description": "诊断统计概览"},
                ],
                "global": [
                    {"name": "brand_library", "description": "品牌库"},
                    {"name": "brand_types", "description": "可用品牌类型列表"},
                    {"name": "countries", "description": "可用国家代码列表"},
                ],
            },
            "tools": {
                "read": [{"name": t["name"], "description": t["description"]} for t in read_tools],
                "ai": [{"name": t["name"], "description": t["description"]} for t in ai_tools],
                "execute": [{"name": t["name"], "description": t["description"]} for t in execute_tools],
            },
            "role": "你是一个数据处理系统的 AI 助手。你帮助用户清洗数据、管理品牌库、分析分类路径。"
                    "你有只读工具（read_*）可以查看数据，"
                    "有 AI 分析工具（ai_*）可以做智能判断，"
                    "有执行工具（execute_*）可以在用户确认后操作数据库。"
                    "数据分析你可以自己写 Python 脚本（execute_python），在受限沙盒中运行。",
        }
