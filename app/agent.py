import os
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

SYSTEM = """You are an Account People 360 executive assistant.
Use database tools for every count, date, ranking, total, comparison, or recommendation.
Never invent facts. Keep answers concise and action-oriented.
For priorities, explain the evidence. The database tables are people, interactions,
opportunities, and relationships. Use read-only SELECT/WITH SQL only."""

def build_agent(db):
    @tool
    def schema() -> str:
        """Describe the available database tables and columns."""
        out = []
        for table in ["people", "interactions", "opportunities", "relationships"]:
            cols = db.execute(f"DESCRIBE {table}").df()["column_name"].tolist()
            out.append(f"{table}: " + ", ".join(cols))
        return "\n".join(out)

    @tool
    def sql(query: str) -> str:
        """Run a read-only DuckDB SQL SELECT/WITH query and return a table."""
        q = query.strip().rstrip(";")
        first = q.split(None, 1)[0].lower() if q else ""
        if first not in {"select", "with"}:
            return "ERROR: only SELECT/WITH queries are allowed."
        try:
            return db.execute(q).df().to_markdown(index=False)
        except Exception as e:
            return f"SQL ERROR: {e}"

    @tool
    def people_360(name: str) -> str:
        """Return a consolidated summary for a person by name."""
        q = """
        SELECT p.*,
          (SELECT max(i.date) FROM interactions i WHERE i.person_id=p.person_id) AS last_interaction,
          (SELECT count(*) FROM interactions i WHERE i.person_id=p.person_id) AS interaction_count,
          (SELECT coalesce(sum(o.value),0) FROM opportunities o WHERE o.person_id=p.person_id) AS opportunity_value
        FROM people p
        WHERE lower(p.name) LIKE lower(?)
        """
        try:
            return db.execute(q, [f"%{name}%"]).df().to_markdown(index=False)
        except Exception as e:
            return f"ERROR: {e}"

    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        temperature=0
    )
    # Checkpointer gives the agent conversation memory per thread_id, so the
    # UI only needs to send the latest question instead of the full history.
    return create_react_agent(llm, [schema, sql, people_360], prompt=SYSTEM, checkpointer=MemorySaver())
