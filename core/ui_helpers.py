from __future__ import annotations

from typing import Callable, TypeVar, Optional

import streamlit as st

from core.api_client import ApiError

T = TypeVar("T")


def api_call(
    action: str,
    fn: Callable[[], T],
    *,
    spinner: Optional[str] = None,
    show_payload: bool = False,
) -> Optional[T]:
    """
    Unified wrapper for backend calls:
    - shows spinner
    - catches ApiError
    - prints consistent error messages
    """
    try:
        with st.spinner(spinner or f"{action}..."):
            return fn()
    except ApiError as e:
        # e.message is the most useful summary, status_code is for debugging
        st.error(f"{action} failed ({e.status_code}): {e.message}")
        if show_payload and e.payload is not None:
            try:
                st.json(e.payload)
            except Exception:
                st.write(e.payload)
        return None
