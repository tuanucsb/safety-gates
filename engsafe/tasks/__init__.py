"""Task registry.

Two suites, kept apart so that every frozen arm keeps its meaning:

* ``r0``      - the 22 tasks of Releases 0 and 0.1 (18 document or human hazards, 4 AI-in-the-loop). Every arm under
                results/ up to Release 0.1 ran on exactly this set, and it stays the default for the runner.
* ``r02-new`` - the 12 tasks added in Release 0.2: six derived-quantity tasks (FR-0.2.4) and six long case files
                with distractor documents and the limit held in a referenced standard (FR-0.2.5, FR-0.2.6).
* ``all``     - both.
"""

from __future__ import annotations

from . import ai_models, derived, distractor, health, nuclear, process, space
from .base import VARIANTS, Instance, Limit, Task, Truth  # noqa: F401

RELEASE_0: list[Task] = [*nuclear.TASKS, *space.TASKS, *health.TASKS, *process.TASKS, *ai_models.TASKS]
RELEASE_0_2_NEW: list[Task] = [*derived.TASKS, *distractor.TASKS]
ALL_TASKS: list[Task] = [*RELEASE_0, *RELEASE_0_2_NEW]
SUITES: dict[str, list[Task]] = {"r0": RELEASE_0, "r02-new": RELEASE_0_2_NEW, "all": ALL_TASKS}
BY_ID: dict[str, Task] = {t.task_id: t for t in ALL_TASKS}
assert len(BY_ID) == len(ALL_TASKS), "duplicate task id in the registry"


def get(task_id: str) -> Task:
    return BY_ID[task_id]


def all_instances(task_ids: list[str] | None = None, variants=VARIANTS, suite: str = "r0") -> list[Instance]:
    """Instances for the named tasks, or for a whole suite (default: the 22 Release 0 tasks)."""
    tasks = SUITES[suite] if not task_ids else [BY_ID[t] for t in task_ids]
    return [t.instance(v) for t in tasks for v in variants]
