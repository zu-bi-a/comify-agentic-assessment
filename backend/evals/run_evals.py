from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT_DIR / ".env")

from agents import (  # noqa: E402
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    Runner,
    SQLiteSession,
)

from agents_app import db, observability  # noqa: E402
from agents_app.context import GivaContext  # noqa: E402
from evals.cases import (  # noqa: E402
    CASES,
    GUARDRAIL_PROBES,
    NUDGE_PHRASES,
    EvalCase,
    GuardrailProbeCase,
    all_tool_calls,
    run_guardrail_probe,
)


async def run_case(case: EvalCase) -> tuple[str, list[tuple[str, bool, str]]]:
    session_id = f"eval-{case.id}-{uuid.uuid4().hex[:8]}"
    context = GivaContext(session_id=session_id)
    session = SQLiteSession(session_id=session_id, db_path=":memory:")

    if case.setup:
        await case.setup(context)
    turns = case.turns_factory(context) if case.turns_factory else case.turns

    agent = case.starting_agent
    results = []
    triggered_input_guardrail = False
    triggered_output_guardrail = False
    guardrail_reason = ""

    with observability.eval_trace(f"eval:{case.id}", metadata={"case_id": case.id}):
        try:
            for turn in turns:
                result = await Runner.run(agent, turn, context=context, session=session)
                results.append(result)
                agent = result.last_agent
            if case.until_tool:
                for nudge in NUDGE_PHRASES[: case.max_nudges]:
                    if case.until_tool in all_tool_calls(results):
                        break
                    result = await Runner.run(agent, nudge, context=context, session=session)
                    results.append(result)
                    agent = result.last_agent
        except InputGuardrailTripwireTriggered as exc:
            triggered_input_guardrail = True
            guardrail_reason = str(exc.guardrail_result.output.output_info)
        except OutputGuardrailTripwireTriggered as exc:
            triggered_output_guardrail = True
            guardrail_reason = str(exc.guardrail_result.output.output_info)

        checks: list[tuple[str, bool, str]] = []
        if case.expect_input_guardrail or case.expect_output_guardrail:
            triggered = triggered_input_guardrail if case.expect_input_guardrail else triggered_output_guardrail
            kind = "input" if case.expect_input_guardrail else "output"
            checks.append(
                (
                    f"{kind}_guardrail_triggered",
                    triggered,
                    f"expected the {kind} guardrail to trip; reason: {guardrail_reason}",
                )
            )
            if triggered and case.expected_reason_keywords:
                matched = any(kw.lower() in guardrail_reason.lower() for kw in case.expected_reason_keywords)
                checks.append(
                    (
                        "guardrail_reason_matches_expected_keywords",
                        matched,
                        f"expected one of {case.expected_reason_keywords} in reason: {guardrail_reason}",
                    )
                )
        elif triggered_input_guardrail or triggered_output_guardrail:
            kind = "input" if triggered_input_guardrail else "output"
            checks.append(
                (
                    "no_unexpected_guardrail_trip",
                    False,
                    f"the {kind} guardrail unexpectedly triggered on a benign request; reason: {guardrail_reason}",
                )
            )
        else:
            for check_fn in case.checks:
                checks.extend(await check_fn(results, context))

        for name, passed, detail in checks:
            observability.score_current_trace(f"eval.{name}", passed, detail)

    return case.id, checks


def _print_case(case_id: str, checks: list[tuple[str, bool, str]]) -> bool:
    case_passed = all(passed for _, passed, _ in checks)
    status = "PASS" if case_passed else "FAIL"
    print(f"[{status}] {case_id}")
    for name, passed, detail in checks:
        mark = "  ok " if passed else "  XX "
        print(f"{mark}- {name}: {detail}")
    print()
    return case_passed


async def run_probe(probe: GuardrailProbeCase) -> tuple[str, list[tuple[str, bool, str]]]:
    with observability.eval_trace(f"eval:{probe.id}", metadata={"case_id": probe.id}):
        checks = await run_guardrail_probe(probe)
        for name, passed, detail in checks:
            observability.score_current_trace(f"eval.{name}", passed, detail)
    return probe.id, checks


async def main() -> int:
    observability.setup_observability()
    await db.init_models()

    all_passed = True
    print(f"Running {len(CASES)} eval cases...\n")
    for case in CASES:
        case_id, checks = await run_case(case)
        all_passed = _print_case(case_id, checks) and all_passed

    print(f"Running {len(GUARDRAIL_PROBES)} guardrail probes...\n")
    for probe in GUARDRAIL_PROBES:
        probe_id, checks = await run_probe(probe)
        all_passed = _print_case(probe_id, checks) and all_passed

    print("=" * 60)
    print("ALL PASSED" if all_passed else "SOME FAILED")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
