package constrail

default allow := {
  "allow": false,
  "decision": "deny",
  "message": "Denied by default",
  "rule_ids": ["default_deny"]
}

allow := {
  "allow": true,
  "decision": "allow",
  "message": "Read-only filesystem access allowed",
  "rule_ids": ["allow_read_file"]
} if {
  input.request.call.tool == "read_file"
}

allow := {
  "allow": true,
  "decision": "allow",
  "message": "Directory listing allowed",
  "rule_ids": ["allow_list_directory"]
} if {
  input.request.call.tool == "list_directory"
}

allow := {
  "allow": false,
  "decision": "approval_required",
  "message": "High-risk tool requires approval",
  "rule_ids": ["approval_required_high_risk"]
} if {
  input.request.call.tool in {"exec", "http_request", "write_file", "delete_file"}
}

allow := {
  "allow": false,
  "decision": "sandbox",
  "message": "High risk score requires sandbox",
  "rule_ids": ["sandbox_high_risk"]
} if {
  input.risk.level == "high"
}

allow := {
  "allow": false,
  "decision": "deny",
  "message": "Critical risk denied",
  "rule_ids": ["deny_critical_risk"]
} if {
  input.risk.level == "critical"
}
