#!/usr/bin/env python3
"""
Agent Demo — 展示 Agent 如何调用现有工具处理数据。

用法:
    python -m product_cleaner.agent.demo <你的Excel文件>
    python -m product_cleaner.agent.demo --sample   (生成测试数据)
"""

import sys
import json
from pathlib import Path

# 注册所有工具（import 即注册）
from .tool_registry import ToolRegistry
from .tools.tool_read_excel import ToolReadExcel
from .tools.tool_brand_cluster import ToolBrandCluster
from .tools.tool_category import ToolCategory
from .tools.tool_diagnosis import ToolDiagnosis

try:
    import pandas as pd
except ImportError:
    pd = None


def make_sample_data(path: str):
    """生成示例 Excel 文件用于测试"""
    if pd is None:
        print("需要安装 pandas: pip install pandas openpyxl")
        sys.exit(1)
    data = {
        "商品名称": [
            "农夫山泉饮用天然水550ml",
            "乐事薯片原味75g",
            "伊利纯牛奶250ml",
            "金龙鱼花生油1.8L",
            "海底捞火锅底料麻辣味200g",
            "三得利乌龙茶500ml",
            "花王洗衣液补充装800g",
            "李锦记生抽酱油500ml",
            "湾仔码头水饺猪肉味400g",
            "瑞士莲特醇黑巧克力100g",
        ],
        "品牌": ["", "", "伊利", "", "海底捞", "", "", "李锦记", "", ""],
        "SPU编码": ["SPU001", "SPU002", "SPU003", "SPU004", "SPU005",
                     "SPU006", "SPU007", "SPU008", "SPU009", "SPU010"],
        "一级分类": ["饮料", "零食", "乳品", "粮油", "速食",
                     "饮料", "日化", "调味", "速冻", "零食"],
        "二级分类": ["饮用水", "薯片", "纯奶", "食用油", "火锅料",
                     "茶饮", "洗衣", "酱油", "水饺", "巧克力"],
        "三级分类": ["天然水", "原味", "纯牛奶", "花生油", "麻辣",
                     "乌龙茶", "补充装", "生抽", "猪肉", "黑巧"],
    }
    df = pd.DataFrame(data)
    df.to_excel(path, index=False)
    print(f"  📄 已生成示例数据: {path} (10 行)")


def print_divider(char="─", width=56):
    print(char * width)


def print_step(step_num: int, total: int, tool_name: str):
    print(f"\n🔧 {step_num}/{total} {tool_name}")


def agent_think(message: str):
    print(f"  🤔 Agent: {message}")


def tool_result(status: str, message: str):
    icon = "✅" if status == "ok" else "⚠️" if status == "warn" else "❌"
    print(f"     {icon} {message}")


def main():
    args = sys.argv[1:]

    if "--sample" in args or not args:
        path = "agent_demo_sample.xlsx"
        make_sample_data(path)
    else:
        path = args[0]
        if not Path(path).exists():
            print(f"文件不存在: {path}")
            sys.exit(1)

    # 列映射（与 web/app.py 自动猜测逻辑一致）
    col_mapping = {
        "org_spu_name": "商品名称",
        "brand_name": "品牌",
        "org_spu_code": "SPU编码",
        "cate_level1_name": "一级分类",
        "cate_level2_name": "二级分类",
        "cate_level3_name": "三级分类",
    }

    # ── 展示 Agent 可用的所有工具 ──
    print_divider("━")
    print("  Agent 工具箱:")
    for t in ToolRegistry.list_tools():
        print(f"    🧰 {t['name']}: {t['description']}")
    print_divider("━")

    # ── Agent 制定计划 ──
    agent_think(f"收到文件: {path}")
    col_info = ", ".join(col_mapping.values())
    agent_think(f"识别到列: {col_info}")
    agent_think("决定按以下计划执行:")
    plan = [
        ("read_excel", {"file_path": path, "col_mapping": col_mapping}),
        ("brand_cluster", {}),
        ("category_analysis", {}),
        ("diagnosis", {}),
    ]
    for i, (name, _) in enumerate(plan, 1):
        desc = ToolRegistry._tools[name].description
        print(f"      {i}. {name} — {desc}")
    print_divider("─")

    # ── 执行: 读取文件 ──
    step_total = len(plan)
    step_num = 0

    step_num += 1
    print_step(step_num, step_total, "read_excel")
    r1 = ToolRegistry.call("read_excel", file_path=path, col_mapping=col_mapping)
    if "error" in r1:
        tool_result("err", r1["error"])
        sys.exit(1)
    df = r1.pop("df")  # DataFrame 需要取出单独传递
    tool_result("ok", f"读取完成: {r1['total_rows']} 行, {len(r1['columns'])} 列")
    if r1["brand_candidates"]:
        tool_result("ok", f"发现 {len(r1['brand_candidates'])} 个品牌候选值")
    agent_think(f"数据已加载，下一步进行品牌聚类")

    # ── 执行: 品牌聚类 ──
    step_num += 1
    print_step(step_num, step_total, "brand_cluster")
    r2 = ToolRegistry.call("brand_cluster", df=df, col_mapping=col_mapping)
    if "error" in r2:
        tool_result("err", r2["error"])
        sys.exit(1)
    s = r2["stats"]
    tool_result("ok", f"聚类完成: 有效 {s['valid']}, 缺失 {s['missing']}, 异常 {s['mismatch']}"
                f"{', 无品牌候选 ' + str(s['unbranded']) if s['unbranded'] else ''}")
    agent_think(f"品牌聚类完成，下一步进行分类分析")

    # ── 执行: 分类分析 ──
    step_num += 1
    print_step(step_num, step_total, "category_analysis")
    r3 = ToolRegistry.call("category_analysis", df=df, col_mapping=col_mapping)
    if "error" in r3:
        tool_result("err", r3["error"])
        sys.exit(1)
    tool_result("ok", f"分类归集: {r3['path_count']} 条标准路径")
    if r3["conflict_count"]:
        tool_result("warn", f"发现 {r3['conflict_count']} 个冲突分类")
    if r3["marketing_count"]:
        tool_result("warn", f"识别 {r3['marketing_count']} 个营销分类")
    agent_think("分类分析完成，正在汇总诊断结果")

    # ── 执行: 诊断汇总 ──
    step_num += 1
    print_step(step_num, step_total, "diagnosis")
    r4 = ToolRegistry.call(
        "diagnosis",
        brand_clusters=r2["clusters"],
        category_result=r3["category_result"],
        total_rows=r1["total_rows"],
    )
    tool_result("ok", "诊断汇总完成")

    # ── 输出结果 ──
    print_divider("━")
    print("  📊 诊断结果:")
    print(f"     总商品数:       {r4['total']}")
    print(f"     正常:           {r4['valid']}")
    print(f"     品牌缺失:       {r4['brand_missing']}")
    print(f"     品牌异常:       {r4['brand_mismatch']}")
    print(f"     营销分类:       {r4['marketing']}")
    print(f"     待 AI 处理:     {r4['need_ai']}")
    print_divider("━")

    # 保存结果为 JSON（agent 可以读）
    result_path = Path(path).with_suffix(".diagnosis.json")
    serializable = {k: v for k, v in r4.items() if k != "brand_clusters"}
    result_path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2, default=str)
    )
    print(f"  💾 诊断结果已保存: {result_path}")
    print()


if __name__ == "__main__":
    main()
