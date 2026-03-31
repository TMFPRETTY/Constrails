# OPA policy bundle

This directory contains example Rego policies for Constrails.

## Package

The default package expected by the current configuration is:

- `constrail`

That maps to OPA queries like:

- `POST /v1/data/constrail/allow`

## Included example bundle

- `constrail/allow.rego`
- `constrail/approval.rego`
- `constrail/sandbox.rego`
- `constrail/deny.rego`

This starter bundle demonstrates policy separation by concern:
- allow rules for low-risk read/list operations
- approval-required rules for high-risk tools
- sandbox rules for high-risk execution
- deny rules for critical-risk actions

## Running OPA locally

Example:

```bash
opa run --server ./policies/rego
```

Then point Constrails at it:

```bash
export OPA_URL=http://localhost:8181
export OPA_POLICY_PACKAGE=constrail
```

## Query example

```bash
curl -s http://localhost:8181/v1/data/constrail/allow \
  -H 'content-type: application/json' \
  -d @policies/examples/input-example.json
```

## Notes

The Python policy engine still includes a built-in fallback path for development if OPA is unavailable.
This directory is the starting point for moving from fallback-only behavior to explicit policy-as-code with better separation between approval, deny, sandbox, and allow rules.
