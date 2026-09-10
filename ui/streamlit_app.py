from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


st.set_page_config(page_title="Production Text-to-SQL", layout="wide")
st.title("Natural Language to SQL")
st.caption("Ask questions about the database in plain English.")

backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
api_key = os.getenv("BACKEND_API_KEY", "")

question = st.text_input(
    "Ask a question",
    placeholder="Show students who scored more than 90",
)

if st.button("Run query", type="primary", disabled=not question.strip()):
    headers = {"X-API-Key": api_key} if api_key else {}
    try:
        response = requests.post(
            f"{backend_url}/api/v1/query",
            json={"question": question, "include_sql": True},
            headers=headers,
            timeout=60,
        )
        if response.ok:
            result = response.json()
            st.success(result["answer"])

            with st.expander("Generated SQL", expanded=True):
                st.code(result.get("sql") or "SQL hidden")

            if result["rows"]:
                st.dataframe(pd.DataFrame(result["rows"]), use_container_width=True)
            else:
                st.info("The query returned no rows.")

            if result.get("truncated"):
                st.warning("The result was truncated to the configured row limit.")
            st.caption(f"Request ID: {result['request_id']} · {result['latency_ms']} ms")
        else:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            st.error(f"Request failed: {detail}")
    except requests.RequestException as exc:
        st.error(f"Could not connect to the backend: {exc}")
