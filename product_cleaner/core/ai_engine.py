#!/usr/bin/env python3
"""
AI 处理引擎 - 商品品牌/分类补全

支持 Provider: Gemini / Claude / OpenAI / DeepSeek
品牌: 品牌库匹配优先 → 匹配不上再调 AI 推断
分类: AI 分析优先 → AI 失败时 fallback 到本地算法
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# 品牌库缓存（含 dynamic_brands + relationships，在 database.py 启动时已合并到 V6）
_BRAND_CACHE = None

def _get_brand_cache():
    global _BRAND_CACHE
    if _BRAND_CACHE is None:
        from ..brands.database import BRAND_DATABASE_V6
        _BRAND_CACHE = list(BRAND_DATABASE_V6.items())
    return _BRAND_CACHE

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import google.genai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


BRAND_PROMPT = """你是一个电商商品数据清洗专家。请从商品名称中提取品牌信息。

商品名称: {product_name}

要求：
1. 提取商品所属的品牌名称
2. 如果无法确定品牌，返回 null
3. 品牌名称要简洁标准，不要包含"公司"、"集团"、"有限"等后缀
4. 说明判断理由

返回 JSON 格式（只返回 JSON，不要其他文字）：
{{
  "brand": "品牌名称 或 null",
  "brand_type": "品牌类型（如：饮料、零食、日化等）",
  "confidence": 0.0-1.0,
  "reason": "判断理由"
}}"""

COMBINED_PROMPT = """你是一个电商商品数据清洗专家。请同时分析以下商品的品牌和分类信息。

商品名称: {product_name}
{brand_info}
{product_paths_info}
===== 可选的标准化分类路径（必须从以下列表中选择一条）=====
{category_options}
====================================================

要求：
1. 从商品名称中提取品牌名称，如果无法确定品牌返回 null
2. 品牌名称要简洁标准，不要包含"公司"、"集团"等后缀
3. **必须**从上方列表中选择一条分类路径，不要自己编造
4. 如果该商品已有原始分类路径列在上面，优先从中选择最接近商品实际的一条
5. 三级分类（最细的品类）匹配最重要

返回 JSON（只返回 JSON，不要其他文字）：
{{
  "brand": "品牌名称 或 null",
  "brand_type": "品牌类型",
  "brand_confidence": 0.0-1.0,
  "brand_reason": "品牌判断理由",
  "path": "一级 > 二级 > 三级",
  "cat_confidence": 0.0-1.0,
  "cat_reason": "分类选择理由",
  "needs_review": true/false,
  "factors": {{
    "entity": "商品核心品类词",
    "brand_type": "品牌类型",
    "modifiers": []
  }}
}}"""

CATEGORY_ANALYSIS_PROMPT = """你是一个电商商品分类专家。请分析以下商品的分类信息，**必须**从下方提供的可选路径中选择一个。

商品名称: {product_name}
{brand_info}
{product_paths_info}
===== 可选的标准化分类路径（必须从以下列表中选择一条）=====
{category_options}
====================================================

要求（请严格遵守）：
1. **必须**从上方列表中选择一条路径，不要自己编造
2. **如果该商品已有原始分类路径列在上面，优先从中选择最接近商品实际的一条。**
3. 只有该商品的所有已有路径都不符合时，才从标准化分类路径列表中选最接近的。
4. **选路径的核心原则：三级分类（最细的品类）匹配最重要。** 先看三级分类是否匹配商品核心品类词（entity），三级匹配的路径优先级最高，二级和一级合理即可。
5. 核心品类词（entity）以及 factors 是决定三级分类的关键，如果 entity 与你分析的不一致也可不参考
6. 品牌类型（brand_type）辅助判断一级分类
7. 当该商品有多个已有路径时，请在 reason 中说明从哪些路径中选择了哪一条、以及选择理由（如 entity 匹配 / 品类更接近等）
8. 置信度低于 0.7 时设置 needs_review=true

返回 JSON（只返回 JSON，不要其他文字）：
{{
  "path": "一级 > 二级 > 三级",
  "confidence": 0.0-1.0,
  "reason": "选择理由（如有多条已有路径，请说明从哪些路径中选择及原因）",
  "needs_review": true/false,
  "factors": {{
    "entity": "商品核心品类词",
    "brand_type": "品牌类型",
    "modifiers": []
  }}
}}"""


class ProductCleanerEngine:
    """核心数据清理引擎 - 支持品牌/分类按字段处理"""

    def __init__(self, api_key: Optional[str] = None,
                 provider: str = 'gemini',
                 model_id: Optional[str] = None,
                 base_url: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key or ''
        self.custom_base_url = base_url  # 用户自定义 base_url
        if not self.api_key:
            raise ValueError("未提供 API Key，请在页面中填写")
        self.call_count = 0
        self.model_id = model_id or self._default_model()
        self.client = self._init_client()
        self.last_error = None  # 最后一次 AI 调用错误
        self.last_prompt = None  # 最近一次调用的 prompt
        self.usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        self.last_usage = None  # 最近一次调用的 token

    def _default_model(self) -> str:
        models = {
            'gemini': 'models/gemini-2.0-flash',
            'claude': 'claude-3-haiku-20240307',
            'openai': 'gpt-4o-mini',
            'deepseek': 'deepseek-chat',
            'alibaba': 'qwen3.6-plus',
        }
        return models.get(self.provider, 'models/gemini-2.0-flash')

    def _init_client(self):
        p = self.provider
        key = self.api_key

        if p == 'gemini':
            if not HAS_GENAI:
                raise ImportError("请安装 google.genai: pip install google-genai")
            return genai.Client(api_key=key)

        elif p == 'claude':
            if not HAS_ANTHROPIC:
                raise ImportError("请安装 anthropic: pip install anthropic")
            return anthropic.Anthropic(api_key=key)

        elif p in ('openai', 'deepseek', 'alibaba'):
            if not HAS_OPENAI:
                raise ImportError("请安装 openai: pip install openai")
            if self.custom_base_url:
                base_url = self.custom_base_url  # 优先用用户设置
            elif p == 'alibaba' and key and key.startswith('sk-sp-'):
                base_url = 'https://coding.dashscope.aliyuncs.com/v1'
            elif p == 'alibaba':
                base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
            elif p == 'deepseek':
                base_url = 'https://api.deepseek.com'
            else:
                base_url = 'https://api.openai.com/v1'
            return OpenAI(api_key=key, base_url=base_url)

        else:
            raise ValueError(f"不支持的 provider: {p}")

    def _call_ai(self, prompt: str, max_tokens: int = 500) -> str:
        """调用 AI 并返回文本响应"""
        p = self.provider
        self.last_error = None
        self.last_prompt = prompt

        try:
            if p == 'gemini':
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt
                )
                if not response.text:
                    raise Exception("Gemini 返回了空内容")
                return response.text

            elif p == 'claude':
                response = self.client.messages.create(
                    model=self.model_id,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                if hasattr(response, 'usage'):
                    self.usage['prompt_tokens'] += response.usage.input_tokens or 0
                    self.usage['completion_tokens'] += response.usage.output_tokens or 0
                    self.usage['total_tokens'] += (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)
                return response.content[0].text

            elif p in ('openai', 'deepseek', 'alibaba'):
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                if hasattr(response, 'usage') and response.usage:
                    u = {'prompt_tokens': response.usage.prompt_tokens or 0,
                         'completion_tokens': response.usage.completion_tokens or 0,
                         'total_tokens': response.usage.total_tokens or 0}
                    self.usage['prompt_tokens'] += u['prompt_tokens']
                    self.usage['completion_tokens'] += u['completion_tokens']
                    self.usage['total_tokens'] += u['total_tokens']
                    self.last_usage = u
                return response.choices[0].message.content

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"AI 调用失败 ({p}): {e}")
            raise

    def _parse_json(self, text: str) -> dict:
        """从 AI 响应中提取 JSON"""
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        text = text.strip()
        return json.loads(text)

    # ===== 品牌处理 =====

    def clean_brand(self, product_name: str,
                    existing_suggestion: str = '') -> Dict:
        """补全品牌 - 品牌库匹配优先，匹配不上调 AI 推断

        Args:
            product_name: 商品名称
            existing_suggestion: 诊断阶段 brand_clusters 中的 suggested_brand
                                传入后不再重复提取，AI 结果会与此对比
        """
        from ..brands.database import find_any_brand, BRAND_DATABASE_V6, load_corrected_brands
        name_lower = product_name.lower()

        # Step 0: 如有修正记录（人工确认过的品牌映射），优先使用
        if existing_suggestion:
            corrected = load_corrected_brands().get(existing_suggestion)
            if corrected and corrected.get('corrected_to'):
                corrected_to = corrected['corrected_to']
                result = find_any_brand(corrected_to)
                if result['found']:
                    info = BRAND_DATABASE_V6.get(result['standard_name'], {})
                    return {
                        'brand': result['standard_name'],
                        'brand_type': info.get('type', '') if isinstance(info, dict) else '',
                        'confidence': 0.95,
                        'from_library': True,
                        'needs_review': False,
                        'error': None,
                        'reason': f'品牌修正记录: "{existing_suggestion}" → "{result["standard_name"]}"',
                        '_suggestion': existing_suggestion
                    }

        # Step 1: 已有建议 → 查品牌库
        if existing_suggestion:
            result = find_any_brand(existing_suggestion)
            if result['found']:
                info = BRAND_DATABASE_V6.get(result['standard_name'], {})
                # 标记为 from_library 但记录来源是诊断建议
                return {
                    'brand': result['standard_name'],
                    'brand_type': info.get('type', '') if isinstance(info, dict) else '',
                    'confidence': 0.95,
                    'from_library': True,
                    'needs_review': False,
                    'error': None,
                    'reason': f'品牌库匹配: {result["standard_name"]}',
                    '_suggestion': existing_suggestion
                }

        # Step 2: 商品名全文扫品牌库（兼容提取器漏掉的品牌）
        for brand_name, info in _get_brand_cache():
            if not isinstance(info, dict):
                continue
            if brand_name.lower() in name_lower:
                return {
                    'brand': brand_name,
                    'brand_type': info.get('type', ''),
                    'confidence': 0.9,
                    'from_library': True,
                    'needs_review': False,
                    'error': None,
                    'reason': f'品牌库扫描: "{brand_name}" 出现在商品名中',
                    '_suggestion': existing_suggestion
                }
            for alias in info.get('aliases', []):
                if isinstance(alias, str) and alias.lower() in name_lower:
                    return {
                        'brand': brand_name,
                        'brand_type': info.get('type', ''),
                        'confidence': 0.9,
                        'from_library': True,
                        'needs_review': False,
                        'error': None,
                        'reason': f'品牌库扫描: 别名"{alias}" 匹配 "{brand_name}"',
                        '_suggestion': existing_suggestion
                    }

        # Step 3: 调 AI 推断
        # AI 结果会与 existing_suggestion 对比：
        #   一致 → 高置信
        #   不一致 → 以 AI 为准
        prompt = BRAND_PROMPT.format(product_name=product_name)
        try:
            text = self._call_ai(prompt, max_tokens=200)
            data = self._parse_json(text)
            ai_brand = data.get('brand') or ''
            if not ai_brand or ai_brand.lower() == 'null':
                # AI 正确判断无品牌（非错误，如生鲜、散装商品）
                return {
                    'brand': existing_suggestion or '(无品牌)',
                    'brand_type': '',
                    'confidence': 0.5,   # AI 确认无品牌，有一定置信度
                    'from_library': False,
                    'needs_review': True,  # 仍需人工确认是否真的无品牌
                    'no_brand': True,
                    'error': None,
                    'reason': data.get('reason', 'AI 判断该商品无品牌'),
                    '_suggestion': existing_suggestion
                }

            # 对比 AI 结果与诊断建议
            agrees_with_suggestion = (existing_suggestion and
                                      ai_brand.lower() == existing_suggestion.lower())

            # AI 返回的品牌再查一次库（兼容别名）
            result = find_any_brand(ai_brand)
            if result['found']:
                info = BRAND_DATABASE_V6.get(result['standard_name'], {})
                return {
                    'brand': result['standard_name'],
                    'brand_type': info.get('type', '') if isinstance(info, dict) else '',
                    'confidence': 0.95 if agrees_with_suggestion else 0.9,
                    'from_library': True,
                    'needs_review': False,
                    'error': None,
                    'reason': data.get('reason', f'AI 推断为 "{ai_brand}"，已在品牌库确认'),
                    '_suggestion': existing_suggestion,
                    '_ai_agrees': agrees_with_suggestion
                }

            # AI 结果不在品牌库中
            return {
                'brand': ai_brand,
                'brand_type': data.get('brand_type', ''),
                'confidence': 0.85 if agrees_with_suggestion else data.get('confidence', 0.7),
                'from_library': False,
                'needs_review': not agrees_with_suggestion,
                'error': None,
                'reason': data.get('reason', f'AI 推断为 "{ai_brand}"，不在品牌库中'),
                '_suggestion': existing_suggestion,
                '_ai_agrees': agrees_with_suggestion
            }
        except Exception as e:
            error_msg = f"AI 品牌推断失败: {self.last_error or str(e)}"
            logger.warning(f"AI brand failed for '{product_name}': {error_msg}")
            return {
                'brand': existing_suggestion or '',
                'brand_type': '',
                'confidence': 0.0,
                'from_library': False,
                'needs_review': True,
                'error': error_msg,
                'reason': 'AI 不可用，使用系统建议值',
                '_suggestion': existing_suggestion
            }

    # ===== 分类处理 =====

    def clean_category(self, product_name: str,
                       entity_dict: dict,
                       cleaned_paths: dict,
                       category_options: dict,
                       brand: str = '',
                       product_paths: list = None) -> Dict:
        """补全分类 - AI 分析优先，AI 失败时 fallback 到本地算法"""
        from ..core.category_detector import CategoryDetector

        # 构建分类选项文本（来自 path_cleaner 处理后的结果）
        all_paths = []
        for l1 in category_options.get('level1', []):
            for l2 in category_options.get('level2_by_level1', {}).get(l1, []):
                for l3 in category_options.get('level3_by_level2', {}).get(f"{l1} > {l2}", []):
                    all_paths.append(f"{l1} > {l2} > {l3}")

        if not all_paths:
            return {'path': '', 'confidence': 0.0, 'factors': {}, 'needs_review': True, 'method': 'no_options', 'error': '无可用的分类路径'}

        # 过滤掉人工标记为营销的分类路径
        try:
            classified_file = Path(__file__).parent.parent / 'categories' / 'classified_paths.json'
            if classified_file.exists():
                with open(classified_file, 'r', encoding='utf-8') as _f:
                    _classified = json.load(_f)
                _marketing_paths = {p for p, label in _classified.items() if label == 'marketing'}
                all_paths = [p for p in all_paths if p not in _marketing_paths]
        except Exception:
            pass

        # 按 L1 分组排列（方便 AI 快速定位）
        grouped = {}
        for p in all_paths:
            l1 = p.split(' > ')[0]
            grouped.setdefault(l1, []).append(p)
        lines = []
        for l1 in sorted(grouped):
            lines.append(f"[{l1}]")
            for p in grouped[l1]:
                lines.append(f"  {p}")
        options_text = "\n".join(lines)

        if not all_paths:
            return {'path': '', 'confidence': 0.0, 'factors': {}, 'needs_review': True, 'method': 'no_options', 'error': '无可用的分类路径'}

        # 按 L1 分组组织选项文本，方便 AI 阅读理解
        grouped = {}
        for p in all_paths:
            l1 = p.split(' > ')[0]
            grouped.setdefault(l1, []).append(p)
        lines = []
        for l1 in sorted(grouped):
            lines.append(f"[{l1}]")
            for p in grouped[l1][:20]:  # 每个 L1 最多 20 条
                lines.append(f"  {p}")
        options_text = "\n".join(lines)
        error_msg = None

        # Step 1: 调 AI 分析分类
        brand_info = f"品牌: {brand}" if brand else "品牌: 未知"
        if product_paths:
            product_paths_info = "该商品已有的分类路径: " + ", ".join(product_paths)
        else:
            product_paths_info = "该商品暂无已有分类路径"
        prompt = CATEGORY_ANALYSIS_PROMPT.format(
            product_name=product_name,
            brand_info=brand_info,
            product_paths_info=product_paths_info,
            category_options=options_text
        )

        try:
            text = self._call_ai(prompt, max_tokens=300)
            data = self._parse_json(text)
            ai_path = data.get('path', '').strip()
            ai_confidence = float(data.get('confidence', 0.5))
            ai_factors = data.get('factors', {})

            # 验证 AI 返回的路径是否在可选路径中
            if ai_path and ai_path in all_paths:
                return {
                    'path': ai_path,
                    'confidence': ai_confidence,
                    'factors': ai_factors,
                    'needs_review': ai_confidence < 0.7,
                    'method': 'ai',
                    'error': None,
                    'reason': data.get('reason', f'AI 分类为 "{ai_path}"')
                }
            elif ai_path:
                # AI 返回的路径不在可选列表中 → 保留建议，标记待复核
                return {
                    'path': ai_path,
                    'confidence': min(ai_confidence, 0.4),
                    'factors': ai_factors,
                    'needs_review': True,
                    'method': 'ai_out_of_range',
                    'error': None,
                    'reason': data.get('reason', f'AI 建议分类 "{ai_path}"（当前可选路径中无直接匹配，建议人工确认）')
                }
            else:
                # AI 返回空路径，fallback
                raise Exception("AI 未返回有效分类路径")
        except Exception as e:
            error_msg = f"AI 分类推断失败: {self.last_error or str(e)}"
            logger.warning(f"AI category failed for '{product_name}': {error_msg}")

        # Step 2: AI 失败，优先从该商品已有路径中匹配
        path = ''
        confidence = 0.0
        factors = {}
        if product_paths:
            for pp in product_paths:
                if pp in all_paths:
                    path = pp
                    confidence = 0.7
                    break
        if not path:
            path, confidence, factors = CategoryDetector.suggest_category(
                product_name, category_options, cleaned_paths, entity_dict
            )
            confidence = confidence * 0.8

        return {
            'path': path,
            'confidence': confidence,
            'factors': factors or {},
            'needs_review': True,
            'method': 'local',
            'error': error_msg,
            'reason': 'AI 不可用，使用本地推算'
        }

    # ===== 组合分析（品牌+分类一次调用）=====

    def clean_product(self, product_name: str,
                      existing_suggestion: str = '',
                      entity_dict: dict = None,
                      cleaned_paths: dict = None,
                      category_options: dict = None,
                      brand: str = '',
                      product_paths: list = None) -> Dict:
        """一次 AI 调用同时提取品牌和分类"""
        from ..brands.database import find_any_brand, BRAND_DATABASE_V6, load_corrected_brands
        from ..core.category_detector import CategoryDetector

        name_lower = product_name.lower()

        # Step 0-2: 品牌库匹配（同 clean_brand）
        if existing_suggestion:
            corrected = load_corrected_brands().get(existing_suggestion)
            if corrected and corrected.get('corrected_to'):
                result = find_any_brand(corrected['corrected_to'])
                if result['found']:
                    info = BRAND_DATABASE_V6.get(result['standard_name'], {})
                    brand_result = {
                        'brand': result['standard_name'],
                        'brand_type': info.get('type', '') if isinstance(info, dict) else '',
                        'confidence': 0.95, 'from_library': True,
                        'needs_review': False, 'error': None,
                        'reason': f'品牌修正记录: "{existing_suggestion}" → "{result["standard_name"]}"',
                        '_suggestion': existing_suggestion
                    }
                    return self._build_combined(brand_result, None, product_name, existing_suggestion,
                                                entity_dict, cleaned_paths, category_options, product_paths)

        if existing_suggestion:
            result = find_any_brand(existing_suggestion)
            if result['found']:
                info = BRAND_DATABASE_V6.get(result['standard_name'], {})
                brand_result = {
                    'brand': result['standard_name'],
                    'brand_type': info.get('type', '') if isinstance(info, dict) else '',
                    'confidence': 0.95, 'from_library': True,
                    'needs_review': False, 'error': None,
                    'reason': f'品牌库匹配: {result["standard_name"]}',
                    '_suggestion': existing_suggestion
                }
                return self._build_combined(brand_result, None, product_name, existing_suggestion,
                                            entity_dict, cleaned_paths, category_options, product_paths)

        for brand_name, info in _get_brand_cache():
            if not isinstance(info, dict):
                continue
            if brand_name.lower() in name_lower:
                brand_result = {
                    'brand': brand_name,
                    'brand_type': info.get('type', ''),
                    'confidence': 0.9, 'from_library': True,
                    'needs_review': False, 'error': None,
                    'reason': f'品牌库扫描: "{brand_name}" 出现在商品名中',
                    '_suggestion': existing_suggestion
                }
                return self._build_combined(brand_result, None, product_name, existing_suggestion,
                                            entity_dict, cleaned_paths, category_options, product_paths)
            for alias in info.get('aliases', []):
                if isinstance(alias, str) and alias.lower() in name_lower:
                    brand_result = {
                        'brand': brand_name,
                        'brand_type': info.get('type', ''),
                        'confidence': 0.9, 'from_library': True,
                        'needs_review': False, 'error': None,
                        'reason': f'品牌库扫描: 别名"{alias}" 匹配 "{brand_name}"',
                        '_suggestion': existing_suggestion
                    }
                    return self._build_combined(brand_result, None, product_name, existing_suggestion,
                                                entity_dict, cleaned_paths, category_options, product_paths)

        # Step 3: 调 AI 一次性分析品牌+分类
        brand_info_text = f"品牌: {brand}" if brand else "品牌: 未知"
        if product_paths:
            product_paths_info = "该商品已有的分类路径: " + ", ".join(product_paths)
        else:
            product_paths_info = "该商品暂无已有分类路径"

        # 构建分类选项：有已有路径只给已有，无路径给 L1>L2:L3列表（省78%token）
        all_paths = []
        if category_options:
            for l1 in category_options.get('level1', []):
                for l2 in category_options.get('level2_by_level1', {}).get(l1, []):
                    for l3 in category_options.get('level3_by_level2', {}).get(f"{l1} > {l2}", []):
                        all_paths.append(f"{l1} > {l2} > {l3}")
        if not all_paths:
            return {'path': '', 'confidence': 0.0, 'factors': {}, 'needs_review': True, 'method': 'no_options', 'error': '无可用的分类路径'}

        # 加载营销路径黑名单
        marketing_set = set()
        try:
            cf = Path(__file__).parent.parent / 'categories' / 'classified_paths.json'
            if cf.exists():
                with open(cf, 'r', encoding='utf-8') as f:
                    cdata = json.load(f)
                marketing_set = {p for p, lbl in cdata.items() if lbl == 'marketing'}
        except Exception: pass

        if product_paths:
            # 有已有路径只展示已有，剔除营销
            clean_paths = [p for p in product_paths if p not in marketing_set]
            options_text = "\n".join(clean_paths) if clean_paths else "\n".join(product_paths)
        else:
            # 无已有路径给分组格式，剔除营销 L3
            grouped = {}
            for l1 in category_options.get('level1', []):
                for l2 in category_options.get('level2_by_level1', {}).get(l1, []):
                    l3s = category_options.get('level3_by_level2', {}).get(f"{l1} > {l2}", [])
                    if l3s:
                        l3s = [l3 for l3 in l3s if f"{l1} > {l2} > {l3}" not in marketing_set]
                        if l3s: grouped.setdefault(f"{l1} > {l2}", []).extend(l3s)
            options_text = "\n".join(k + ": " + ", ".join(v) for k, v in sorted(grouped.items()))

        prompt = COMBINED_PROMPT.format(
            product_name=product_name,
            brand_info=brand_info_text,
            product_paths_info=product_paths_info,
            category_options=f"可选分类:\n{options_text}"
        )

        try:
            text = self._call_ai(prompt, max_tokens=500)
            data = self._parse_json(text)

            # 品牌部分
            ai_brand = data.get('brand') or ''
            if not ai_brand or ai_brand.lower() == 'null':
                brand_result = {
                    'brand': existing_suggestion or '',
                    'brand_type': '',
                    'confidence': 0.5, 'from_library': False,
                    'needs_review': True, 'no_brand': True, 'error': None,
                    'reason': data.get('brand_reason', 'AI 判断该商品无品牌'),
                    '_suggestion': existing_suggestion
                }
            else:
                agrees = existing_suggestion and ai_brand.lower() == existing_suggestion.lower()
                result = find_any_brand(ai_brand)
                if result['found']:
                    info = BRAND_DATABASE_V6.get(result['standard_name'], {})
                    brand_result = {
                        'brand': result['standard_name'],
                        'brand_type': info.get('type', '') if isinstance(info, dict) else '',
                        'confidence': 0.95 if agrees else 0.9, 'from_library': True,
                        'needs_review': False, 'error': None,
                        'reason': data.get('brand_reason', f'AI 推断为 "{ai_brand}"，品牌库确认'),
                        '_suggestion': existing_suggestion, '_ai_agrees': agrees
                    }
                else:
                    brand_result = {
                        'brand': ai_brand,
                        'brand_type': data.get('brand_type', ''),
                        'confidence': 0.85 if agrees else data.get('brand_confidence', 0.7),
                        'from_library': False,
                        'needs_review': not agrees,
                        'error': None,
                        'reason': data.get('brand_reason', f'AI 推断为 "{ai_brand}"，不在品牌库中'),
                        '_suggestion': existing_suggestion, '_ai_agrees': agrees
                    }

            # 分类部分
            ai_path = data.get('path', '').strip()
            ai_cat_conf = float(data.get('cat_confidence', 0.5))
            ai_factors = data.get('factors', {})

            if ai_path and all_paths and ai_path in all_paths:
                cat_result = {
                    'path': ai_path, 'confidence': ai_cat_conf,
                    'factors': ai_factors,
                    'needs_review': ai_cat_conf < 0.7,
                    'method': 'ai', 'error': None,
                    'reason': data.get('cat_reason', f'AI 分类为 "{ai_path}"')
                }
            elif ai_path:
                cat_result = {
                    'path': ai_path, 'confidence': min(ai_cat_conf, 0.4),
                    'factors': ai_factors,
                    'needs_review': True, 'method': 'ai_out_of_range', 'error': None,
                    'reason': data.get('cat_reason', f'AI 建议 "{ai_path}"（不在可选路径中）')
                }
            else:
                raise Exception("AI 未返回有效分类路径")

        except Exception as e:
            error_msg = f"AI 分析失败: {self.last_error or str(e)}"
            logger.warning(f"clean_product failed for '{product_name}': {error_msg}")
            brand_result = {
                'brand': existing_suggestion or '',
                'brand_type': '', 'confidence': 0.0, 'from_library': False,
                'needs_review': True, 'error': error_msg,
                'reason': 'AI 不可用，使用系统建议值',
                '_suggestion': existing_suggestion
            }
            cat_result = self._cat_fallback(product_name, entity_dict, cleaned_paths, category_options,
                                            product_paths, all_paths, error_msg)

        return {'brand': brand_result, 'category': cat_result}

    def _build_combined(self, brand_result, cat_result, product_name, existing_suggestion,
                        entity_dict, cleaned_paths, category_options, product_paths):
        """当品牌库命中时，仍需处理分类（要么AI要么fallback）"""
        all_paths = []
        if category_options:
            for l1 in category_options.get('level1', []):
                for l2 in category_options.get('level2_by_level1', {}).get(l1, []):
                    for l3 in category_options.get('level3_by_level2', {}).get(f"{l1} > {l2}", []):
                        all_paths.append(f"{l1} > {l2} > {l3}")

        if product_paths:
            product_paths_info = "该商品已有的分类路径: " + ", ".join(product_paths)
        else:
            product_paths_info = "该商品暂无已有分类路径"

        # 加载营销黑名单
        marketing_set = set()
        try:
            cf = Path(__file__).parent.parent / 'categories' / 'classified_paths.json'
            if cf.exists():
                with open(cf, 'r', encoding='utf-8') as f:
                    cdata = json.load(f)
                marketing_set = {p for p, lbl in cdata.items() if lbl == 'marketing'}
        except Exception: pass

        if product_paths:
            clean = [p for p in product_paths if p not in marketing_set]
            options_text = "\n".join(clean) if clean else "\n".join(product_paths)
        else:
            grouped = {}
            for l1 in category_options.get('level1', []):
                for l2 in category_options.get('level2_by_level1', {}).get(l1, []):
                    l3s = category_options.get('level3_by_level2', {}).get(f"{l1} > {l2}", [])
                    if l3s:
                        l3s = [l3 for l3 in l3s if f"{l1} > {l2} > {l3}" not in marketing_set]
                        if l3s: grouped.setdefault(f"{l1} > {l2}", []).extend(l3s)
            options_text = "\n".join(k + ": " + ", ".join(v) for k, v in sorted(grouped.items()))
        brand_info_text = f"品牌: {brand_result.get('brand', '')}"

        prompt = CATEGORY_ANALYSIS_PROMPT.format(
            product_name=product_name,
            brand_info=brand_info_text,
            product_paths_info=product_paths_info,
            category_options=options_text
        )
        try:
            text = self._call_ai(prompt, max_tokens=300)
            data = self._parse_json(text)
            ai_path = data.get('path', '').strip()
            ai_conf = float(data.get('confidence', 0.5))
            ai_factors = data.get('factors', {})
            if ai_path and all_paths and ai_path in all_paths:
                cat_result = {
                    'path': ai_path, 'confidence': ai_conf,
                    'factors': ai_factors,
                    'needs_review': ai_conf < 0.7, 'method': 'ai', 'error': None,
                    'reason': data.get('reason', f'AI 分类为 "{ai_path}"')
                }
            elif ai_path:
                cat_result = {
                    'path': ai_path, 'confidence': min(ai_conf, 0.4),
                    'factors': ai_factors,
                    'needs_review': True, 'method': 'ai_out_of_range', 'error': None,
                    'reason': data.get('reason', f'AI 建议 "{ai_path}"（不在可选路径中）')
                }
            else:
                raise Exception("AI 未返回有效分类路径")
        except Exception as e:
            error_msg = f"AI 分类推断失败: {self.last_error or str(e)}"
            logger.warning(f"Category AI failed for '{product_name}': {error_msg}")
            cat_result = self._cat_fallback(product_name, entity_dict, cleaned_paths, category_options,
                                            product_paths, all_paths, error_msg)

        return {'brand': brand_result, 'category': cat_result}

    def _cat_fallback(self, product_name, entity_dict, cleaned_paths, category_options,
                      product_paths, all_paths, error_msg):
        """分类 fallback：先匹配已有路径，再本地推算"""
        from ..core.category_detector import CategoryDetector
        if product_paths and all_paths:
            for pp in product_paths:
                if pp in all_paths:
                    return {
                        'path': pp, 'confidence': 0.7, 'factors': {},
                        'needs_review': True, 'method': 'local', 'error': error_msg,
                        'reason': 'AI 不可用，使用本地推算'
                    }
        path, confidence, factors = CategoryDetector.suggest_category(
            product_name, category_options, cleaned_paths, entity_dict
        )
        return {
            'path': path, 'confidence': confidence * 0.8,
            'factors': factors or {},
            'needs_review': True, 'method': 'local', 'error': error_msg,
            'reason': 'AI 不可用，使用本地推算'
        }

    # ===== 批量处理 =====

    def process_batch(self, items: List[Dict],
                      fields: List[str] = None,
                      entity_dict: dict = None,
                      cleaned_paths: dict = None,
                      category_options: dict = None,
                      progress_callback=None) -> List[Dict]:
        """批量处理，按字段粒度处理"""
        if fields is None:
            fields = ['brand', 'category']
        results = []

        for idx, item in enumerate(items):
            result = {
                'code': item.get('code', ''),
                'name': item.get('name', ''),
                'brand': {'status': 'skipped', 'value': item.get('brand', '') or '', 'confidence': 1.0, 'error': None},
                'category': {'status': 'skipped', 'path': item.get('category', '') or '', 'confidence': 1.0, 'factors': {}, 'error': None},
                'needs_review': False
            }

            # 只要该商品有任何字段需要 AI，品牌和分类一次调用同时分析
            needs_any_ai = item.get('needs_brand_ai') or item.get('needs_category_ai')

            if needs_any_ai and ('brand' in fields or 'category' in fields):
                combined = self.clean_product(
                    item.get('name', ''),
                    existing_suggestion=item.get('existing_suggestion', ''),
                    entity_dict=entity_dict,
                    cleaned_paths=cleaned_paths,
                    category_options=category_options,
                    brand=item.get('brand', ''),
                    product_paths=item.get('all_category_paths', [])
                )

                # 品牌
                brand_result = combined.get('brand', {})
                is_from_lib = brand_result.get('from_library', False)
                has_error = brand_result.get('error') is not None
                is_no_brand = brand_result.get('no_brand', False)
                status = 'no_brand' if is_no_brand else (
                    'from_library' if is_from_lib else ('error' if has_error else 'ai_ok')
                )
                result['brand'] = {
                    'status': status,
                    'value': brand_result.get('brand', ''),
                    'brand_type': brand_result.get('brand_type', ''),
                    'confidence': brand_result.get('confidence', 0.0),
                    'needs_review': brand_result.get('needs_review', True),
                    'error': brand_result.get('error'),
                    'suggestion': brand_result.get('_suggestion', ''),
                    'ai_agrees': brand_result.get('_ai_agrees', None),
                    'no_brand': is_no_brand,
                    'reason': brand_result.get('reason', '')
                }
                if brand_result.get('needs_review'):
                    result['needs_review'] = True

                # 分类
                cat_result = combined.get('category', {})
                result['category'] = {
                    'status': 'ai_ok' if cat_result.get('method', '').startswith('ai') else ('out_of_range' if cat_result.get('method') == 'ai_out_of_range' else 'local_fallback'),
                    'path': cat_result.get('path', ''),
                    'confidence': cat_result.get('confidence', 0.0),
                    'factors': cat_result.get('factors', {}),
                    'method': cat_result.get('method', ''),
                    'needs_review': cat_result.get('needs_review', True),
                    'error': cat_result.get('error'),
                    'reason': cat_result.get('reason', '')
                }
                if cat_result.get('needs_review'):
                    result['needs_review'] = True
                result['_tokens'] = self.last_usage
                result['_prompt'] = self.last_prompt

            results.append(result)

            if progress_callback:
                progress_callback(idx + 1, len(items), result)

        return results
