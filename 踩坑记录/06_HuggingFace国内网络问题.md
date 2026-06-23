# 06 — HuggingFace 国内无法连接

## 症状

- 首次加载 embedding 模型时报网络错误
- `ConnectionError: (WinError 10060) 由于连接方在一段时间后没有正确答复...`
- `huggingface.co` 域名无法解析或连接超时
- 但模型权重文件已在本地缓存，理论上不需要联网

## 根因

**HuggingFace Hub（`huggingface.co`）在中国大陆无法直接访问。**

`sentence-transformers` 库默认从 `https://huggingface.co` 下载模型文件。即使在本地缓存了模型权重，库仍然会在启动时向 HuggingFace 服务器发起 HEAD 请求检查文件更新。

## 修复

### 方案 1：使用镜像站（推荐）

```python
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
```

在项目代码（[app.py](../app.py)、[管理面板.py](../管理面板.py)、[批量导入mod代码.py](../批量导入mod代码.py)）中，通过 embedding 配置读取 `hf_endpoint` 并写入环境变量。

### 方案 2：强制离线模式

```python
os.environ["HF_HUB_OFFLINE"] = "1"
```

此设置告诉 HuggingFace 库完全跳过网络请求。但这会阻止首次下载（需要先手动下载模型到缓存）。

### 方案 3：组合使用

```python
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"  # 首次下载走镜像
os.environ["HF_HUB_OFFLINE"] = "1"                   # 后续运行不走网络
```

注意：`HF_HUB_OFFLINE=1` 会让 `sentence-transformers` 加载模型时完全跳过网络请求，但如果缓存不完整会直接报错。确保模型已通过镜像完全缓存后使用。

## 影响范围

- 中国大陆所有访问 HuggingFace 服务的场景
- 模型下载、tokenizer 配置下载、Hub API 查询等
- `sentence-transformers`、`transformers`、`tokenizers`、`huggingface_hub` 等包

## 相关资源

- HuggingFace 镜像站：https://hf-mirror.com
- 阿里云/华为云等国内云厂商也有 HF 模型镜像
