from langchain_openai import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_milvus import Milvus
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import MongoDBChatMessageHistory, ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from backend.config import QWEN_API_KEY, QWEN_API_BASE, MILVUS_URI, EMBEDDING_MODEL_NAME, MONGODB_URI

embeddings = DashScopeEmbeddings(model=EMBEDDING_MODEL_NAME, dashscope_api_key=QWEN_API_KEY)

def _build_retriever():
    vector_store = Milvus(
        embedding_function=embeddings,
        connection_args={"uri": MILVUS_URI},
        collection_name="knowledge_base",
        auto_id=True,
    )
    return vector_store.as_retriever()

llm = ChatOpenAI(api_key=QWEN_API_KEY or "sk-dummy", base_url=QWEN_API_BASE, model="qwen-turbo", temperature=0.7)

contextualize_q_system_prompt = (
    "Given a chat history and the latest user question which might reference context in the chat history, "
    "formulate a standalone question which can be understood without the chat history. Do NOT answer the question, "
    "just reformulate it if needed and otherwise return it as is."
)

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [("system", contextualize_q_system_prompt), MessagesPlaceholder("chat_history"), ("human", "{input}")]
)

qa_system_prompt = (
    "You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer "
    "the question. If you don't know the answer, say that you don't know. Use three sentences maximum and keep the "
    "answer concise.\n\n{context}"
)

qa_prompt = ChatPromptTemplate.from_messages(
    [("system", qa_system_prompt), MessagesPlaceholder("chat_history"), ("human", "{input}")]
)

_LOCAL_HISTORY: dict[str, ChatMessageHistory] = {}

def get_session_history(session_id: str):
    try:
        return MongoDBChatMessageHistory(
            session_id=session_id,
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
    history_aware_retriever = create_history_aware_retriever(llm, _build_retriever(), contextualize_q_prompt)
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
    try:
        chain = get_chain_with_history(use_memory=False)
        return chain.invoke({"input": query}, config={"configurable": {"session_id": session_id}})
    except Exception:
        chain = get_chain_with_history(use_memory=True)
        return chain.invoke({"input": query}, config={"configurable": {"session_id": session_id}})

def general_web_like_answer(query: str) -> str:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Provide a concise answer based on general public web knowledge. If policies vary by organization, state that it may differ. Answer in the same language as the question.",
            ),
            ("human", "{q}"),
        ]
    )
    chain = prompt | llm
    res = chain.invoke({"q": query})
    try:
        return res.content
    except Exception:
        return str(res)
