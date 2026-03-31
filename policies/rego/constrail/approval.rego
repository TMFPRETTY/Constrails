package constrail.approvals

high_risk_tools := {"exec", "http_request", "write_file", "delete_file"}

match if {
  input.request.call.tool in high_risk_tools
}

decision := {
  "allow": false,
  "decision": "approval_required",
  "message": "High-risk tool requires approval",
  "rule_ids": ["approval_required_high_risk"]
}
