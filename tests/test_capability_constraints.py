from constrail.capability.manager import CapabilityManager
from constrail.models import AgentIdentity


AGENT = AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='dev', trust_level=0.8)


def test_read_path_constraint_allows_repo_readme():
    manager = CapabilityManager()
    assert manager.is_tool_allowed(AGENT, 'read_file', {'path': 'README.md'}) is True


def test_read_path_constraint_blocks_dotdot_escape():
    manager = CapabilityManager()
    assert manager.is_tool_allowed(AGENT, 'read_file', {'path': '../secrets.txt'}) is False


def test_http_domain_constraint_blocks_unknown_domain():
    manager = CapabilityManager()
    assert manager.is_tool_allowed(AGENT, 'http_request', {'url': 'https://evil.example.com'}) is False


def test_exec_command_allowlist_blocks_unapproved_command():
    manager = CapabilityManager()
    assert manager.is_tool_allowed(AGENT, 'exec', {'command': 'rm -rf /'}) is False


def test_namespace_fallback_still_finds_agent_manifest():
    manager = CapabilityManager()
    agent = AgentIdentity(agent_id='dev-agent', tenant_id='default', namespace='other', trust_level=0.8)
    assert manager.is_tool_allowed(agent, 'read_file', {'path': 'README.md'}) is True
