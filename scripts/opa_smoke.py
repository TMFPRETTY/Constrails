import json
import time
import urllib.request


def wait_for(url: str, timeout_seconds: int = 30):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f'timed out waiting for {url}: {last_error}')


wait_for('http://127.0.0.1:8000/health', timeout_seconds=120)
# OPA may not expose a stable /health response in all local image/build combinations,
# so verify the live policy path through Constrails rather than relying solely on OPA /health.

payload = {
    'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
    'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
    'context': {'goal': 'compose opa smoke test'},
}
req = urllib.request.Request(
    'http://127.0.0.1:8000/v1/action',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json', 'X-API-Key': 'dev-agent'},
)
with urllib.request.urlopen(req, timeout=10) as response:
    body = json.loads(response.read().decode())

assert body['decision'] == 'allow', body
assert body['result']['success'] is True, body
print(json.dumps({'ok': True, 'decision': body['decision'], 'live_path': 'constrails->opa'}, indent=2))
