"""
Tool: AI 审核新品牌候选 — 只做判断，不入库

接收 llm_call 函数（由对话系统传入），不自己初始化 AI 引擎。
没有 llm_call 时降级为自己读 settings 初始化。
"""

import json
import logging
from typing import List, Dict

from ..tool_registry import ToolRegistry, BaseTool

logger = logging.getLogger(__name__)

REVIEW_PROMPT = """你是一个电商品牌管理专家。商品经过算法处理，已初步识别出一些"疑似新品牌"，并给出了预填信息。
请你逐条审核：**预填值对不对？**

审核原则：
- **默认信任算法**：算法已经过大量数据验证，没有明确错误就确认
- **只在你非常确定有错误时才修正**
- **只在完全无法判断时才标记 ask_user**

## 现有品牌库（部分参考）
已有 {brand_count} 个品牌，包含但不限于：{brand_samples}
品牌类型：{brand_types}
国家和地区：{countries}

## 待审核品牌列表
每条包含：
- name：算法候选的品牌名（已预填值）
- type：算法推测的品牌类型
- country：算法推测的国家
- sample_product：该品牌关联的代表性商品
- sample_category：该商品所属分类

{new_brands_json}

## 审核要求

对每条候选，你的任务是审核算法给出的结论，返回以下操作之一：

1. **confirm** — **确认是品牌。**
   - 商品名中包含品牌名，且看起来像真实品牌 → confirm
   - **使用列表里预填的 type 和 country**，不要自己猜
   - 如果你觉得预填的 type/country 不对 → 走 correct

2. **correct** — 预填值需要修正
   - 名字有错别字："农妇山泉" → "农夫山泉"
   - 类型不对："零食" → "饮料"
   - 在 brand_name / brand_type / country 里填修正值
   - **brand_type 先尝试从类型列表中选，确实没有匹配的再新增**

3. **confirm_as_sub_brand** — 是某主品牌的子品牌

4. **confirm_as_alias** — 是某主品牌的别名

5. **reject** — **能判断不是品牌。** 品类词、营销词、描述短语等

6. **ask_user** — **无法判断，信息不足。** 仅限：不确定是不是品牌、有歧义

返回 JSON（只返回 JSON，不要其他文字）：
{{
  "actions": [
    {{
      "name": "候选品牌名",
      "action": "confirm|correct|confirm_as_sub_brand|confirm_as_alias|reject|ask_user",
      "brand_name": "修正后的品牌名（correct 时必填）",
      "brand_type": "品牌类型",
      "country": "国家代码",
      "parent_brand": "主品牌名（sub_brand/alias 时必填）",
      "aliases": ["别名"],
      "confidence": 0.0-1.0,
      "reason": "判断理由"
    }}
  ]
}}
"""


@ToolRegistry.register
class ToolAIReviewNewBrands(BaseTool):
    name = "ai_review_new_brands"
    description = "AI 批量审核新品牌候选：判断每条是否品牌、预填值对不对。只出结论，不入库。"
    input_schema = {
        "type": "object",
        "properties": {
            "new_brands": {
                "type": "array",
                "description": "新品牌候选列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "country": {"type": "string"},
                        "sample_product": {"type": "string"},
                        "sample_category": {"type": "string"},
                    },
                },
            },
        },
        "required": ["new_brands"],
    }

    def execute(self, new_brands: List[Dict], llm_call=None,
                api_key: str = None, provider: str = None,
                model_id: str = None) -> Dict:
        if not new_brands:
            return {
                "actions": [],
                "summary": {"total": 0, "confirmed": 0, "corrected": 0,
                           "sub_brand": 0, "alias": 0, "rejected": 0, "uncertain": 0},
            }

        from ...brands.database import BRAND_DATABASE_V6

        brand_names = list(BRAND_DATABASE_V6.keys())
        brand_types = sorted(set(
            info.get("type", "") for info in BRAND_DATABASE_V6.values()
            if isinstance(info, dict) and info.get("type")
        ))
        countries = sorted(set(
            info.get("country", "") for info in BRAND_DATABASE_V6.values()
            if isinstance(info, dict) and info.get("country")
        ))

        prompt = REVIEW_PROMPT.format(
            brand_count=len(brand_names),
            brand_samples=", ".join(brand_names[:40]),
            brand_types=", ".join(brand_types),
            countries=", ".join(countries),
            new_brands_json=json.dumps(
                [{"name": b["name"], "type": b.get("type", ""),
                  "country": b.get("country", "CN"),
                  "sample_product": b.get("sample_product", ""),
                  "sample_category": b.get("sample_category", "")}
                 for b in new_brands],
                ensure_ascii=False, indent=2),
        )

        try:
            if llm_call:
                text = llm_call(prompt)
            else:
                from ...core.ai_engine import ProductCleanerEngine
                engine = ProductCleanerEngine(
                    api_key=api_key or "",
                    provider=provider or "gemini",
                    model_id=model_id,
                )
                text = engine._call_ai(prompt, max_tokens=3000)
            from ...core.ai_engine import ProductCleanerEngine as _PCE
            data = _PCE._parse_json(None, text)
            actions = data.get("actions", [])
        except Exception as e:
            return {"error": f"AI 调用失败: {e}", "actions": [], "summary": {}}

        stats = {
            "total": len(actions),
            "confirmed": sum(1 for a in actions if a.get("action") == "confirm"),
            "corrected": sum(1 for a in actions if a.get("action") == "correct"),
            "sub_brand": sum(1 for a in actions if a.get("action") == "confirm_as_sub_brand"),
            "alias": sum(1 for a in actions if a.get("action") == "confirm_as_alias"),
            "rejected": sum(1 for a in actions if a.get("action") == "reject"),
            "uncertain": sum(1 for a in actions if a.get("action") == "ask_user"),
        }

        return {"actions": actions, "summary": stats}
