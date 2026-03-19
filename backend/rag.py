from langchain_openai import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_milvus import Milvus
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import MongoDBChatMessageHistory, ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from backend.config import QWEN_API_KEY, QWEN_API_BASE, MILVUS_URI, EMBEDDING_MODEL_NAME, MONGODB_URI

# -------------------------
# 1) 向量模型（Embedding）
# -------------------------
# 使用 Qwen / DashScope 的 embedding 模型，将文本转为向量用于向量检索
embeddings = DashScopeEmbeddings(
    model=EMBEDDING_MODEL_NAME,
    """
    延迟连接 Milvus，避免服务启动阶段因为远程不可达而崩溃。
    仅在真正检索时才建立连接。
    """
    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={"uri": MILVUS_URI},
        collection_name="knowledge_base",
# -------------------------
# 3) 大语言模型（LLM：Qwen）
# -------------------------
# 通过 OpenAI 兼容接口使用 Qwen。在 DashScope 控制台开通相应模型即可
llm = ChatOpenAI(
    api_key=QWEN_API_KEY or "sk-dummy",
    base_url=QWEN_API_BASE,

# -------------------------
# 4) 历史感知：将多轮对话中的指代解析为可独立理解的问题
# -------------------------
contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question which can be understood "
    "without the chat history. Do NOT answer the question, "
    "just reformulate it if needed and otherwise return it as is."
)

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),

# -------------------------
# 5) 答案生成：基于检索到的上下文生成简洁回答
# -------------------------
qa_system_prompt = (
    "You are an assistant for question-answering tasks. "
    "Use the following pieces of retrieved context to answer "
    "the question. If you don't know the answer, say that you "
    "don't know. Use three sentences maximum and keep the "
    "answer concise."
    "\n\n"
    "{context}"
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
_LOCAL_HISTORY: dict[str, ChatMessageHistory] = {}
    ]
)

# -------------------------
# 6) 消息历史：优先使用 MongoDB，失败时回退到进程内内存
            connection_string=MONGODB_URI,
            database_name="chat_history",
            collection_name="messages",
        )
    except Exception:
        if session_id not in _LOCAL_HISTORY:
            _LOCAL_HISTORY[session_id] = ChatMessageHistory()
        return _LOCAL_HISTORY[session_id]

def get_session_history_memory(session_id: str):
    if session_id not in _LOCAL_HISTORY:
        _LOCAL_HISTORY[session_id] = ChatMessageHistory()
    return _LOCAL_HISTORY[session_id]

def get_chain_with_history(use_memory: bool = False):
    history_aware_retriever = create_history_aware_retriever(
        llm, _build_retriever(), contextualize_q_prompt
    )
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    return RunnableWithMessageHistory(
        rag_chain,
        get_session_history_memory if use_memory else get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

def run_rag(query: str, session_id: str):
    # 优先尝试使用 MongoDB 历史；若出现连接类异常，自动回退到内存历史
    try:
        chain = get_chain_with_history(use_memory=False)
        return chain.invoke(
            {"input": query},
            config={"configurable": {"session_id": session_id}}
        )
    except Exception as e:
        chain = get_chain_with_history(use_memory=True)
        return chain.invoke(
            {"input": query},
            config={"configurable": {"session_id": session_id}}
        )

def general_web_like_answer(query: str) -> str:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Provide a concise answer based on general public web knowledge. If policies vary by organization, state that it may differ. Answer in Chinese when the question is Chinese."),
            ("human", "{q}"),
        ]
    )
    chain = prompt | llm
    res = chain.invoke({"q": query})
    try:
        return res.content
    except Exception:
        return str(res)
