import io
import duckdb
import pandas as pd

EXPECTED = ["People", "Interactions", "Opportunities", "Relationships"]

def load_workbook_to_duckdb(workbook_bytes: bytes):
    xls = pd.ExcelFile(io.BytesIO(workbook_bytes))
    missing = [s for s in EXPECTED if s not in xls.sheet_names]
    if missing:
        raise ValueError(f"Missing sheets: {missing}. Found: {xls.sheet_names}")
    con = duckdb.connect(database=":memory:")
    for sheet in EXPECTED:
        df = pd.read_excel(xls, sheet_name=sheet)
        name = sheet.lower()
        con.register("tmp_df", df)
        con.execute(f'CREATE TABLE "{name}" AS SELECT * FROM tmp_df')
        con.unregister("tmp_df")
    return con
