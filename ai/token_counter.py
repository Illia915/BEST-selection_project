def _get_store():
    try:
        import streamlit as st
        if "token_usage" not in st.session_state:
            st.session_state["token_usage"] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "requests": 0}
        return st.session_state["token_usage"]
    except Exception:
        return _fallback

_fallback = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "requests": 0}

def update_usage(prompt_tokens: int, completion_tokens: int):
    s = _get_store()
    s["prompt_tokens"] += prompt_tokens
    s["completion_tokens"] += completion_tokens
    s["total_tokens"] += prompt_tokens + completion_tokens
    s["requests"] += 1

def get_session_usage() -> dict:
    return dict(_get_store())

def reset_session():
    s = _get_store()
    for key in s:
        s[key] = 0