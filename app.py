import os
import uuid
import streamlit as st
from dotenv import load_dotenv
from app.data_loader import load_workbook_to_duckdb
from app.agent import build_agent

load_dotenv()
st.set_page_config(page_title="Account People 360", page_icon="👥", layout="wide")
st.title("👥 Account People 360")
st.caption("LangGraph + DuckDB + Groq")


@st.cache_resource(show_spinner="Loading workbook into DuckDB...")
def get_db(workbook_bytes: bytes):
    return load_workbook_to_duckdb(workbook_bytes)


@st.cache_resource(show_spinner="Starting agent...")
def get_agent(_db):
    return build_agent(_db)


with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload Excel workbook", type=["xlsx", "xls"])
    if uploaded:
        new_bytes = uploaded.getvalue()
        if st.session_state.get("workbook_bytes") != new_bytes:
            st.session_state["workbook_bytes"] = new_bytes
            st.session_state["thread_id"] = str(uuid.uuid4())
            st.session_state["messages"] = []
        st.success(f"Loaded: {uploaded.name}")
    else:
        st.info("Using included synthetic sample workbook.")

    st.divider()
    st.header("Try a question")
    examples = [
        "Who should I prioritize this week?",
        "Show me people who have not been contacted in 60 days.",
        "Who are the decision makers?",
        "Which people are connected to our biggest opportunities?",
        "Give me a People 360 summary for Sarah Lee.",
        "Give me an account people summary.",
        "Which relationships are at risk?"
    ]
    for q in examples:
        if st.button(q, use_container_width=True):
            st.session_state["pending"] = q

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())

for m in st.session_state["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

question = st.chat_input("Ask about people, relationships, engagement, or opportunities...")
if not question and "pending" in st.session_state:
    question = st.session_state.pop("pending")

if question:
    st.session_state["messages"].append({"role":"user","content":question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        if not os.getenv("GROQ_API_KEY"):
            answer = "Add GROQ_API_KEY to `.env` (copy `.env.example` first)."
        else:
            try:
                if "workbook_bytes" in st.session_state:
                    raw = st.session_state["workbook_bytes"]
                else:
                    with open("data/sample_account_people.xlsx", "rb") as f:
                        raw = f.read()
                db = get_db(raw)
                agent = get_agent(db)
                config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
                with st.spinner("Analyzing..."):
                    # Only the new question is sent; the checkpointer recalls
                    # prior turns for this thread, so follow-ups stay in context.
                    result = agent.invoke({"messages": [{"role": "user", "content": question}]}, config=config)
                answer = result["messages"][-1].content
            except Exception as e:
                answer = f"Error: {e}"
        st.markdown(answer)
    st.session_state["messages"].append({"role":"assistant","content":answer})
