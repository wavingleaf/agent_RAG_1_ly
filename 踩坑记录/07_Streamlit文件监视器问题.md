# 07 — Streamlit 文件监视器触发 torchvision 缺失

## 症状

- 运行 `streamlit run 管理面板.py` 时，启动过程中报错
- `ModuleNotFoundError: No module named 'torchvision'`
- 项目的 `requirements.txt` 中并没有 `torchvision` 依赖，管理面板也没使用它

## 根因

**Streamlit 启动过程中触发了 `transformers` 包中对 `torchvision` 的引用。**

`transformers` 的部分源码文件（主要是图像模型，如 ViT/CLIP 等）包含 `import torchvision`。Streamlit 在某条路径上触发了这个 `import`，而系统中没有安装 `torchvision`。

注意：本项目使用 bge-m3 纯文本 embedding 模型，实际运行时**不需要** `torchvision`（`torchvision` 仅用于图像模型推理，bge-m3 不会触发这些代码路径）。安装 `torchvision`（~800MB）是不必要的浪费。

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

- 使用 `--server.runOnSave false` — 仅关闭保存时刷新，但未必覆盖触发 `torchvision` 引用的路径
