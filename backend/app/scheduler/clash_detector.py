"""
Early clash detection for students shortlisted by multiple companies with overlapping fixed windows.
Flags conflicts prior to scheduling and produces actionable resolution options for TPO officers.
"""

from __future__ import annotations

from backend.app.scheduler.models import SchedulerDrive, StudentClashOption


def detect_student_fixed_window_clashes(
    drives: list[SchedulerDrive],
    student_name_map: dict[str, str] | None = None,
) -> list[StudentClashOption]:
    """
    Identifies students shortlisted for concurrent drives whose company windows overlap.
    Returns structured options so coordinators never silently drop students.
    """
    name_map = student_name_map or {}
    alerts: list[StudentClashOption] = []

    for i in range(len(drives)):
        for j in range(i + 1, len(drives)):
            d1 = drives[i]
            d2 = drives[j]

            # Check if both have fixed company windows and they overlap
            if not d1.fixed_window or not d2.fixed_window:
                continue

            if not d1.fixed_window.overlaps(d2.fixed_window):
                continue

            # Check common shortlisted students
            common_sids = set(d1.shortlisted_student_ids) & set(d2.shortlisted_student_ids)
            if not common_sids:
                continue

            overlap_str = (
                f"{max(d1.fixed_window.start_time, d2.fixed_window.start_time).strftime('%Y-%m-%d %H:%M')} - "
                f"{min(d1.fixed_window.end_time, d2.fixed_window.end_time).strftime('%H:%M')}"
            )

            for sid in sorted(common_sids):
                sname = name_map.get(sid, f"Student {sid}")
                alerts.append(
                    StudentClashOption(
                        student_id=sid,
                        student_name=sname,
                        drive_a_id=d1.id,
                        drive_a_company=d1.company_name,
                        drive_b_id=d2.id,
                        drive_b_company=d2.company_name,
                        overlap_window=overlap_str,
                        suggested_options=[
                            f"Reschedule '{d2.company_name}' to an alternate date or time window.",
                            f"Split shortlisted candidates into morning & afternoon panels to accommodate {sname}.",
                            f"Record {sname}'s drive preference in the portal and re-allocate the non-preferred slot.",
                        ],
                    )
                )

    return alerts
