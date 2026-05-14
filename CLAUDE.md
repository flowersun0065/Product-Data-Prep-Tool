# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A product data cleaning and standardization tool for grocery/supermarket product catalogs. It processes Excel files with product records, auto-completing missing brands, extracting product specs, standardizing category taxonomies, and detecting data quality issues. Uses AI models (Claude/Gemini/OpenAI/DeepSeek) as fallback for unresolvable cases.

## Commands

- **Start web server**: `python run_server.py` (serves at http://localhost:5001)
- **Run CLI directly**: `python -m product_cleaner.web.app`
- **Install deps**: `pip install anthropic pandas openpyxl flask flask-cors`
- **Optional AI providers**: `pip install google-generativeai openai`
- **Set API key**: `export ANTHROPIC_API_KEY="sk-..."`

## Project Structure

```
product_cleaner/
  constants.py         # Base paths, regex patterns, AI config thresholds
  web/app.py           # Flask server (~2100 lines): routes, session mgmt, file upload, async AI processing
  core/
    product_parser.py  # Low-level text extraction: spec extraction (weight+pack split), entity recognition, brand/noise stripping, classify_word() lookup
    brand_checker.py   # Brand consistency: 3-tier extraction + confidence scoring
    brand_cluster.py   # Brand clustering: groups similar brand names, identifies missing/mismatched
    category_detector.py  # Category analysis: marketing detection, conflict resolution, suggestion engine (uses SpecExtractor, classify_word, CATEGORY_GROUP_CN)
    ai_engine.py       # AI provider abstraction (Gemini/Claude/OpenAI/DeepSeek) for brand+category completion
    standardization.py # Applies brand/category editing rules to DataFrames
    cache.py           # JSON-file based cache for AI results, review decisions, rules
    lexicon.py         # ~570 lines: NOT_BRAND_CATEGORIES, SPEC_UNITS, WEIGHT_UNITS, PACK_UNITS, CATEGORY_GROUP_CN, dual-meaning brands
  brands/
    database.py        # Brand database V6 (~2000 lines): BRAND_DATABASE_V6 dict + dynamic persistence
    patterns.py        # Slash brand pattern matching (e.g. "Lay's/乐事")
  categories/
    path_cleaner.py    # Category path cleaning algorithm (marketing removal, hierarchy merging, convergence)
    classified_paths.py # Persistence for user-labeled marketing/standard path flags
    marketing_keywords.py # Keywords used to detect marketing-oriented categories
  templates/
    html_templates.py  # All HTML/CSS/JS inline (~12K lines, single file)
  static/js/           # Frontend JS modules: upload, diagnosis, brand_editor, ai_process, export
```

## Architecture

- **Layered separation**: `product_parser.py` has zero business logic (no brand/category decisions), serving as pure text extraction utility consumed by all engine modules
- **No circular deps**: `lexicon.py` → `product_parser.py` → `brand_checker.py`/`brand_cluster.py`/`category_detector.py` → `app.py`
- **Session-based async processing**: Each upload creates a session with async diagnosis (brand clustering + category analysis) and optional async AI batch processing (with cancellation support)
- **Brand processing pipeline**: (1) Brand column check → (2) BrandConsistencyChecker.check() for validity → (3) BrandClusterEngine.cluster() for grouping → (4) AI or local extraction for missing brands
- **Category processing pipeline**: (1) Raw paths collected per product code → (2) path_cleaner removes marketing paths, merges variants → (3) Cleaned paths used as suggestions → (4) Missing items get entity-based recommendation
- **Persistence model**: Session snapshots (`session_snapshots.json`), brand correction history (`corrected_products.json`), AI cache (`ai_cache_v4.json`), dismissed brands, all stored as JSON files in `cache/` or alongside code

## Key Patterns

- `StandardizationEngine.apply_rules()` mutates DataFrames in place using brand/category rules dicts
- `CacheManager` uses atomic write (`write tmp → os.replace`) for thread safety
- `diagnose_async()` and `process_file_async()` run in background threads with session-level locks
- `infer_brand_metadata()` uses heuristic country/type detection for new brand candidates
- `build_entity_dict()` identifies product entity words by analyzing name suffixes across all products

## Rules

- When modifying algorithm logic (brand extraction, clustering, category detection, path cleaning, AI prompts), update the corresponding documentation in `DIAGNOSIS_RULES.md` to keep references in sync.
- When module dependencies or interface relationships change (e.g., adding/removing imports between core modules), update `core/CALL_GRAPH.md`.
- Keep `CLAUDE.md` itself up to date when the project structure or architecture changes significantly.

## AI Integration

- Supports Gemini (default), Claude, OpenAI, DeepSeek
- `ProductCleanerEngine` (`ai_engine.py`) handles brand via prompt `BRAND_PROMPT` and category via `CATEGORY_ANALYSIS_PROMPT`
- Brand processing: library lookup first → AI fallback → confidence scoring
- Category processing: AI analysis first → fallback to local `CategoryDetector.suggest_category()` rule engine
- All brand/classifier logic, prompts, and heuristics are embedded in Python source code
