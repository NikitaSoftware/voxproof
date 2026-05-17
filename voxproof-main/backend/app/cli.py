#!/usr/bin/env python3
"""VoxProof CLI — run security test suites against voice AI agents."""

import sys
from pathlib import Path
from app.runners.replay_runner import ReplayRunner
from app.db.trace_store import TraceStore
from app.reports.report_generator import ReportGenerator


def main():
    if len(sys.argv) < 2:
        print("VoxProof v0.1.0 — Voice Agent Security Gateway & Test Harness")
        print()
        print("Usage:")
        print("  voxproof run <suite>          Run attack suite against voice agent")
        print("  voxproof report <run_id>      Generate readiness report")
        print("  voxproof runs                 List past runs")
        print()
        print("Example:")
        print("  voxproof run finance_voice_agent")
        sys.exit(0)

    cmd = sys.argv[1]
    runner = ReplayRunner()
    store = TraceStore()
    report_gen = ReportGenerator()

    if cmd == "run":
        suite = sys.argv[2] if len(sys.argv) > 2 else "finance_voice_agent"
        print(f"🔬 Running VoxProof attack suite: {suite}")
        print(f"{'─' * 60}")
        result = runner.run_suite(suite)
        run_id = store.save_run(result)

        for r in result.results:
            symbol = "✅" if r.gate.value == "PASS" else "🔴" if r.gate.value == "FAIL" else "🟡"
            findings = f"({len(r.findings)} findings)" if r.findings else ""
            print(f"  {symbol} [{r.gate.value}] {r.title} {findings}")

        print(f"{'─' * 60}")
        print(f"Trust Score: {result.trust_score}  |  "
              f"PASS: {result.passed}  FAIL: {result.failed}  NEEDS_REVIEW: {result.needs_review}")
        print(f"Run ID: {run_id}")
        print(f"Report: voxproof report {run_id}")

    elif cmd == "report":
        run_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        result = store.get_run(run_id)
        if not result:
            print(f"Run #{run_id} not found.")
            sys.exit(1)
        path = report_gen.save_report(result, f"voxproof_report_{run_id}.html")
        print(f"Report saved: {path}")

    elif cmd == "runs":
        for r in store.list_runs():
            print(f"  #{r['id']}  {r['suite_name']}  {r['created_at']}")


if __name__ == "__main__":
    main()
