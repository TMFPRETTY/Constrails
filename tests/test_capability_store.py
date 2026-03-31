from constrail.capability_store import get_capability_store
from constrail.database import init_db



def setup_module(module):
    init_db()



def test_capability_store_create_and_list_manifest():
    store = get_capability_store()
    created = store.create_manifest(
        agent_id='tenant-agent',
        tenant_id='tenant-a',
        namespace='project-x',
        version=1,
        allowed_tools=[{'tool': 'read_file'}],
        active=True,
    )
    assert created.agent_id == 'tenant-agent'
    rows = store.list_manifests(agent_id='tenant-agent', active=True)
    assert any(row.agent_id == 'tenant-agent' for row in rows)
    assert any(getattr(row, 'tenant_id', None) == 'tenant-a' for row in rows)



def test_capability_store_update_and_activate_manifest():
    store = get_capability_store()
    created = store.create_manifest(
        agent_id='tenant-agent-update',
        tenant_id='tenant-b',
        namespace='project-y',
        version=1,
        allowed_tools=[{'tool': 'read_file'}],
        active=False,
    )
    updated = store.update_manifest_tools(created.id, [{'tool': 'list_directory'}], activate=True)
    assert updated is not None
    assert updated.active is True
    assert updated.allowed_tools == [{'tool': 'list_directory'}]

    bumped = store.create_next_version(created.id, activate=False)
    assert bumped is not None
    activated = store.activate_manifest(bumped.id)
    assert activated is not None
    assert activated.active is True
