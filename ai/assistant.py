import google.generativeai as genai
import time
from ai.prompts import SYSTEM_PROMPT, get_flight_report_prompt
from ai.pipeline_logger import log_pipeline
from ai.token_counter import update_usage

AVAILABLE_MODELS = {
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
}
DEFAULT_MODEL = "gemini-2.5-flash"

def analyze_flight(metrics, gps_df, api_key, model=DEFAULT_MODEL):
    if not api_key: return {"text": "API key required", "model": model, "prompt_tokens": 0, "completion_tokens": 0}
    
    genai.configure(api_key=api_key)
    llm = genai.GenerativeModel(
        model_name=model,
        system_instruction=SYSTEM_PROMPT
    )
    
    prompt = get_flight_report_prompt(metrics, gps_df)
    start_time = time.time()
    
    try:
        response = llm.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.1)
        )
        duration = time.time() - start_time
        
        text = response.text
        p_tokens = response.usage_metadata.prompt_token_count
        c_tokens = response.usage_metadata.candidates_token_count
        
        update_usage(p_tokens, c_tokens)
        log_pipeline(model, prompt, text, metrics, p_tokens, c_tokens, duration)
        
        return {"text": text, "model": model, "prompt_tokens": p_tokens, "completion_tokens": c_tokens}
    except Exception as e:
        return {"text": f"Error: {str(e)}", "model": model, "prompt_tokens": 0, "completion_tokens": 0}

def analyze_flight_ab(metrics, gps_df, api_key, models, timeout=45):
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
    with ThreadPoolExecutor(max_workers=len(models)) as executor:
        futures = {executor.submit(analyze_flight, metrics, gps_df, api_key, m): m for m in models}
        results = []
        for future, model in futures.items():
            try:
                results.append(future.result(timeout=timeout))
            except FuturesTimeout:
                results.append({"text": f"Timeout after {timeout}s", "model": model, "prompt_tokens": 0, "completion_tokens": 0})
        return results
