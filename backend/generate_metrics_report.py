"""Generate H1-H5 reports from backend/data/metrics.json."""

import csv
import json
import os
from collections import defaultdict
from statistics import median

from database import get_metrics


REPORTS_DIR = os.path.join(os.path.dirname(__file__), "data", "reports")


def _percentile(values, p):
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(float(v) for v in values)
    idx = (len(ordered) - 1) * p
    lower = int(idx)
    upper = min(lower + 1, len(ordered) - 1)
    frac = idx - lower
    return ordered[lower] * (1 - frac) + ordered[upper] * frac


def _write_csv(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_reports(metrics):
    jobs = [m for m in metrics if m.get("type") == "job"]
    events = [m for m in metrics if m.get("type") == "event"]

    # H1: time metrics per workflow
    by_workflow_times = defaultdict(list)
    for job in jobs:
        if isinstance(job.get("total_seconds"), (int, float)):
            by_workflow_times[str(job.get("workflow") or "unknown")].append(float(job["total_seconds"]))
    h1_rows = []
    for workflow, values in sorted(by_workflow_times.items()):
        h1_rows.append(
            {
                "workflow": workflow,
                "runs": len(values),
                "median_seconds": round(median(values), 3),
                "p90_seconds": round(_percentile(values, 0.90), 3),
                "avg_seconds": round(sum(values) / max(1, len(values)), 3),
            }
        )

    # H2: clip quality (available for content maximizer jobs)
    h2_rows = []
    for job in jobs:
        if "h2_clip_quality_score_avg" in job:
            h2_rows.append(
                {
                    "job_id": job.get("job_id"),
                    "workflow": job.get("workflow"),
                    "clip_quality_score_avg": job.get("h2_clip_quality_score_avg", 0.0),
                    "clip_overlap_avg": job.get("h2_clip_overlap_avg", 0.0),
                }
            )

    # H3: process errors from script state transitions
    transitions = [e for e in events if e.get("event_name") == "script_status_transition"]
    invalid_transitions = [e for e in transitions if not bool(e.get("valid"))]
    h3_rows = [
        {
            "total_transitions": len(transitions),
            "invalid_transitions": len(invalid_transitions),
            "invalid_transition_rate": round(
                (len(invalid_transitions) / max(1, len(transitions))) * 100.0, 2
            ),
        }
    ]

    # H4: AI time share by workflow
    h4_rows = []
    for job in jobs:
        stage_seconds = job.get("stage_seconds") or {}
        if not isinstance(stage_seconds, dict):
            continue
        total = float(job.get("total_seconds") or 0.0)
        if total <= 0:
            continue
        ai_stage_keys = ("clips", "blog", "social", "market_research", "psychoanalysis", "creative_brief")
        ai_time = sum(float(stage_seconds.get(k, 0.0)) for k in ai_stage_keys)
        h4_rows.append(
            {
                "job_id": job.get("job_id"),
                "workflow": job.get("workflow"),
                "total_seconds": round(total, 3),
                "ai_seconds": round(ai_time, 3),
                "ai_time_share_percent": round((ai_time / total) * 100.0, 2),
                "gemini_retries": int(job.get("gemini_retries", 0)),
            }
        )

    # H5: post-generation edits in scripts
    created = [e for e in events if e.get("event_name") == "script_created"]
    chapter_updates = [e for e in events if e.get("event_name") == "script_chapters_updated"]
    updates_by_script = defaultdict(int)
    for event in chapter_updates:
        updates_by_script[str(event.get("script_id"))] += 1
    h5_rows = []
    for event in created:
        script_id = str(event.get("script_id"))
        h5_rows.append(
            {
                "script_id": script_id,
                "project_id": event.get("project_id"),
                "chapter_updates_after_creation": updates_by_script.get(script_id, 0),
            }
        )

    summary = {
        "h1_runs_total": sum(row["runs"] for row in h1_rows),
        "h2_jobs_total": len(h2_rows),
        "h3_invalid_transition_rate_percent": h3_rows[0]["invalid_transition_rate"] if h3_rows else 0.0,
        "h4_jobs_total": len(h4_rows),
        "h5_scripts_total": len(h5_rows),
    }

    return {
        "h1": h1_rows,
        "h2": h2_rows,
        "h3": h3_rows,
        "h4": h4_rows,
        "h5": h5_rows,
        "summary": summary,
    }


def main():
    metrics = get_metrics()
    report = build_reports(metrics)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    _write_csv(
        os.path.join(REPORTS_DIR, "h1_times.csv"),
        report["h1"],
        ["workflow", "runs", "median_seconds", "p90_seconds", "avg_seconds"],
    )
    _write_csv(
        os.path.join(REPORTS_DIR, "h2_quality.csv"),
        report["h2"],
        ["job_id", "workflow", "clip_quality_score_avg", "clip_overlap_avg"],
    )
    _write_csv(
        os.path.join(REPORTS_DIR, "h3_process_errors.csv"),
        report["h3"],
        ["total_transitions", "invalid_transitions", "invalid_transition_rate"],
    )
    _write_csv(
        os.path.join(REPORTS_DIR, "h4_ai_share.csv"),
        report["h4"],
        ["job_id", "workflow", "total_seconds", "ai_seconds", "ai_time_share_percent", "gemini_retries"],
    )
    _write_csv(
        os.path.join(REPORTS_DIR, "h5_post_generation_edits.csv"),
        report["h5"],
        ["script_id", "project_id", "chapter_updates_after_creation"],
    )

    summary_path = os.path.join(REPORTS_DIR, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(report["summary"], f, ensure_ascii=False, indent=2)

    print(f"Reports generated in: {REPORTS_DIR}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
