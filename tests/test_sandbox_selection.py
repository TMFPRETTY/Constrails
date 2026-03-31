from constrail.config import settings
from constrail.sandbox import DevSandboxExecutor, DockerSandboxExecutor, get_sandbox_executor, reset_sandbox_executor, sandbox_health


class TempSetting:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.original = getattr(settings, name)

    def __enter__(self):
        setattr(settings, self.name, self.value)

    def __exit__(self, exc_type, exc, tb):
        setattr(settings, self.name, self.original)



def test_dev_sandbox_selected_when_configured():
    reset_sandbox_executor()
    with TempSetting('sandbox_type', 'dev'):
        executor = get_sandbox_executor()
        assert isinstance(executor, DevSandboxExecutor)
    reset_sandbox_executor()



def test_docker_sandbox_selected_when_configured():
    reset_sandbox_executor()
    with TempSetting('sandbox_type', 'docker'):
        executor = get_sandbox_executor()
        assert isinstance(executor, DockerSandboxExecutor)
    reset_sandbox_executor()



def test_none_sandbox_returns_none():
    reset_sandbox_executor()
    with TempSetting('sandbox_type', 'none'):
        executor = get_sandbox_executor()
        assert executor is None
    reset_sandbox_executor()



def test_sandbox_health_reports_posture_flags():
    with TempSetting('sandbox_type', 'docker'), TempSetting('sandbox_workspace_mount_readonly', False), TempSetting('sandbox_allow_host_network', True), TempSetting('sandbox_require_image_digest', True), TempSetting('sandbox_image', 'python:3.11-alpine'):
        health = sandbox_health()
        assert health['sandbox_type'] == 'docker'
        assert health['sandbox_require_image_digest'] is True
        assert health['sandbox_allow_host_network'] is True
        assert health['sandbox_workspace_mount_readonly'] is False
        assert health['production_ready'] is False
        assert len(health['warnings']) >= 1
