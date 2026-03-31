package constrail.sandbox

match if {
  input.risk.level == "high"
}

decision := {
  "allow": false,
  "decision": "sandbox",
  "message": "High risk score requires sandbox",
  "rule_ids": ["sandbox_high_risk"]
}
