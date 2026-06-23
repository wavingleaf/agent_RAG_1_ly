# 04 — Windows 终端 GBK 编码报错

## 症状

- Python 脚本 `print()` 输出含中文或 emoji 的字符串时报错
- `UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f680' in position 0: illegal multibyte sequence`
- 涉及所有启动脚本（`启动rag助手.py`、`启动管理面板.py`、`批量导入mod代码.py`）

## 根因

**Windows 中文版系统的终端默认编码是 GBK（CP936），而非 UTF-8。**

Python 的 `sys.stdout` 继承了终端的编码设置。当代码中 `print("🚀 正在启动...")` 时，Python 尝试用 GBK 编码 emoji `🚀`（U+1F680），但 GBK 编码表中没有这个字符，抛 `UnicodeEncodeError`。

## 修复

在每个独立运行的 Python 脚本顶部，强制将 stdout 的编码改为 UTF-8：

```python
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

`errors="replace"` 确保即使有无法表示的字符，也会被替换为 `?` 而非崩溃。

**注意**：不能用 `sys.setdefaultencoding`（Python 3 已移除），也不能设环境变量 `PYTHONIOENCODING=utf-8`（在某些 Windows 终端中不生效）。

## 影响范围

- Windows 中文/日文/韩文等非英语系统
- 所有独立运行的 `.py` 启动脚本（不通过 IDE 运行时）
- 如通过 PyCharm/VSCode 等 IDE 运行，IDE 通常有独立的终端编码配置，可能不受影响

## 替代方案

- 避免在 print 中使用 emoji（"🚀"→"[启动]"），但治标不治本
- PowerShell 中运行 `chcp 65001` 切换当前终端到 UTF-8（每次打开终端都需手动执行）
