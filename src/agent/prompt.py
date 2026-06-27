"""
src/agent/prompt.py —— System Prompt 拼装

根据 config 的 agent 节动态生成 system prompt，
无需硬编码——所有规则通过 config.json 的开关控制。
"""


def build_system_prompt(cfg: dict) -> str:
    """根据 agent 配置动态拼装 system prompt"""
    agent_cfg = cfg["agent"]

    # 基础检索规则
    lines = [
        "你是 DST Mod 开发知识库助手。严格按以下规则工作：",
        "",
        "## 检索规则",
        "1. 收到用户问题后，必须先调用 search_knowledge_base 工具",
        "2. **最多调用 3 次工具**。超过后必须基于已有信息直接回答",
        "3. 连续 2 次检索返回相同内容 = 知识库已穷尽，立刻停止检索",
        "4. 工具返回的是知识库中实际存在的代码片段，请严格引用",
        "",
        "## 回答规则",
    ]

    if agent_cfg.get("allow_external_knowledge", False):
        lines += [
            "5. 知识库信息不足时，可用你自己的 DST Mod 知识补充",
            "6. 补充部分必须明确标注「（以下为补充知识）」并解释为什么知识库没有覆盖",
        ]
    else:
        lines += [
            "5. 知识库信息不足时，直接说「抱歉，当前知识库中没有足够的相关信息」",
            "6. 绝对禁止编造知识库中没有的信息",
        ]

    extra = agent_cfg.get("system_prompt_extra", "").strip()
    if extra:
        lines.append(f"\n补充规则：{extra}")

    return "\n".join(lines)
