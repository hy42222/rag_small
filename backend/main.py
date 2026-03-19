import os
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models import ChatRequest, ChatResponse, UploadResponse
from backend.rag2 import run_rag, general_web_like_answer
from backend.ingest import process_documents

# 创建 FastAPI 应用
app = FastAPI(title="Knowledge Base RAG System")

# 开启 CORS，方便前端（如 Streamlit）跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 文件上传目录（用于保存上传的 PDF/DOCX/Excel）
UPLOAD_DIR = "data"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    对话接口：
    - 接收用户 query 与 session_id
    - 调用带有多轮上下文能力的 RAG 链
    - 返回答案与检索到的来源
    """
    try:
        response = run_rag(request.query, request.session_id)
        sources = []
        if "context" in response and response["context"]:
            for doc in response["context"]:
                sources.append(doc.metadata.get("source", "Unknown"))
        ans = response.get("answer", "")
        low_conf = (not sources) or any(x in ans for x in ["不知道", "不清楚", "无法确定", "don't know", "unknown"])
        if low_conf:
            web_ans = general_web_like_answer(request.query)
            ans = f"抱歉，没有在知识库中检索到确切答案。以下为参考的通用网络信息：\n\n{web_ans}"
            if not sources:
                sources = ["Internet"]
        return ChatResponse(answer=ans, sources=list(set(sources)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload", response_model=List[UploadResponse])
async def upload_files(files: List[UploadFile] = File(...)):
    """
    文件上传接口：
    - 将文件保存到 data 目录
    - 触发向量化与入库流程（process_documents）
    - 返回每个文件的处理状态
    """
    results = []
    file_paths = []
    
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_paths.append(file_path)
            results.append(UploadResponse(filename=file.filename, status="Uploaded"))
        except Exception as e:
            results.append(UploadResponse(filename=file.filename, status=f"Error: {str(e)}"))
            
    if file_paths:
        try:
            count = process_documents(file_paths)
            for res in results:
                if res.status == "Uploaded":
                    res.status = f"Uploaded and Ingested ({count} chunks)"
        except Exception as e:
             for res in results:
                if res.status == "Uploaded":
                    res.status = f"Uploaded but Ingestion Failed: {str(e)}"
                    
    return results

@app.post("/ingest_folder")
async def ingest_folder():
    try:
        exts = {".pdf", ".docx", ".xlsx", ".xls"}
        files = []
        for name in os.listdir(UPLOAD_DIR):
            path = os.path.join(UPLOAD_DIR, name)
            if os.path.isfile(path) and os.path.splitext(name)[1].lower() in exts:
                files.append(path)
        if not files:
            return {"message": "No files found in data"}
        count = process_documents(files)
        return {"message": f"Ingested {count} chunks from {len(files)} files"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # 本地调试运行：启动 FastAPI 服务
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
