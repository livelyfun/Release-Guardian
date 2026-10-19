from dataclasses import dataclass, field


@dataclass
class StepOutcome:
    name: str
    status: str
    duration_ms: int
    error: str | None = None
    evidence: dict = field(default_factory=dict)


@dataclass
class CheckOutcome:
    status: str
    duration_ms: int
    steps: list[StepOutcome]
    summary: dict
