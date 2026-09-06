print("SCRIPT START", flush=True)
from dotenv import load_dotenv
load_dotenv()
print("ENV LOADED", flush=True)
from app.data_loader import load_workbook_to_duckdb
from app.agent import build_agent

with open("data/sample_account_people.xlsx", "rb") as f:
    raw = f.read()
db = load_workbook_to_duckdb(raw)
agent = build_agent(db)
config = {"configurable": {"thread_id": "test"}}
try:
    result = agent.invoke({"messages": [{"role": "user", "content": "Who should I prioritize this week?"}]}, config=config)
    for m in result["messages"]:
        print("---", type(m).__name__)
        print(m)
except Exception as e:
    import traceback
    traceback.print_exc()
