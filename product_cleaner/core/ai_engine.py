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
    import google.generativeai as genai
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

CATEGORY_ANALYSIS_PROMPT = """你是一个电商商品分类专家。请分析以下商品的分类信息，**必须**从下方提供的可选路径中选择一个。

商品名称: {product_name}
{brand_info}

===== 可选的标准化分类路径（必须从以下列表中选择一条）=====
{category_options}
====================================================

要求（请严格遵守）：
1. **必须**从上方列表中选择一条路径，不要自己编造
  1.2 如果列表中没有完全匹配的路径，选择商品品类或者品种上最接近的
  1.2 如果列表中有多个路径，先找出最优秀的路径，路径本身分类由总到分，由粗到细，一级到三级都是相同或类似的命名，反而不是最优路径。
2. 寻找匹配分类的优先判断是从三级向前去找，以三级最优、二级和一级合理即可
3. 核心品类词（entity）以及(fators)是决定三级分类的关键，如果entity与你分析的不一致，也可不参考
5. 品牌类型（brand_type）辅助判断一级分类
6. 如果商品的多条路径中有营销分类路径，不要去选，哪怕他多路径都不符合，也要选择最接近实际的标准分类
7. 置信度低于 0.7 时设置 needs_review=true

返回 JSON（只返回 JSON，不要其他文字）：
{{
  "path": "一级 > 二级 > 三级",
  "confidence": 0.0-1.0,
  "reason": "选择理由",
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
                 model_id: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key or ''
        if not self.api_key:
            raise ValueError("未提供 API Key，请在页面中填写")
        self.call_count = 0
        self.model_id = model_id or self._default_model()
        self.client = self._init_client()
        self.last_error = None  # 最后一次 AI 调用错误

    def _default_model(self) -> str:
        models = {
            'gemini': 'models/gemini-2.0-flash',
            'claude': 'claude-3-haiku-20240307',
            'openai': 'gpt-4o-mini',
            'deepseek': 'deepseek-chat',
        }
        return models.get(self.provider, 'models/gemini-2.0-flash')

    def _init_client(self):
        p = self.provider
        key = self.api_key

        if p == 'gemini':
            if not HAS_GENAI:
                raise ImportError("请安装 google-generativeai: pip install google-generativeai")
            genai.configure(api_key=key)
            return genai.GenerativeModel(self.model_id)

        elif p == 'claude':
            if not HAS_ANTHROPIC:
                raise ImportError("请安装 anthropic: pip install anthropic")
            return anthropic.Anthropic(api_key=key)

        elif p in ('openai', 'deepseek'):
            if not HAS_OPENAI:
                raise ImportError("请安装 openai: pip install openai")
            base_url = 'https://api.deepseek.com' if p == 'deepseek' else 'https://api.openai.com/v1'
            return OpenAI(api_key=key, base_url=base_url)

        else:
            raise ValueError(f"不支持的 provider: {p}")

    def _call_ai(self, prompt: str, max_tokens: int = 500) -> str:
        """调用 AI 并返回文本响应"""
        p = self.provider
        self.last_error = None

        try:
            if p == 'gemini':
                response = self.client.generate_content(prompt)
                if not response.text:
                    raise Exception("Gemini 返回了空内容")
                return response.text

            elif p == 'claude':
                response = self.client.messages.create(
                    model=self.model_id,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            elif p in ('openai', 'deepseek'):
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
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
                'reason': error_msg,
                '_suggestion': existing_suggestion
            }

    # ===== 分类处理 =====

    def clean_category(self, product_name: str,
                       entity_dict: dict,
                       cleaned_paths: dict,
                       category_options: dict,
                       brand: str = '') -> Dict:
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
        prompt = CATEGORY_ANALYSIS_PROMPT.format(
            product_name=product_name,
            brand_info=brand_info,
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

        # Step 2: AI 失败，fallback 到本地算法
        path, confidence, factors = CategoryDetector.suggest_category(
            product_name, category_options, cleaned_paths, entity_dict
        )

        return {
            'path': path,
            'confidence': confidence * 0.8,
            'factors': factors or {},
            'needs_review': True,
            'method': 'rule_fallback',
            'error': error_msg,
            'reason': f'AI 失败，本地规则 fallback: {path or "无匹配"}'
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

            # 只要该商品有任何字段需要 AI，品牌和分类都一起分析
            needs_any_ai = item.get('needs_brand_ai') or item.get('needs_category_ai')

            if 'brand' in fields and needs_any_ai:
                brand_result = self.clean_brand(
                    item.get('name', ''),
                    existing_suggestion=item.get('existing_suggestion', '')
                )
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

            # 分类（与品牌同上，needs_any_ai 即任一字段需要就一起分析）
            if 'category' in fields and needs_any_ai:
                cat_result = self.clean_category(
                    item.get('name', ''),
                    entity_dict or {},
                    cleaned_paths or {},
                    category_options or {},
                    brand=result['brand'].get('value', '')
                )
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

            results.append(result)

            if progress_callback:
                progress_callback(idx + 1, len(items), result)

        return results
