"""
批量导入mod代码.py —— 将指定 mod 目录下所有 .lua 文件切分入库

用法：
    python 批量导入mod代码.py
    python 批量导入mod代码.py --mod 棱镜           # 只导入指定 mod
    python 批量导入mod代码.py --dry-run            # 只统计不写入
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Windows 终端可能使用 GBK 编码，强制 stdout 用 UTF-8（避免 emoji 报错）
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

# ── 0. 路径与配置 ──────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_DIR / "config.json"
MOD_SOURCE_DIR = PROJECT_DIR.parent / "好mod全部代码供观看"  # 默认 mod 源码目录

load_dotenv(PROJECT_DIR / ".env")


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_embedding(cfg):
    emb_cfg = cfg.get("embedding", {})
    endpoint = emb_cfg.get("hf_endpoint", "")
    if endpoint and not os.getenv("HF_ENDPOINT"):
        os.environ["HF_ENDPOINT"] = endpoint
    # 强制离线模式：模型已在首次运行时缓存到本地（~80MB），无需每次联网检查
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    # GPU 优先：sentence-transformers 检测到 CUDA 时会自动用 GPU
    # RTX 4060 下 Embedding 推理比 CPU 快 20-50 倍
    model_kwargs = {"local_files_only": True}
    return HuggingFaceEmbeddings(
        model_name=emb_cfg.get("model_name", "all-MiniLM-L6-v2"),
        model_kwargs=model_kwargs,
    )


# ── 1. 核心逻辑 ───────────────────────────────────────────────────


def collect_lua_files(mod_dir: Path) -> list[Path]:
    """递归收集目录下所有 .lua 文件"""
    files = []
    for f in mod_dir.rglob("*.lua"):
        # 跳过非代码目录（anim/ 下如果有 .lua 也保留，但 .zip 已被过滤）
        files.append(f)
    return sorted(files)


def read_file_content(filepath: Path) -> str | None:
    """读取文件内容，自动尝试 UTF-8 / GBK 编码"""
    for enc in ["utf-8", "gbk", "latin-1"]:
        try:
            return filepath.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None


def import_mod(
    mod_name: str,
    mod_dir: Path,
    vectorstore: Chroma,
    splitter: RecursiveCharacterTextSplitter,
    dry_run: bool = False,
) -> dict:
    """
    导入单个 mod 的所有 .lua 文件到向量库。
    返回统计信息。
    """
    files = collect_lua_files(mod_dir)
    if not files:
        print(f"  ⚠️ {mod_name}: 未找到 .lua 文件")
        return {"files": 0, "chunks": 0, "skipped": 0}

    total_chunks = 0
    skipped = 0

    for fpath in files:
        content = read_file_content(fpath)
        if content is None:
            print(f"  ⚠️ 无法解码: {fpath.name}")
            skipped += 1
            continue

        # 跳过空文件
        if not content.strip():
            skipped += 1
            continue

        # 相对路径作为元数据（如 "scripts/prefabs/moonlight_legion.lua"）
        rel_path = str(fpath.relative_to(mod_dir))

        if dry_run:
            # 干跑模式：只统计分块数，不写入
            chunks = splitter.split_text(content)
            total_chunks += len(chunks)
            continue

        chunks = splitter.split_text(content)
        metadatas = [
            {
                "mod_name": mod_name,
                "source": rel_path,
                "chunk": i,
                "knowledge_source": "reference-mods",
            }
            for i in range(len(chunks))
        ]
        vectorstore.add_texts(chunks, metadatas=metadatas)
        total_chunks += len(chunks)

    print(f"  ✅ {mod_name}: {len(files)} 文件 → {total_chunks} 片段" + (f"（跳过 {skipped}）" if skipped else ""))
    return {"files": len(files), "chunks": total_chunks, "skipped": skipped}


# ── 2. 入口 ──────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="批量导入 mod .lua 代码到 RAG 向量库")
    parser.add_argument("--mod", type=str, help="只导入指定 mod（目录名）")
    parser.add_argument("--source", type=str, help="mod 源码根目录", default=str(MOD_SOURCE_DIR))
    parser.add_argument("--dry-run", action="store_true", help="只统计文件数和分块数，不写入向量库")
    args = parser.parse_args()

    source_dir = Path(args.source)
    if not source_dir.exists():
        print(f"❌ 目录不存在: {source_dir}")
        sys.exit(1)

    cfg = load_config()
    kb_cfg = cfg.get("knowledge_base", {})

    # 分块策略：.lua 文件用换行符优先，搭配 Lua 常见分隔符
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=kb_cfg.get("chunk_size", 500),
        chunk_overlap=kb_cfg.get("chunk_overlap", 50),
        separators=["\n\n\n", "\n\n", "\n", "end\n", " ", ""],
    )

    # 初始化向量库
    embedding = get_embedding(cfg)
    pd = kb_cfg.get("persist_directory", "./chroma_db")
    persist_dir = str(Path(pd).expanduser()) if pd.startswith("~") else str(PROJECT_DIR / pd)
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embedding)

    batch_count = vectorstore._collection.count() if vectorstore._collection else 0
    print(f"📚 导入前知识库片段数: {batch_count}")
    print(f"📂 源码目录: {source_dir}")
    if args.dry_run:
        print("🔍 DRY RUN 模式 — 不写入向量库\n")
    else:
        print()

    # 确定要导入哪些 mod
    if args.mod:
        mod_dirs = [(args.mod, source_dir / args.mod)]
    else:
        # 自动发现源码目录下的所有子目录
        mod_dirs = []
        for d in sorted(source_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                mod_dirs.append((d.name, d))

    total_stats = {"files": 0, "chunks": 0, "skipped": 0}
    for mod_name, mod_dir in mod_dirs:
        stats = import_mod(mod_name, mod_dir, vectorstore, splitter, dry_run=args.dry_run)
        total_stats["files"] += stats["files"]
        total_stats["chunks"] += stats["chunks"]
        total_stats["skipped"] += stats["skipped"]

    # 汇总
    print(f"\n{'🔍 [DRY RUN] 汇总' if args.dry_run else '📊 入库汇总'}:")
    print(f"  文件数: {total_stats['files']}")
    print(f"  切分片段: {total_stats['chunks']}")
    if total_stats["skipped"]:
        print(f"  跳过: {total_stats['skipped']}")

    if not args.dry_run:
        final_count = vectorstore._collection.count() if vectorstore._collection else 0
        print(f"  知识库总片段数: {final_count} (导入前 {batch_count} → 导入后 {final_count})")

    print("\n✅ 完成")


if __name__ == "__main__":
    main()
