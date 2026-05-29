"""
Agent 循环：看 → 想 → 动

流程：
  1. 用户发消息
  2. LLM 决定：直接回复还是调工具
  3. 调工具 → 结果喂回 LLM → 再决定
  4. 重复直到 LLM 直接回复用户
"""

import json
import logging
from typing import Callable, Optional

from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

# 最大循环次数，防止无限递归
MAX_ITERATIONS = 20

SYSTEM_PROMPT = """你是一个数据处理系统的 AI 助手。你有以下工具可用：

{tools_desc}

你的工作方式：
1. 用户提出需求后，先思考需要哪些数据
2. 调 read_* 工具获取数据
3. 根据数据决定下一步操作：调 ai_* 做判断，或调 execute_* 执行
4. 全部完成 → 给用户总结报告
5. 有不确定的 → 告诉用户具体情况，让用户决定

每次只调一个工具。调完工具后，我看结果再决定下一步。

如果你认为不需要调工具，直接回复用户。
如果你认为需要用户确认，直接告诉用户，不要擅自执行。
"""


def call_tool_loop(llm_call: Callable[[str], str],
                    user_message: str,
                    session_id: str = "",
                    conversation_history: list = None,
                    ui_context: dict = None) -> dict:
    """
    Agent 循环入口。

    参数：
      llm_call: call(prompt) → LLM 回复文本
      user_message: 用户输入
      session_id: 当前会话 ID（可选）
      conversation_history: 历史消息 [{role, content}]

    返回：
      {"reply": "最终回复", "actions": [...], "summary": {...}}
    """
    tools_desc = _build_tools_desc()
    history = conversation_history or []
    messages = _build_messages(SYSTEM_PROMPT.format(tools_desc=tools_desc),
                                 history, user_message, session_id)

    # Inject UI context if provided (front-end component selection)
    if ui_context:
        selected = ui_context.get("selected_item", "")
        panel = ui_context.get("current_panel", "")
        if selected or panel:
            ctx_line = "[上下文] 用户当前在页面选中了：{}{}".format(
                selected or "(无具体项)",
                "（" + panel + " 面板）" if panel else ""
            )
            messages.insert(0, {"role": "system", "content": ctx_line})

    all_actions = []

    for iteration in range(MAX_ITERATIONS):
        # 调 LLM
        prompt = _format_messages(messages)
        try:
            reply = llm_call(prompt + "\n\n请输出 JSON（只输出 JSON）：\n")
        except Exception as e:
            return {"reply": f"AI 调用失败: {e}", "actions": all_actions}

        # 解析回复
        parsed = _parse_reply(reply)
        if parsed is None:
            # 不是 JSON，当做自然语言回复 → 结束
            return {"reply": reply, "actions": all_actions}

        tool_name = parsed.get("tool")
        if not tool_name:
            # LLM 决定直接回复
            return {"reply": parsed.get("reply", reply), "actions": all_actions}

        # LLM 要调工具
        tool_args = parsed.get("arguments", {})

        # 自动注入 session_id
        if session_id and "session_id" not in tool_args:
            # 检查工具是否接受 session_id 参数
            try:
                tool = ToolRegistry._tools.get(tool_name)
                if tool and hasattr(tool, "input_schema"):
                    props = tool.input_schema.get("properties", {})
                    if "session_id" in props:
                        tool_args["session_id"] = session_id
            except Exception:
                pass

        # 注入 llm_call（如果工具需要）
        try:
            tool = ToolRegistry._tools.get(tool_name)
            import inspect
            sig = inspect.signature(tool.execute) if tool else None
            if sig and "llm_call" in sig.parameters:
                tool_args["llm_call"] = llm_call
        except Exception:
            pass

        # 执行
        try:
            result = ToolRegistry.call(tool_name, **tool_args)
        except Exception as e:
            result = {"error": str(e)}

        all_actions.append({"tool": tool_name, "arguments": tool_args, "result": result})

        # 把工具执行结果加入消息历史
        messages.append({
            "role": "assistant",
            "content": f"调用了 {tool_name}，结果为：{json.dumps(result, ensure_ascii=False, default=str)[:2000]}"
        })
        messages.append({
            "role": "user",
            "content": "继续。如果完成了就直接回复我，如果需要我确认什么就告诉我。"
        })

    return {"reply": "处理超时，请重试或分解问题", "actions": all_actions}


def _build_tools_desc() -> str:
    """生成工具描述列表"""
    tools = ToolRegistry.list_tools()
    lines = []
    for t in tools:
        lines.append(f"- {t['name']}: {t['description']}")
    return "\n".join(lines)


def _build_messages(system_prompt: str, history: list,
                    user_message: str, session_id: str) -> list:
    """构建 LLM 消息列表"""
    msgs = [{"role": "system", "content": system_prompt}]

    # 如果有 session_id
    if session_id:
        msgs.append({
            "role": "system",
            "content": f"当前会话 ID: {session_id}。需要数据时用 read_* 工具读取。"
        })

    # 历史消息
    for h in history[-10:]:  # 只取最近 10 条
        msgs.append({"role": h.get("role", "user"), "content": h.get("content", "")})

    msgs.append({"role": "user", "content": user_message})
    return msgs


def _format_messages(messages: list) -> str:
    """把消息列表格式化成 LLM 输入"""
    parts = []
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            parts.append(f"[系统]: {content}")
        elif role == "user":
            parts.append(f"[用户]: {content}")
        elif role == "assistant":
            parts.append(f"[助手]: {content}")
    return "\n\n".join(parts)


def _parse_reply(text: str) -> Optional[dict]:
    """尝试从 LLM 回复中解析 JSON"""
    text = text.strip()
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试从 ```json 块中提取
    if "```json" in text:
        try:
            block = text.split("```json")[1].split("```")[0].strip()
            return json.loads(block)
        except (IndexError, json.JSONDecodeError):
            pass
    # 尝试从 ``` 块中提取
    if "```" in text:
        try:
            block = text.split("```")[1].split("```")[0].strip()
            return json.loads(block)
        except (IndexError, json.JSONDecodeError):
            pass
    return None
