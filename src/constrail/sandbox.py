"""
Sandbox executor abstractions for Constrail.
"""

from __future__ import annotations

import asyncio
import os
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
    """Development sandbox executor.

    This is not a production isolation boundary. It exists to preserve the
    sandbox-first control flow while local development is still bringing up
    real containerized execution.
    """

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
    """Docker-backed sandbox executor.

    This is opt-in and requires a reachable Docker daemon.
    """

    def __init__(self, image: str = 'python:3.11-alpine'):
        self.image = image

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

        cmd = prefix + [
            'docker', 'run', '--rm', '--name', sandbox_id,
            '--network', 'none',
            '--memory', f'{settings.sandbox_memory_limit_mb}m',
            '--cpus', '0.5',
            '--read-only',
            '-w', workdir,
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
            return SandboxExecutionResult(
                sandbox_id=sandbox_id,
                exit_code=process.returncode,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
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
