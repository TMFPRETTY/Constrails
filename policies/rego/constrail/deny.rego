package constrail.denies

match if {
  input.risk.level == "critical"
}

decision := {
  "allow": false,
  "decision": "deny",
  "message": "Critical risk denied",
  "rule_ids": ["deny_critical_risk"]
}
