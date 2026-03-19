import os
from dotenv import load_dotenv

load_dotenv()

# 加载 .env 环境变量，用于本地开发时读取密钥与配置
# 生产环境中建议通过系统环境变量或秘密管理服务注入，避免明文写入代码库

# -------------------------
# 大模型（Qwen / DashScope）配置
# -------------------------
# 从环境变量读取 DashScope 的 API Key（优先 DASHSCOPE_API_KEY，其次 QWEN_API_KEY）
QWEN_API_KEY = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
# Qwen OpenAI 兼容接口的 Base URL（默认使用 DashScope 兼容模式）
QWEN_API_BASE = os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# -------------------------
# MongoDB 配置（会话历史与元数据）
# -------------------------
# 远程 MongoDB 连接串，示例为在 118.25.145.235 上的 Docker 部署
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://118.25.145.235:27017/")

# -------------------------
# Milvus 配置（向量数据库）
# -------------------------
# 远程 Milvus 服务端地址（Standalone 兼容 http://host:19530）
MILVUS_URI = os.getenv("MILVUS_URI", "http://118.25.145.235:19530")

# -------------------------
# 向量化模型（Embedding）配置
# -------------------------
# 使用 Qwen / DashScope 的向量模型名称，默认 text-embedding-v1
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-v1")
