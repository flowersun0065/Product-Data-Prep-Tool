#!/usr/bin/env python3
"""测试 AI 批量确认品牌 Tool — 用真实诊断数据"""

import json
import sys
sys.path.insert(0, "/Users/lynn.sun_1/Downloads/files")

from product_cleaner.agent.tool_registry import ToolRegistry
from product_cleaner.agent.tools.tool_ai_confirm_brands import ToolAIConfirmBrands

# 读取真实的 session 新品牌数据
snapshot = json.load(open(
    "/Users/lynn.sun_1/Downloads/files/product_cleaner/cache/session_snapshots/921f8216/9cac1ff90073.json"
))
new_brands = snapshot.get("new_brands", [])
print(f"读取到 {len(new_brands)} 个真实新品牌候选")

# 从 settings.json 读取 API Key
settings = json.load(open(
    "/Users/lynn.sun_1/Downloads/files/product_cleaner/cache/settings.json"
))
ai_configs = settings.get("ai_configs", [])
if ai_configs:
    api_key = ai_configs[0].get("api_key") or settings.get("api_key", "")
    provider = ai_configs[0].get("provider") or settings.get("ai_provider", "gemini")
    model_id = ai_configs[0].get("model") or settings.get("model_id", "")
else:
    api_key = settings.get("api_key", "")
    provider = settings.get("ai_provider", "gemini")
    model_id = settings.get("model_id", "")

if not api_key:
    print("❌ 请在页面设置中填写 API Key")
    sys.exit(1)
print(f"✅ API: {provider}/{model_id or '默认'}")

# 调 AI 审核（每次测 10 条左右，可以换切片测试不同数据）
start = 10  # 改这个偏移量来测不同批
batch = new_brands[start:start + 10]
print(f"测试第 {start+1}-{start+len(batch)} 条")
result = ToolRegistry.call(
    "ai_confirm_new_brands",
    new_brands=batch,
    api_key=api_key,
    provider=provider,
    model_id=model_id,
)

print(json.dumps(result, ensure_ascii=False, indent=2))
