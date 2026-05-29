"""Tool 注册中心 — 所有工具注册、发现、调用的入口"""

from typing import Dict, List, Any


class BaseTool:
    """所有工具的基类"""
    name: str = ""
    description: str = ""

    def execute(self, **kwargs) -> Any:
        raise NotImplementedError


class ToolRegistry:
    """工具注册中心"""
    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool_cls):
        """注册一个工具类（实例化后注册）"""
        instance = tool_cls()
        cls._tools[instance.name] = instance
        return tool_cls

    @classmethod
    def list_tools(cls) -> List[Dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
            }
            for t in cls._tools.values()
        ]

    @classmethod
    def call(cls, name: str, **kwargs) -> Any:
        if name not in cls._tools:
            raise KeyError(f"未知工具: {name}，可用: {list(cls._tools.keys())}")
        return cls._tools[name].execute(**kwargs)
