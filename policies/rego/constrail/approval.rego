package constrail.approvals

high_risk_tools := {"exec", "shell", "http_request", "write_file", "delete_file", "network"}

match if {
  input.request.call.tool in high_risk_tools
}

match if {
  input.request.call.tool == "http_request"
  not startswith(input.request.call.parameters.url, "https://")
}

match if {
  input.request.call.tool == "write_file"
  startswith(input.request.call.parameters.path, "/etc")
}

decision := {
  "allow": false,
  "decision": "approval_required",
  "message": "High-risk tool or sensitive target requires approval",
  "rule_ids": ["approval_required_high_risk"]
}
