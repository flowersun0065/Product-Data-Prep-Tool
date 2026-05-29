"""
Agent API 路由。

在 app.py register_routes() 中调：
  from ..agent.routes_agent import register_agent_routes
  register_agent_routes(app)
"""

import json
import logging

from flask import jsonify, request

from .conversation_store import (
    init_db, create_conversation, get_conversation, list_conversations,
    add_message, get_messages, update_conversation,
)
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_agent_routes(app):
    init_db()

    # ── 注册所有 Agent 工具（import 即注册） ──
    from .tools.tool_read_system_catalog import ToolReadSystemCatalog
    from .tools.tool_read_sessions_list import ToolReadSessionsList
    from .tools.tool_read_diagnosis_result import ToolReadDiagnosisResult
    from .tools.tool_read_new_brands import ToolReadNewBrands
    from .tools.tool_read_brand_library import ToolReadBrandLibrary
    from .tools.tool_read_brand_types import ToolReadBrandTypes
    from .tools.tool_read_countries import ToolReadCountries
    from .tools.tool_ai_confirm_brands import ToolAIReviewNewBrands
    from .tools.tool_ai_summarize import ToolAISummarize
    from .tools.tool_execute_python import ToolExecutePython
    from .tools.tool_execute_brand_actions import ToolExecuteBrandActions
    logger.info(f"Agent 工具已注册: {len(ToolRegistry.list_tools())} 个")

    # ── API ──

    @app.route("/api/agent/catalog")
    def agent_catalog():
        """系统目录 + 角色设定，外部可访问"""
        from .tools.tool_read_system_catalog import ToolReadSystemCatalog
        return jsonify(ToolReadSystemCatalog().execute())

    @app.route("/api/agent/conversations", methods=["GET"])
    def agent_list_conversations():
        """对话列表"""
        convs = list_conversations()
        return jsonify({"conversations": convs})

    @app.route("/api/agent/conversations", methods=["POST"])
    def agent_create_conversation():
        """新建对话"""
        data = request.json or {}
        title = data.get("title", "")
        session_id = data.get("session_id", "")
        cid = create_conversation(title=title, session_id=session_id)
        return jsonify({"conversation_id": cid})

    @app.route("/api/agent/conversations/<conversation_id>", methods=["GET"])
    def agent_get_conversation(conversation_id):
        """读取对话详情 + 消息历史"""
        conv = get_conversation(conversation_id)
        if not conv:
            return jsonify({"error": "对话不存在"}), 404
        msgs = get_messages(conversation_id)
        conv["messages"] = msgs
        return jsonify(conv)

    @app.route("/api/agent/conversations/<conversation_id>/chat", methods=["POST"])
    def agent_chat(conversation_id):
        """发消息 + 触发 Agent 循环"""
        conv = get_conversation(conversation_id)
        if not conv:
            return jsonify({"error": "对话不存在"}), 404

        data = request.json or {}
        message = data.get("message", "").strip()
        session_id = data.get("session_id") or conv.get("current_session_id", "")
        context = data.get("context") or {}
        ui_context = data.get("ui_context") or context  # support both names

        if not message:
            return jsonify({"error": "消息不能为空"}), 400

        # 存用户消息
        add_message(conversation_id, "user", message)

        # 初始化 AI 引擎
        from ..core.ai_engine import ProductCleanerEngine
        try:
            settings = _load_settings()
            ai_configs = settings.get("ai_configs", [])
            if ai_configs:
                api_key = ai_configs[0].get("api_key") or settings.get("api_key", "")
                provider = ai_configs[0].get("provider") or settings.get("ai_provider", "gemini")
                model_id = ai_configs[0].get("model") or settings.get("model_id", "")
            else:
                api_key = settings.get("api_key", "")
                provider = settings.get("ai_provider", "gemini")
                model_id = settings.get("model_id", "")

            engine = ProductCleanerEngine(
                api_key=api_key or "",
                provider=provider or "gemini",
                model_id=model_id,
            )
        except Exception as e:
            error_msg = f"AI 引擎初始化失败: {e}"
            add_message(conversation_id, "assistant", error_msg)
            return jsonify({"reply": error_msg})

        # 加载历史消息
        history = get_messages(conversation_id)
        history_msgs = []
        for m in history:
            if m.get("role") in ("user", "assistant"):
                history_msgs.append({"role": m["role"], "content": m.get("content", "")})

        # 更新 session_id
        if session_id and session_id != conv.get("current_session_id"):
            update_conversation(conversation_id, session_id=session_id)

        # 执行 Agent 循环
        from .agent_loop import call_tool_loop
        try:
            result = call_tool_loop(
                llm_call=lambda prompt: engine._call_ai(prompt, max_tokens=2000),
                user_message=message,
                session_id=session_id,
                conversation_history=history_msgs[:-1],
                ui_context=ui_context,
            )
        except Exception as e:
            result = {"reply": f"处理失败: {e}", "actions": []}

        reply = result.get("reply", "")
        actions = result.get("actions", [])

        # 存 AI 回复
        add_message(conversation_id, "assistant", reply, tool_calls=actions)

        return jsonify({
            "reply": reply,
            "actions": actions,
        })


def _load_settings() -> dict:
    """读取 settings.json"""
    import json as _json
    from pathlib import Path as _Path
    base = _Path(__file__).parent.parent
    for p in [base / "cache" / "settings.json"]:
        if p.exists():
            try:
                return _json.load(open(p))
            except Exception:
                pass
    return {}
