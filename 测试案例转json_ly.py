"""
测试案例转json_ly.py —— 将测试案例_ly.md 转为 测试案例_ly.json

用法：
    python 测试案例转json_ly.py                  # md → json
    python 测试案例转json_ly.py --reverse          # json → md（更新 md 中的答案和评价）

人类编辑 md，脚本产出 json。json 供 LangSmith 等自动化工具取用。
"""

import json
import re
import sys
from pathlib import Path

# Windows 终端可能使用 GBK 编码，强制 stdout 用 UTF-8（避免 emoji 报错）
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).resolve().parent
MD_PATH = PROJECT_DIR / "测试案例_ly.md"
JSON_PATH = PROJECT_DIR / "测试案例_ly.json"


def md_to_json():
    """从 Markdown 解析测试案例，返回 JSON 数据列表"""
    text = MD_PATH.read_text(encoding="utf-8")
    records = []

    # 按 --- 分割各条目（跳过文件头）
    sections = re.split(r"\n---\n", text)

    for section in sections:
        # 提取问题：## N. 问题标题
        q_match = re.search(r"^## \d+\.\s*(.+)", section, re.MULTILINE)
        if not q_match:
            continue
        question = q_match.group(1).strip()

        # 提取答案：<details>...</details> 内的内容
        # re.DOTALL 让 . 匹配换行符
        a_match = re.search(r"<details>\s*<summary>.*?</summary>\s*(.*?)</details>", section, re.DOTALL)
        if a_match:
            answer = a_match.group(1).strip()
        else:
            answer = ""

        # 提取评价：### 评价 之后的内容（到下一个 --- 或文件尾）
        e_match = re.search(r"^### 评价\s*\n(.*?)(?=\n---\n|\Z)", section, re.DOTALL | re.MULTILINE)
        if e_match:
            evaluation = e_match.group(1).strip()
        else:
            evaluation = ""

        records.append({"问题": question, "答案": answer, "用户评价": evaluation})

    return records


def json_to_md():
    """将 JSON 中的答案和评价写回 Markdown（保留手工编辑的问题和期望）"""
    if not JSON_PATH.exists():
        print("❌ 测试案例_ly.json 不存在，请先运行 md→json 方向的转换")
        sys.exit(1)

    records = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    text = MD_PATH.read_text(encoding="utf-8")

    for i, rec in enumerate(records):
        # 找到第 i+1 个 <details> 块，替换其内容
        # 策略：逐条匹配 ## N. 标题，找到后替换该条目内的 <details> 和 ### 评价
        pass  # TODO: 实现反向写入

    print("json → md 方向暂未实现，md 手工编辑后用 md→json 方向即可")


# ── 入口 ──────────────────────────────────────────────────────────

def main():
    if "--reverse" in sys.argv:
        json_to_md()
    else:
        records = md_to_json()
        JSON_PATH.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"✅ 已从 {MD_PATH.name} 生成 {JSON_PATH.name}（{len(records)} 条记录）")


if __name__ == "__main__":
    main()
