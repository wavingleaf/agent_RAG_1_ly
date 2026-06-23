"""
一键启动 RAG 助手（聊天端）
双击此文件或终端执行 `python 启动rag助手.py`

聊天界面运行在 http://localhost:8000
管理面板请另开终端执行 `streamlit run 管理面板.py`，运行在 http://localhost:8501
"""
import subprocess
import sys
from pathlib import Path

# Windows 终端可能使用 GBK 编码，强制 stdout 用 UTF-8（避免 emoji 报错）
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    print("🚀 正在启动 RAG 聊天端...")
    print(f"📂 工作目录: {project_dir}")
    print(f"🌐 浏览器访问: http://localhost:8000")
    print(f"🛠️ 管理面板另开: streamlit run 管理面板.py  (http://localhost:8501)")
    print()

    try:
        subprocess.run(
            [sys.executable, "-m", "chainlit", "run", "app.py"],
            cwd=project_dir,
            check=True,
        )
    except FileNotFoundError:
        print("❌ 错误：未找到 chainlit，请先运行 pip install -r requirements.txt")
        input("按回车键退出...")
    except subprocess.CalledProcessError:
        print("⚠️ 程序异常退出，查看上方报错信息")
        input("按回车键退出...")
    except KeyboardInterrupt:
        print("\n👋 已关闭")


if __name__ == "__main__":
    main()
