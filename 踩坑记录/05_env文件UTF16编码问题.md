# 05 — .env 文件 UTF-16 编码导致 dotenv 失败

## 症状

- `python-dotenv` 加载 `.env` 时报错 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff`
- API Key 无法读取，后续所有 LLM 调用失败
- `.env` 文件在记事本中看似正常，但文件大小为 2 字节/字符

## 根因

**某些 Windows 文本编辑器（特别是旧版记事本或某些 IDE 配置）默认将文件保存为 UTF-16 LE 编码。**

UTF-16 LE 的文件以 BOM `FF FE` 开头，而 `python-dotenv` 默认用 UTF-8 编码读取文件，看到 `FF FE` 就报解码错误。

用 `xxd` 查看文件头：
```
FF FE 44 00 45 00 45 00 50 00 53 00 ...  → UTF-16 LE with BOM
```

正常 UTF-8 文件应该是：
```
44 45 45 50 53 45 45 4B 5F 41 50 49 5F ... → 直接可读 ASCII
```

## 修复

将 `.env` 文件转换为 UTF-8 编码：

```bash
# 方法1: iconv
iconv -f UTF-16 -t UTF-8 .env > .env_utf8 && mv .env_utf8 .env

# 方法2: Python
python -c "
content = open('.env', encoding='utf-16').read()
open('.env', 'w', encoding='utf-8').write(content)
"

# 方法3: VSCode
# 右下角点击编码 → 「通过编码保存」 → UTF-8
```

## 影响范围

- Windows 环境，尤其使用中文系统自带记事本创建/编辑 `.env` 时
- 也与 IDE 的项目编码设置有关（某些 IDE 可能默认 UTF-16）

## 预防

- 在 `.gitignore` 中已排除 `.env`，但不影响编码问题
- 建议用 VSCode 等支持编码指示的编辑器打开 `.env`
- 创建 `.env.example` 作为模板，并确保它为 UTF-8
