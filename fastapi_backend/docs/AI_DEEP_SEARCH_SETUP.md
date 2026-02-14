# 部门制度 AI 深度搜索 - 模型与部署说明

## 一、依赖安装

```bash
cd fastapi_backend
pip install chromadb sentence-transformers PyMuPDF python-docx
# 或
pip install -r requirements.txt
```

## 二、模型 bge-small-zh-v1.5

### 方式 A：自动下载（推荐）

首次运行深度搜索时，程序会自动从 HuggingFace 下载模型，需确保服务器可访问外网。

### 方式 B：手动下载并指定路径

1. **下载模型**
   - HuggingFace: https://huggingface.co/BAAI/bge-small-zh-v1.5
   - 下载全部文件到本地目录，例如：`fastapi_backend/models/bge-small-zh-v1.5/`

2. **目录结构示例**
   ```
   fastapi_backend/
   └── models/
       └── bge-small-zh-v1.5/
           ├── config.json
           ├── pytorch_model.bin  (或 model.safetensors)
           ├── tokenizer_config.json
           ├── vocab.txt
           └── ...
   ```

3. **配置路径**
   - 在 `fastapi_backend/.env` 中添加：
   ```
   EMBEDDING_MODEL_PATH=models/bge-small-zh-v1.5
   ```
   - 或使用绝对路径，如：`E:/Desktop/tuixiu_protect/OA_system/fastapi_backend/models/bge-small-zh-v1.5`

## 三、已有制度回填向量

新增深度搜索前已存在的制度需执行回填脚本，为它们生成向量：

```bash
cd fastapi_backend
python scripts/backfill_policy_vectors.py
```

## 四、切片参数（可调）

文档按切片存储，便于展示匹配切片。可在 `.env` 中配置：

```
VECTOR_CHUNK_SIZE=400    # 每块字符数（100~2000）
VECTOR_CHUNK_OVERLAP=80  # 块间重叠字符数
```

切片越小，匹配越精准，匹配切片越易展示。修改后需重新回填。

## 五、向量数据存储

向量库存储在 `fastapi_backend/data/policy_chroma/`，持久化，重启服务后无需重新建库。**修改切片参数或距离度量后需删除该目录并重新回填**。

## 六、相关性分数

使用**余弦距离**（cosine distance），相关性 = 1 - 距离，范围为 0–100%。原文复制时理论上接近 100%。若分数仍偏低，请先删除 `data/policy_chroma/` 目录后重新执行回填。
