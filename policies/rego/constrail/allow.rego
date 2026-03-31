package constrail

import data.constrail.approvals
import data.constrail.denies
import data.constrail.sandbox

default allow := {
  "allow": false,
  "decision": "deny",
  "message": "Denied by default",
  "rule_ids": ["default_deny"]
}

allow := denies.decision if denies.match

allow := approvals.decision if approvals.match

allow := sandbox.decision if sandbox.match

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
