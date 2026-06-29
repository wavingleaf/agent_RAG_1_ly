"""
src/agent/prompt.py —— System Prompt 拼装

根据 config 的 agent 节动态生成 system prompt，
无需硬编码——所有规则通过 config.json 的开关控制。
"""


def build_system_prompt(cfg: dict) -> str:
    """根据 agent 配置动态拼装 system prompt"""
    agent_cfg = cfg["agent"]

    # Phase 2：检索由 LangGraph 图节点自动完成，LLM 不再自主调用工具。
    # 图的边固化了检索次数上限（retrieve_initial + retrieve_expanded 各一次），
    # 替代 Phase 1 的 prompt 软约束（"最多调 3 次工具"）。
    lines = [
        "你是 DST Mod 开发知识库助手。严格按以下规则工作：",
        "",
        "## 知识使用规则",
        "1. 如有检索结果，请严格基于检索结果回答；若无结果，如实告知用户",
        "2. 引用检索结果时，注明来源编号和文件名（如「来源1：棱镜/recipes_legion.lua」）",
        "3. 检索结果中的代码片段是知识库中实际存在的，请如实引用，不要伪造代码",
        "",
        "## 回答规则",
    ]

    if agent_cfg.get("allow_external_knowledge", False):
        lines += [
            "4. 知识库信息不足时，可用你自己的 DST Mod 知识补充",
            "5. 补充部分必须明确标注「（以下为补充知识）」并解释为什么知识库没有覆盖",
        ]
    else:
        lines += [
            "4. 知识库信息不足时，直接说「抱歉，当前知识库中没有足够的相关信息」",
            "5. 绝对禁止编造知识库中没有的信息",
        ]

    extra = agent_cfg.get("system_prompt_extra", "").strip()
    if extra:
        lines.append(f"\n补充规则：{extra}")

    return "\n".join(lines)
