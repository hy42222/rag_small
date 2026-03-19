from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    # 用户的自然语言问题
    query: str
    # 会话 ID，用于多轮对话的历史记录检索与存储
    session_id: str = "default"
    # 可选的历史消息（前端可传，后端实际以 MongoDB 为准）
    history: List[dict] = []

class ChatResponse(BaseModel):
    # 大模型生成的回答
    answer: str
    # 检索到的文档来源（去重后展示）
    sources: List[str]

class UploadResponse(BaseModel):
    # 上传的文件名
    filename: str
    # 处理状态（例如：已上传 / 已上传并入库 / 入库失败等）
    status: str
