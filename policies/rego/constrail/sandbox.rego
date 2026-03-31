package constrail.sandbox

default match := false

match if {
  input.risk.level == "high"
}

match if {
  input.request.call.tool == "exec"
}

match if {
  input.request.call.tool == "http_request"
  startswith(input.request.call.parameters.url, "http://")
}

decision := {
  "allow": false,
  "decision": "sandbox",
  "message": "High-risk execution path requires sandbox",
  "rule_ids": ["sandbox_required"]
}
