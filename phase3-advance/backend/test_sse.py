import urllib.request, json
data = json.dumps({'session_id':'','message':'hi','user_id':'test','deep_thinking':False,'guide_mode':False}).encode()
req = urllib.request.Request('http://localhost:8081/api/chat/stream', data=data, headers={'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    with open('e:/tmp_sse.txt', 'wb') as f:
        f.write(raw)
    print('OK bytes:', len(raw))
except Exception as e:
    with open('e:/tmp_sse_err.txt', 'w') as f:
        f.write(f'ERROR: {e}')
    print('ERROR:', e)