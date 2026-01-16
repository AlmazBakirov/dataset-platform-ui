import streamlit as st
import pandas as pd
from core.auth import require_role
from core.config import settings
from core.api_client import ApiClient
from core import mock_backend
from core.ui import header
from core.ui_helpers import api_call

require_role(["customer"])
header("QC Review", "Проверка на плагиат/дубликаты + AI-generated. Отображаем результаты, фильтруем по порогам.")

def client() -> ApiClient:
    return ApiClient(settings.backend_url, token=st.session_state.get("token"))

default_request_id = str(st.session_state.get("selected_request_id", "")).strip()
request_id = st.text_input("Request ID", value=default_request_id).strip()
if request_id:
    st.session_state["selected_request_id"] = request_id

col1, col2 = st.columns(2)
with col1:
    dup_thr = st.slider("Duplicate threshold", 0.0, 1.0, 0.85, 0.01)
with col2:
    ai_thr = st.slider("AI-generated threshold", 0.0, 1.0, 0.80, 0.01)

if st.button("Run QC", type="primary", disabled=not request_id):
    def do_run_qc():
        if settings.use_mock:
            return {"status": "mocked"}
        return client().run_qc(request_id)

    resp = api_call("Run QC", do_run_qc, spinner="Starting QC...", show_payload=True)
    if resp is not None:
        st.success("QC started (or mocked).")

if st.button("Load QC results", disabled=not request_id):
    def do_load():
        if settings.use_mock:
            return mock_backend.mock_qc_results(request_id)
        return client().qc_results(request_id)

    rows = api_call("Load QC results", do_load, spinner="Loading QC results...", show_payload=True)
    if rows is None:
        st.stop()

    df = pd.DataFrame(rows)
    if df.empty:
        st.write("No results.")
    else:
        # Защита от отсутствия колонок
        if "duplicate_score" not in df.columns:
            df["duplicate_score"] = 0.0
        if "ai_generated_score" not in df.columns:
            df["ai_generated_score"] = 0.0

        df["is_duplicate"] = df["duplicate_score"] >= dup_thr
        df["is_ai"] = df["ai_generated_score"] >= ai_thr

        only_flagged = st.checkbox("Show only flagged", value=True)
        if only_flagged:
            df = df[df["is_duplicate"] | df["is_ai"]]

        st.dataframe(df, use_container_width=True)
