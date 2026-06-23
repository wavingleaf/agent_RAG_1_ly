# 07 — Streamlit 文件监视器触发 torchvision 缺失

## 症状

- 运行 `streamlit run 管理面板.py` 时，启动过程中报错
- `ModuleNotFoundError: No module named 'torchvision'`
- 项目的 `requirements.txt` 中并没有 `torchvision` 依赖，管理面板也没使用它

## 根因

**Streamlit 的文件监视器（file watcher）会在启动时扫描所有已安装的 Python 包目录，查找配置文件/脚本文件的变化。**

默认情况下 Streamlit 使用 `watchdog` 或 `polling` 监视器扫描项目目录和依赖包目录。当它扫描到 `transformers` 包目录时，`transformers` 的某段代码会**懒加载** `torchvision`（在特定条件下才 import），而系统中没有安装 `torchvision`。

不是在代码中直接 import `torchvision`，而是 Streamlit 的文件系统扫描触发了 `transformers` 包内的模块发现机制，导致间接引用了 `torchvision`。

## 修复

禁用 Streamlit 的文件监视器：

```python
os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")
```

启动命令中添加参数：
```bash
streamlit run 管理面板.py --server.fileWatcherType none
```

或者在 [启动管理面板.py](../启动管理面板.py) 中同时使用环境变量和命令行参数双保险：
```python
subprocess.run([
    sys.executable, "-m", "streamlit", "run", "管理面板.py",
    "--server.fileWatcherType", "none"
])
```

## 影响范围

- 安装了大量 Python 机器学习包的环境
- `--server.fileWatcherType none` 意味着 Streamlit 不会自动检测代码修改并重载页面，需手动刷新

## 替代方案

- 安装 `torchvision`（`pip install torchvision`）— 但为不需要的依赖安装 800MB+ 的包不合理
- 使用 `--server.runOnSave false` — 仅关闭保存时刷新，文件监视器仍可能触发扫描
