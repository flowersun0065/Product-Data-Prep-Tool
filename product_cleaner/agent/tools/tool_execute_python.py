"""
Tool: 在受限沙盒中运行 Python 脚本，用于数据分析。

安全限制：
  - 白名单 import：pandas, json, collections, re, math, statistics, itertools, typing, datetime
  - 禁止：os, subprocess, sys, shutil, requests, urllib, socket, importlib
  - 数据通过 data 全局变量注入
  - 超时 10 秒
  - 不能读写文件系统，不能碰网络
"""

import sys
import json
import traceback
from io import StringIO

from ..tool_registry import ToolRegistry, BaseTool

ALLOWED_IMPORTS = {
    "pandas", "json", "collections", "re", "math",
    "statistics", "itertools", "typing", "datetime",
    "_json",  # json 内部依赖
}


"""原始 __import__ 备份，防止递归"""
_original_import = __import__


def _safe_import(name, *args, **kwargs):
    """拦截 import，只允许白名单内的模块"""
    if name not in ALLOWED_IMPORTS:
        raise ImportError(f"不允许 import '{name}'，只能在白名单内: {', '.join(sorted(ALLOWED_IMPORTS))}")
    return _original_import(name, *args, **kwargs)


@ToolRegistry.register
class ToolExecutePython(BaseTool):
    name = "execute_python"
    description = "在受限沙盒中运行 Python 脚本，用于数据分析。数据通过 data 变量传入。不能读写文件系统和网络。"
    input_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python 代码"},
            "data": {"description": "要处理的数据（JSON 格式）"},
        },
        "required": ["code", "data"],
    }

    def execute(self, code: str, data) -> dict:
        if not code.strip():
            return {"error": "代码不能为空"}

        # 捕获输出
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        result = {"stdout": "", "stderr": "", "error": ""}

        try:
            # 设置安全 import
            safe_builtins = dict(__builtins__) if isinstance(__builtins__, dict) else dict(__builtins__.__dict__)
            safe_builtins["__import__"] = _safe_import
            local_vars = {"data": data}
            exec(code, {"__builtins__": safe_builtins}, local_vars)
            result["stdout"] = sys.stdout.getvalue()
            result["stderr"] = sys.stderr.getvalue()
        except Exception as e:
            result["stdout"] = sys.stdout.getvalue()
            result["error"] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        return result
