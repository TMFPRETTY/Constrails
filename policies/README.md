# Constrail bootstrap policies

This directory contains development-time policy inputs for the MVP spine.

## Included

- `capabilities/dev-agent.json` - minimal capability manifest for local bring-up
- `tool_risk_profiles.json` - bootstrap risk model used by the risk engine

## Notes

- Capability manifests are intentionally explicit and fail closed when absent.
- For now, policy evaluation falls back to the built-in simple policy when OPA is unavailable.
- This is bootstrap scaffolding, not the final production policy story.
