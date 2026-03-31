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
        if os.path.isdir(host_workspace):
            volume_args = ['-v', f'{host_workspace}:/workspace:ro']

        cmd = prefix + [
            'docker', 'run', '--rm', '--name', sandbox_id,
            '--network', 'none',
            '--memory', f'{settings.sandbox_memory_limit_mb}m',
            '--cpus', '0.5',
            '--read-only',
            '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m',
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
    return {
        'sandbox_type': sandbox_type,
        'sandbox_image': settings.sandbox_image,
        'docker_cli_found': docker_available,
        'docker_path': docker_path,
        'docker_socket': settings.docker_socket or os.environ.get('DOCKER_HOST'),
    }


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
