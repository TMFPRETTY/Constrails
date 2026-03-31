# OPA policy bundle

This directory contains example Rego policies for Constrails.

## Package

The default package expected by the current configuration is:

- `constrail`

That maps to OPA queries like:

- `POST /v1/data/constrail/allow`

## Included example

- `constrail/allow.rego`

This policy demonstrates:
- allow for `read_file`
- allow for `list_directory`
- approval-required for risky tools
- sandbox for high risk
- deny for critical risk

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

## Notes

The Python policy engine still includes a built-in fallback path for development if OPA is unavailable.
This directory is the starting point for moving from fallback-only behavior to explicit policy-as-code.
