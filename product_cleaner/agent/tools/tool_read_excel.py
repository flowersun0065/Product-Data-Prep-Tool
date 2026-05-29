"""Tool: 读取 Excel 文件"""

import pandas as pd
import numpy as np
from pathlib import Path

from ..tool_registry import ToolRegistry, BaseTool


@ToolRegistry.register
class ToolReadExcel(BaseTool):
    name = "read_excel"
    description = "读取 Excel 文件，返回 DataFrame 和元数据"

    def execute(self, file_path: str, col_mapping: dict = None) -> dict:
        fp = Path(file_path)
        if not fp.exists():
            return {"error": f"文件不存在: {file_path}"}

        df = None
        last_error = None
        for engine in ["openpyxl", "xlrd"]:
            try:
                df = pd.read_excel(file_path, engine=engine)
                break
            except Exception as e:
                last_error = str(e)
                continue

        if df is None:
            try:
                df = pd.read_excel(file_path)
            except Exception as e:
                return {"error": f"无法读取文件: {last_error or str(e)}"}

        df = df.replace({np.nan: None})
        total_rows = len(df)
        columns = list(df.columns)

        brand_candidates = []
        if col_mapping and col_mapping.get("brand_name"):
            bc = col_mapping["brand_name"]
            if bc in df.columns:
                brand_candidates = df[bc].dropna().unique().tolist()

        return {
            "df": df,
            "total_rows": total_rows,
            "columns": columns,
            "file_size": fp.stat().st_size,
            "brand_candidates": brand_candidates[:20],
            "engine": engine if "engine" in dir() else "auto",
        }
