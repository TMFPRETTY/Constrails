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

read_payload = {
    'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
    'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
    'context': {'goal': 'compose opa smoke test'},
}
read_req = urllib.request.Request(
    'http://127.0.0.1:8000/v1/action',
    data=json.dumps(read_payload).encode(),
    headers={'Content-Type': 'application/json', 'X-API-Key': 'dev-agent'},
)
with urllib.request.urlopen(read_req, timeout=10) as response:
    read_body = json.loads(response.read().decode())

assert read_body['decision'] == 'allow', read_body
assert read_body['result']['success'] is True, read_body

exec_payload = {
    'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
    'call': {'tool': 'exec', 'parameters': {'command': 'echo opa-smoke'}},
    'context': {'goal': 'compose opa smoke test exec'},
}
exec_req = urllib.request.Request(
    'http://127.0.0.1:8000/v1/action',
    data=json.dumps(exec_payload).encode(),
    headers={'Content-Type': 'application/json', 'X-API-Key': 'dev-agent'},
)
with urllib.request.urlopen(exec_req, timeout=10) as response:
    exec_body = json.loads(response.read().decode())

assert exec_body['decision'] in {'approval_required', 'sandbox'}, exec_body
print(json.dumps({'ok': True, 'read_decision': read_body['decision'], 'exec_decision': exec_body['decision'], 'live_path': 'constrails->opa'}, indent=2))
