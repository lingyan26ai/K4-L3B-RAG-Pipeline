import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("RAG Chatbot")
    st.caption("Thay mô tả theo đề tài của nhóm")
    top_k = st.slider("Số chunks", 3, 10, 5)

st.title("RAG Chatbot")
st.caption("Thay tiêu đề và hướng dẫn sử dụng")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Nguồn trích dẫn / Documents"):
                for idx, src in enumerate(message["sources"], 1):
                    meta = src.get("metadata", {})
                    title = meta.get("title", "Không có tiêu đề")
                    source = meta.get("source", "Không rõ nguồn")
                    method = src.get("retrieval_method", "N/A")
                    score = src.get("score", 0.0)
                    st.markdown(f"**[{idx}] {title}** ({source})")
                    st.caption(f"Phương thức: `{method}` | Điểm: `{score:.4f}`")
                    st.text(src.get("content", ""))

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        result = generate_with_citation(query, top_k=top_k)
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        st.markdown(answer)

        if sources:
            with st.expander("Nguồn trích dẫn / Documents"):
                for idx, src in enumerate(sources, 1):
                    meta = src.get("metadata", {})
                    title = meta.get("title", "Không có tiêu đề")
                    source = meta.get("source", "Không rõ nguồn")
                    method = src.get("retrieval_method", "N/A")
                    score = src.get("score", 0.0)
                    st.markdown(f"**[{idx}] {title}** ({source})")
                    st.caption(f"Phương thức: `{method}` | Điểm: `{score:.4f}`")
                    st.text(src.get("content", ""))

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
