import streamlit as st
import requests
import uuid
import os

# 页面基础配置（标题、布局、收起侧边栏）
st.set_page_config(page_title="知识库问答系统", layout="wide", initial_sidebar_state="collapsed")

# 自定义样式：营造“豆包”风格的居中欢迎区与卡片化对话气泡
st.markdown("""
<style>
    .stApp {
        background-color: #f7f9fb;
    }
    .main-header {
        text-align: center;
        margin-top: 100px;
        margin-bottom: 40px;
    }
    .main-header h1 {
        font-size: 48px;
        font-weight: 600;
        color: #1f2329;
    }
    .suggestion-chip {
        background-color: #ffffff;
        border: 1px solid #e4e6e9;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
        height: 100%;
        display: flex;
        align-items: center;
        justify_content: center;
        font-size: 14px;
        color: #1f2329;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }
    .suggestion-chip:hover {
        background-color: #f2f4f7;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .stChatMessage {
        background-color: transparent !important;
    }
    div[data-testid="stChatMessageContent"] {
        background-color: #ffffff !important;
        border-radius: 12px !important;
        padding: 15px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02) !important;
    }
    div[data-testid="stChatMessageContent"] p {
        font-size: 16px !important;
    }
</style>
""", unsafe_allow_html=True)

# 后端 API 地址（FastAPI）
API_URL = os.getenv("API_URL", "http://localhost:8000")

# 侧边栏：文档上传与批量导入
with st.sidebar:
    st.header("📚 知识库")
    uploaded_files = st.file_uploader(
        "上传文档（PDF、DOCX、Excel）", 
        type=["pdf", "docx", "xlsx"], 
        accept_multiple_files=True
    )
    
    if st.button("处理文档", type="primary"):
        if uploaded_files:
            files = [
                ("files", (file.name, file, file.type))
                for file in uploaded_files
            ]
            try:
                with st.spinner("正在处理文档..."):
                    response = requests.post(f"{API_URL}/upload", files=files)
                if response.status_code == 200:
                    st.success("文档处理成功！")
                    st.json(response.json())
                else:
                    st.error(f"处理文档出错：{response.text}")
            except Exception as e:
                st.error(f"连接错误：{str(e)}")
        else:
            st.warning("请先上传文件。")

    st.markdown("---")
    if st.button("导入 data 文件夹"):
        try:
            with st.spinner("正在导入 data 文件夹文件..."):
                response = requests.post(f"{API_URL}/ingest_folder")
            if response.status_code == 200:
                st.success(response.json()["message"])
            else:
                st.error(f"导入文件夹出错：{response.text}")
        except Exception as e:
            st.error(f"连接错误：{str(e)}")

# 会话状态：保存聊天记录与会话 ID
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# 主区域：初始欢迎页与建议问题按钮
if not st.session_state.messages:
    st.markdown('<div class="main-header"><h1>我可以帮你做什么？</h1></div>', unsafe_allow_html=True)
    
    # # Suggestion Chips
    # suggestions = [
    #     "Summarize the employee handbook",
    #     "What is the reimbursement policy?",
    #     "How do I apply for leave?",
    #     "Explain the project workflow"
    # ]
    
    cols = st.columns(2)
    # for i, suggestion in enumerate(suggestions):
    #     with cols[i % 2]:
    #         if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
    #             st.session_state.messages.append({"role": "user", "content": suggestion})
    #             st.rerun()

# 历史消息区：逐条渲染
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 输入区：发送问题并与后端交互
if prompt := st.chat_input("请输入你的问题..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            with st.spinner("思考中..."):
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "query": prompt,
                        "session_id": st.session_state.session_id,
                        "history": st.session_state.messages
                    }
                )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])
                
                full_response = answer
                if sources:
                    full_response += "\n\n**来源：**\n" + "\n".join(f"- {s}" for s in sources)
                
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            else:
                message_placeholder.error(f"错误：{response.text}")
        except Exception as e:
            message_placeholder.error(f"连接错误：{str(e)}")
