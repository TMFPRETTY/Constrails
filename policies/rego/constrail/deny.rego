package constrail.denies

default match := false

match if {
  input.risk.level == "critical"
}

match if {
  input.request.agent.tenant_id == null
}

match if {
  input.request.call.tool == "delete_file"
  startswith(input.request.call.parameters.path, "/")
  not startswith(input.request.call.parameters.path, "/tmp/")
}

decision := {
  "allow": false,
  "decision": "deny",
  "message": "Critical risk, missing tenant scope, or destructive target denied",
  "rule_ids": ["deny_guardrail"]
}
