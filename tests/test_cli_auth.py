from click.testing import CliRunner

from constrail.cli import cli


runner = CliRunner()


def test_auth_status_command():
    result = runner.invoke(cli, ['auth-status'])
    assert result.exit_code == 0
    assert 'Constrail Auth Status' in result.output



def test_auth_status_json_command():
    result = runner.invoke(cli, ['auth-status', '--json'])
    assert result.exit_code == 0
    assert '"agent_role": "agent"' in result.output
    assert '"admin_role": "admin"' in result.output
    assert '"bearer_tokens_enabled": true' in result.output



def test_auth_mint_token_json_command():
    result = runner.invoke(
        cli,
        [
            'auth-mint-token',
            '--role', 'agent',
            '--subject', 'local-agent',
            '--tenant', 'default',
            '--namespace', 'dev',
            '--agent-id', 'dev-agent',
            '--json',
        ],
    )
    assert result.exit_code == 0
    assert '"token":' in result.output
    assert '"issuer": "constrails"' in result.output
    assert '"audience": "constrails-api"' in result.output



def test_auth_inspect_token_json_command():
    minted = runner.invoke(
        cli,
        [
            'auth-mint-token',
            '--role', 'agent',
            '--subject', 'inspect-me',
            '--tenant', 'default',
            '--namespace', 'dev',
            '--agent-id', 'dev-agent',
            '--json',
        ],
    )
    assert minted.exit_code == 0
    token = minted.output.split('"token": "', 1)[1].split('"', 1)[0]

    inspected = runner.invoke(cli, ['auth-inspect-token', token, '--json'])
    assert inspected.exit_code == 0
    assert '"sub": "inspect-me"' in inspected.output
    assert '"aud": "constrails-api"' in inspected.output



def test_auth_revoke_token_json_command():
    minted = runner.invoke(
        cli,
        [
            'auth-mint-token',
            '--role', 'agent',
            '--subject', 'revoke-me',
            '--tenant', 'default',
            '--namespace', 'dev',
            '--agent-id', 'dev-agent',
            '--json',
        ],
    )
    assert minted.exit_code == 0
    token = minted.output.split('"token": "', 1)[1].split('"', 1)[0]

    revoked = runner.invoke(cli, ['auth-revoke-token', token, '--json'])
    assert revoked.exit_code == 0
    assert '"revoked": true' in revoked.output
    assert '"subject": "revoke-me"' in revoked.output



def test_auth_rotate_secret_json_command():
    rotated = runner.invoke(cli, ['auth-rotate-secret', '--json'])
    assert rotated.exit_code == 0
    assert '"rotated": true' in rotated.output
    assert '"previous_secret_preserved": true' in rotated.output
