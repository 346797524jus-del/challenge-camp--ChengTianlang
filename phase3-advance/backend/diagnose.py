"""Diagnose chat flow end-to-end"""
import sys, os, json, traceback
sys.path.insert(0, os.getcwd())

# Load env
from dotenv import load_dotenv
load_dotenv('.env')

print("=== Step 1: Test config loading ===")
from app.config import get_settings
s = get_settings()
print(f"  Base URL: {s.ai_api_base_url}")
print(f"  Model: {s.ai_model_name}")
print(f"  Key prefix: {s.ai_api_key[:8]}...")

print("\n=== Step 2: Test direct OpenAI client ===")
from openai import OpenAI
import httpx
client = OpenAI(
    base_url=s.ai_api_base_url,
    api_key=s.ai_api_key,
    timeout=15,
    max_retries=1,
)
try:
    r = client.chat.completions.create(
        model=s.ai_model_name,
        messages=[{"role": "user", "content": "say hi"}],
        max_tokens=20,
        temperature=0.7,
    )
    print(f"  OK: '{r.choices[0].message.content}'")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")

print("\n=== Step 3: Test process_layer ===")
try:
    from app.pipeline.process_layer import DataProcessingLayer
    from app.pipeline.input_layer import UserIntent
    dl = DataProcessingLayer()
    intent = UserIntent(primary_intent="chat", raw_message="你好")
    from app.pipeline.data_layer import DataSources
    sources = DataSources()
    result = dl.process(intent, sources)
    print(f"  Result: '{result.cleaned_content[:100]}'")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    traceback.print_exc()

print("\n=== Step 4: Test run_stream ===")
try:
    from app.database import init_db, SessionLocal
    init_db()
    db = SessionLocal()
    from app.pipeline.pipeline import AgentPipeline
    pipeline = AgentPipeline()
    import asyncio
    
    async def test_stream():
        count = 0
        async for event in pipeline.run_stream(
            db, "你好", "test_user", "", deep_thinking=False, guide_mode=False
        ):
            count += 1
            evt = event.get("event", "?")
            data = event.get("data", "{}")
            if len(data) > 200:
                data = data[:200] + "..."
            print(f"  event[{count}]: {evt} => {data}")
            if count > 10:
                print("  ... (truncated)")
                break
        print(f"  Total events: {count}")
    
    asyncio.run(test_stream())
    db.close()
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    traceback.print_exc()

print("\n=== Step 5: Test /api/chat endpoint ===")
try:
    import httpx, asyncio
    # First create a session via HTTP
    client = httpx.Client(timeout=30)
    r = client.post("http://localhost:8081/api/sessions", json={"user_id": "test_user"})
    if r.status_code != 200:
        print(f"  Session create failed: {r.status_code} {r.text}")
    else:
        sid = r.json()["id"]
        print(f"  Session: {sid[:8]}")
        r2 = client.post("http://localhost:8081/api/chat", json={
            "session_id": sid, "message": "你好", "user_id": "test_user",
            "deep_thinking": False, "guide_mode": False,
        }, timeout=30)
        print(f"  Chat status: {r2.status_code}")
        d = r2.json()
        print(f"  Keys: {list(d.keys())}")
        print(f"  Message: '{d.get('message', 'NONE')[:200]}'")
        print(f"  Error: '{d.get('error', 'NONE')}'")
        if d.get("thinking_steps"):
            print(f"  Thinking steps: {len(d['thinking_steps'])}")
except Exception as e:
    print(f"  ERROR: need server running first: {e}")

print("\n=== Done ===")