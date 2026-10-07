"""Ask Claude to review the portfolio snapshot and write a Chinese report."""

import json

import anthropic

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """你是一位谨慎、务实的投资组合分析助手，为一位使用 Trading 212 Stocks ISA 账户的英国个人投资者撰写每日收盘后的持仓简报。

报告会以纯文本形式推送到手机上的 Telegram，因此：
- 不要使用 Markdown 语法（不要用 #、**、表格），可以用 emoji 和短横线列表来分段。
- 控制在约 600 个汉字以内，先给结论，再给细节。
- 金额保留两位小数并标注币种，百分比保留一位小数。

报告结构：
1. 今日概览：总资产、当日变动（如果有上一次快照）、累计浮动盈亏。
2. 值得关注的持仓：涨跌幅最大或权重最大的几只，用网络搜索查一下它们最近的新闻、财报或评级变化，简要说明原因。
3. 风险提示：仓位集中度（单只超过 20%、前五大合计等）、行业或地区过度集中、现金比例是否过高或过低。
4. 建议：给出 1 到 3 条具体、可执行的观察或调仓思路，说明理由；如果今天没有需要做的事，就直接说"维持现状"。

Stocks ISA 内的资本利得和股息在英国免税，不要建议与此相悖的税务操作。所有建议都只是参考，结尾用一句话提醒这不构成投资建议。"""


def write_report(snapshot: dict, changes: dict | None, investor_profile: str = "") -> str:
    client = anthropic.Anthropic()

    payload = {"snapshot": snapshot, "changes_since_last_run": changes}
    user_text = "以下是我的 Trading 212 Stocks ISA 账户最新数据（JSON）：\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    if investor_profile:
        user_text += "\n\n我的投资背景和偏好：\n" + investor_profile
    if changes is None:
        user_text += "\n\n这是第一次运行，没有上一次的快照可以对比。"

    messages = [{"role": "user", "content": user_text}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}]

    # Server-side web search can pause a long turn; resend to let it continue.
    for _ in range(4):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=tools,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to write the report (stop_reason=refusal)")

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise RuntimeError(f"Claude returned no report text (stop_reason={response.stop_reason})")
    return text
