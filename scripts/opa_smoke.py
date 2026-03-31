import json
import time
import urllib.request
import urllib.error


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


def post_action(payload: dict) -> dict:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/v1/action',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json', 'X-API-Key': 'dev-agent'},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode())


wait_for('http://127.0.0.1:8000/health', timeout_seconds=120)

read_body = post_action(
    {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'read_file', 'parameters': {'path': 'README.md'}},
        'context': {'goal': 'compose opa smoke test read'},
    }
)
assert read_body['decision'] == 'allow', read_body
assert read_body['result']['success'] is True, read_body

exec_body = post_action(
    {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'exec', 'parameters': {'command': 'echo opa-smoke'}},
        'context': {'goal': 'compose opa smoke test exec'},
    }
)
assert exec_body['decision'] in {'approval_required', 'sandbox'}, exec_body

http_body = post_action(
    {
        'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
        'call': {'tool': 'http_request', 'parameters': {'url': 'http://example.com'}},
        'context': {'goal': 'compose opa smoke test plain http'},
    }
)
assert http_body['decision'] in {'sandbox', 'approval_required'}, http_body

payload = {
    'agent': {'agent_id': 'placeholder', 'trust_level': 0.8},
    'call': {'tool': 'delete_file', 'parameters': {'path': '/etc/passwd'}},
    'context': {'goal': 'compose opa smoke test destructive delete'},
}
req = urllib.request.Request(
    'http://127.0.0.1:8000/v1/action',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json', 'X-API-Key': 'dev-agent'},
)
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        delete_body = json.loads(response.read().decode())
except urllib.error.HTTPError as exc:
    delete_body = json.loads(exc.read().decode())

assert delete_body['decision'] == 'deny', delete_body

print(json.dumps({
    'ok': True,
    'read_decision': read_body['decision'],
    'exec_decision': exec_body['decision'],
    'http_decision': http_body['decision'],
    'delete_decision': delete_body['decision'],
    'live_path': 'constrails->opa',
}, indent=2))
