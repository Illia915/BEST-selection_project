_session_usage = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "requests": 0,
}

def update_usage(prompt_tokens: int, completion_tokens: int):
    _session_usage["prompt_tokens"] += prompt_tokens
    _session_usage["completion_tokens"] += completion_tokens
    _session_usage["total_tokens"] += prompt_tokens + completion_tokens
    _session_usage["requests"] += 1

def get_session_usage() -> dict:
    return dict(_session_usage)

def reset_session():
    for key in _session_usage:
        _session_usage[key] = 0
