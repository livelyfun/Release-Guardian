# 12 — AI ENGINEERING AND EVALUATION

**Status:** Planning-only | **Date:** 2026-10-19

AI is **optional and advisory only**. It never overrides deterministic pass/fail status and never overwrites original test evidence.

## Supported Use Cases

- Assisting with regression diagnosis (correlating evidence across runs/deployments).
- Summarizing failure context for operators.
- Assisting with test-definition authoring (suggestions, human-approved).
- Advanced analytics (advisory).

## Explicitly Prohibited Actions

- Overwriting or mutating deterministic results or original evidence.
- Auto-rolling back production or changing customer infrastructure.
- Executing arbitrary generated code in the control plane.
- Presenting unverified claims as fact.

## Design Requirements

- Model-provider abstraction where useful (avoid lock-in).
- Data redaction before any external model call.
- **Prompt-injection threat model** (untrusted page content, artifacts, logs).
- Evidence citation format for every AI claim.
- Structured output schema (validated).
- Confidence and uncertainty presented explicitly.
- Human-review requirements for high-impact suggestions.
- Defined behavior on insufficient evidence (say so; do not invent).
- Model-version tracking for reproducibility.
- Latency and spending limits enforced.
- Fallback behavior when providers fail.

## Evaluation

- Build a repeatable evaluation set from real or safely anonymized failure cases.
- Measure whether explanations are **supported by evidence**.
- Measure whether the correct failed component is identified.
- Verify the model does not fabricate details.
- Track evaluation results across model versions.

## Safety

- AI output is advisory; deterministic engine remains source of truth.
- All AI actions subject to tenant isolation and access controls.
