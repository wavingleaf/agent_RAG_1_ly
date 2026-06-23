"""
一键启动 RAG 管理面板
双击此文件或终端执行 `python 启动管理面板.py`

管理面板运行在 http://localhost:8501
聊天端请另开终端执行 `chainlit run app.py`，运行在 http://localhost:8000
"""
import subprocess
import sys
from pathlib import Path

# Windows 终端可能使用 GBK 编码，强制 stdout 用 UTF-8（避免 emoji 报错）
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    print("🛠️ 正在启动 RAG 管理面板...")
    print(f"📂 工作目录: {project_dir}")
    print(f"🌐 浏览器访问: http://localhost:8501")
    print(f"💬 聊天端另开: chainlit run app.py  (http://localhost:8000)")
    print()

    try:
        # --server.fileWatcherType none 避免扫描 transformers 时误报 torchvision 缺失
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "管理面板.py",
             "--server.fileWatcherType", "none"],
            cwd=project_dir,
            check=True,
        )
    except FileNotFoundError:
        print("❌ 错误：未找到 streamlit，请先运行 pip install -r requirements.txt")
        input("按回车键退出...")
    except subprocess.CalledProcessError:
        print("⚠️ 程序异常退出，查看上方报错信息")
        input("按回车键退出...")
    except KeyboardInterrupt:
        print("\n👋 已关闭")


if __name__ == "__main__":
    main()
