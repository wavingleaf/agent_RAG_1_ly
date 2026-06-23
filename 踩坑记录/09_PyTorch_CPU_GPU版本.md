# 09 — PyTorch CPU 版本无法使用 GPU

## 症状

- 大批量文本 Embedding 时，Python 进程 CPU 占用 90%+，GPU 0%
- `torch.cuda.is_available()` 返回 `False`
- `sentence-transformers` 加载模型日志显示 `No device provided, using cpu`
- 系统已安装 NVIDIA GPU（RTX 4060）和 CUDA Driver（13.1）

## 根因

**安装的是 PyTorch CPU-only 版本，不包含 CUDA 支持。**

`pip install torch` 默认安装的是 CPU 版本。CPU 版本不管系统有没有 GPU，都不会使用 CUDA。

PyTorch 的 CUDA 版本需要用特定的 `--index-url` 参数安装：
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

`cu124` 对应 CUDA 12.4 版本。RTX 4060 需要 CUDA 12.x。

## 修复

```bash
# 1. 卸载 CPU 版
pip uninstall torch -y

# 2. 安装 CUDA 12.4 版
pip install torch --index-url https://download.pytorch.org/whl/cu124

# 3. 验证
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU only\"}')"
# 输出: CUDA available: True
#       Device: NVIDIA GeForce RTX 4060
```

## 影响范围

- 所有需要 GPU 加速的 PyTorch 操作（Embedding、模型推理）
- RTX 4060 8GB 在 `all-MiniLM-L6-v2` 上：GPU 推理比 CPU 快 20-50 倍
- `sentence-transformers` 自动检测 CUDA 并使用 GPU，无需额外配置

## 性能对比

| 场景 | CPU (Ryzen) | GPU (RTX 4060) |
|------|-------------|-----------------|
| 嵌入 1000 条文本 | ~45 秒 | ~2 秒 |
| 嵌入 35000 条文本 | ~25 分钟 | ~40 秒 |
| CPU 占用 | 90%+ | < 10% |

## CUDA 版本选择

- 查看 Driver 支持的最高 CUDA：`nvidia-smi`（右上角 CUDA Version）
- 本机 Driver 13.1，支持 CUDA 12.x
- PyTorch 目前最新稳定为 cu124（CUDA 12.4）
