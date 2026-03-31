"""
Sandbox executor abstractions for Constrail.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from typing import Optional, Dict, Any

from .config import settings


@dataclass
class SandboxExecutionResult:
    sandbox_id: str
    exit_code: Optional[int]
    stdout: str
    stderr: str
    timeout: bool
    executor: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sandbox_id': self.sandbox_id,
            'exit_code': self.exit_code,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'timeout': self.timeout,
            'executor': self.executor,
        }


class SandboxEnforcementError(RuntimeError):
    pass


class SandboxExecutor:
    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> SandboxExecutionResult:
        raise NotImplementedError


class DevSandboxExecutor(SandboxExecutor):
    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> SandboxExecutionResult:
        sandbox_id = f"dev-sandbox-{uuid.uuid4()}"
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout or settings.sandbox_timeout_seconds,
            )
            return SandboxExecutionResult(
                sandbox_id=sandbox_id,
                exit_code=process.returncode,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                timeout=False,
                executor='dev',
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return SandboxExecutionResult(
                sandbox_id=sandbox_id,
                exit_code=None,
                stdout='',
                stderr='',
                timeout=True,
                executor='dev',
            )


class DockerSandboxExecutor(SandboxExecutor):
    def __init__(self, image: Optional[str] = None):
        self.image = image or settings.sandbox_image

    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> SandboxExecutionResult:
        sandbox_id = f"docker-sandbox-{uuid.uuid4()}"
        docker_timeout = timeout or settings.sandbox_timeout_seconds
        workdir = cwd or '/workspace'
        env_args = []
        if env:
            for key, value in env.items():
                env_args.extend(['-e', f'{key}={value}'])

        docker_host = settings.docker_socket or os.environ.get('DOCKER_HOST')
        prefix = []
        if docker_host:
            prefix = ['env', f'DOCKER_HOST={docker_host}']

        volume_args = []
        host_workspace = os.getcwd()
        mount_mode = 'ro' if settings.sandbox_workspace_mount_readonly else 'rw'
        if os.path.isdir(host_workspace):
            volume_args = ['-v', f'{host_workspace}:/workspace:{mount_mode}']

        network_mode = 'none' if not settings.sandbox_allow_host_network else 'bridge'
        tmpfs_spec = f"/tmp:rw,noexec,nosuid,size={settings.sandbox_tmpfs_size_mb}m"

        cmd = prefix + [
            'docker', 'run', '--rm', '--name', sandbox_id,
            '--network', network_mode,
            '--memory', f'{settings.sandbox_memory_limit_mb}m',
            '--cpus', '0.5',
            '--read-only',
            '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges:true',
            '--pids-limit', '128',
            '--tmpfs', tmpfs_spec,
            '-w', workdir,
            *volume_args,
            *env_args,
            self.image,
            'sh', '-lc', command,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=docker_timeout,
            )
            stderr_text = stderr.decode('utf-8', errors='replace')
            if "Unable to find image" in stderr_text and "Status: Downloaded newer image" in stderr_text:
                stderr_text = ""
            return SandboxExecutionResult(
                sandbox_id=sandbox_id,
                exit_code=process.returncode,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr_text,
                timeout=False,
                executor='docker',
            )
        except FileNotFoundError as e:
            return SandboxExecutionResult(
                sandbox_id=sandbox_id,
                exit_code=None,
                stdout='',
                stderr=f'Docker CLI not available: {e}',
                timeout=False,
                executor='docker',
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return SandboxExecutionResult(
                sandbox_id=sandbox_id,
                exit_code=None,
                stdout='',
                stderr='',
                timeout=True,
                executor='docker',
            )


_default_sandbox_executor: Optional[SandboxExecutor] = None


def reset_sandbox_executor():
    global _default_sandbox_executor
    _default_sandbox_executor = None


def sandbox_health() -> dict[str, Any]:
    sandbox_type = settings.sandbox_type
    docker_path = shutil.which('docker')
    docker_available = docker_path is not None
    image_has_digest = '@sha256:' in settings.sandbox_image
    docker_host = settings.docker_socket or os.environ.get('DOCKER_HOST')

    checks = {
        'docker_mode_enabled': sandbox_type == 'docker',
        'docker_cli_available': docker_available,
        'image_pinned_by_digest': image_has_digest or not settings.sandbox_require_image_digest,
        'workspace_mount_readonly': settings.sandbox_workspace_mount_readonly,
        'host_network_disabled': not settings.sandbox_allow_host_network,
        'tmpfs_configured': settings.sandbox_tmpfs_size_mb > 0,
        'memory_limit_configured': settings.sandbox_memory_limit_mb > 0,
        'timeout_configured': settings.sandbox_timeout_seconds > 0,
        'docker_socket_configured': bool(docker_host) or sandbox_type != 'docker',
    }

    production_ready = all(checks.values())
    warnings = []
    if not checks['docker_mode_enabled']:
        warnings.append('sandbox_type is not docker')
    if not checks['docker_cli_available']:
        warnings.append('docker CLI not found')
    if not checks['image_pinned_by_digest']:
        warnings.append('sandbox image is not pinned by digest')
    if not checks['workspace_mount_readonly']:
        warnings.append('workspace mount is writable')
    if not checks['host_network_disabled']:
        warnings.append('sandbox network is not isolated')
    if not checks['tmpfs_configured']:
        warnings.append('sandbox tmpfs is not configured')
    if not checks['memory_limit_configured']:
        warnings.append('sandbox memory limit is not configured')
    if not checks['timeout_configured']:
        warnings.append('sandbox timeout is not configured')
    if not checks['docker_socket_configured']:
        warnings.append('docker socket/host is not configured')

    return {
        'sandbox_type': sandbox_type,
        'sandbox_mode': settings.sandbox_mode,
        'sandbox_image': settings.sandbox_image,
        'sandbox_image_has_digest': image_has_digest,
        'sandbox_require_image_digest': settings.sandbox_require_image_digest,
        'sandbox_allow_host_network': settings.sandbox_allow_host_network,
        'sandbox_workspace_mount_readonly': settings.sandbox_workspace_mount_readonly,
        'sandbox_tmpfs_size_mb': settings.sandbox_tmpfs_size_mb,
        'sandbox_memory_limit_mb': settings.sandbox_memory_limit_mb,
        'sandbox_timeout_seconds': settings.sandbox_timeout_seconds,
        'docker_cli_found': docker_available,
        'docker_path': docker_path,
        'docker_socket': docker_host,
        'checks': checks,
        'production_ready': production_ready,
        'warnings': warnings,
    }


def enforce_sandbox_posture(operation: str = 'sandboxed execution') -> None:
    if not settings.sandbox_strict_mode:
        return
    health = sandbox_health()
    if health['production_ready']:
        return
    warnings = '; '.join(health['warnings']) if health['warnings'] else 'sandbox posture not production-ready'
    raise SandboxEnforcementError(
        f"Strict sandbox mode blocked {operation}: {warnings}"
    )


def get_sandbox_executor() -> Optional[SandboxExecutor]:
    global _default_sandbox_executor
    if _default_sandbox_executor is not None:
        return _default_sandbox_executor

    if settings.sandbox_type == 'dev':
        _default_sandbox_executor = DevSandboxExecutor()
    elif settings.sandbox_type == 'docker':
        _default_sandbox_executor = DockerSandboxExecutor()
    elif settings.sandbox_type == 'none':
        _default_sandbox_executor = None
    else:
        _default_sandbox_executor = None

    return _default_sandbox_executor
