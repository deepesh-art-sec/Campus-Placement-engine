"""
Offline output queue generator.
Produces student-facing notification text and recruiter roster exports (CSV and formatted clipboard text).
Ensures absolute offline privacy: no emails or network payloads ever leave the machine.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from backend.app.domain.impact.models import RecruiterRosterExport, StudentNotification
from backend.app.domain.models import Drive, Student
from backend.app.scheduler.models import ScheduledItem


class OutputQueueService:
    """Prepares student notifications and recruiter exports for local use."""

    def generate_student_notifications(
        self,
        drive: Drive,
        students: list[Student],
        schedule_items: list[ScheduledItem],
    ) -> list[StudentNotification]:
        notifications: list[StudentNotification] = []
        student_map = {s.id: s for s in students}

        # Build map of student_id -> list[ScheduledItem]
        student_slots: dict[str, list[ScheduledItem]] = {}
        for it in schedule_items:
            for sid in it.student_ids:
                if sid not in student_slots:
                    student_slots[sid] = []
                student_slots[sid].append(it)

        for sid, items in student_slots.items():
            stu = student_map.get(sid)
            if not stu:
                continue

            sorted_items = sorted(items, key=lambda x: x.start_time)
            primary_slot = sorted_items[0]

            slot_str = f"{primary_slot.start_time.strftime('%Y-%m-%d %H:%M')} - {primary_slot.end_time.strftime('%H:%M')}"
            room_name = primary_slot.room_name
            panel_name = primary_slot.panel_name or "Panel Room"

            msg_body = (
                f"Dear {stu.name} ({stu.roll_no}),\n\n"
                f"You have been successfully shortlisted for the upcoming {drive.company_name} recruitment drive.\n\n"
                f"--- SCHEDULE DETAILS ---\n"
                f"Round: {primary_slot.round_name}\n"
                f"Scheduled Slot: {slot_str}\n"
                f"Room / Venue: {room_name}\n"
                f"Panel: {panel_name}\n\n"
                f"Please report to {room_name} at least 15 minutes prior to your allocated slot with your valid institutional identity card."
            )

            notifications.append(
                StudentNotification(
                    student_id=stu.id,
                    student_roll_no=stu.roll_no,
                    student_email=stu.email,
                    subject=f"[Placement Office] Schedule Confirmation: {drive.company_name} Drive",
                    message=msg_body,
                    scheduled_slot=slot_str,
                    room_name=room_name,
                    panel_name=panel_name,
                )
            )

        return notifications

    def generate_recruiter_export(
        self,
        drive: Drive,
        students: list[Student],
        schedule_items: list[ScheduledItem],
    ) -> RecruiterRosterExport:
        student_map = {s.id: s for s in students}

        rows: list[dict[str, Any]] = []
        for it in sorted(schedule_items, key=lambda x: (x.start_time, x.round_number)):
            slot_str = f"{it.start_time.strftime('%H:%M')}-{it.end_time.strftime('%H:%M')}"
            for sid in it.student_ids:
                stu = student_map.get(sid)
                if stu:
                    rows.append({
                        "Roll No": stu.roll_no,
                        "Candidate Name": stu.name,
                        "Branch": stu.branch,
                        "CGPA": f"{stu.cgpa:.2f}",
                        "Round": it.round_name,
                        "Slot": slot_str,
                        "Venue": it.room_name,
                        "Panel": it.panel_name or "Central Hall",
                    })

        # Generate CSV
        csv_buffer = io.StringIO()
        fieldnames = ["Roll No", "Candidate Name", "Branch", "CGPA", "Round", "Slot", "Venue", "Panel"]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        csv_content = csv_buffer.getvalue()

        # Generate Human-Friendly Clipboard Text
        clip_lines = [
            f"=== {drive.company_name.upper()} RECRUITMENT ROSTER ===",
            f"Date: {drive.drive_date.isoformat()} | Total Candidates: {len(rows)}",
            "-" * 80,
            f"{'ROLL NO':<12} {'CANDIDATE NAME':<24} {'BRANCH':<12} {'CGPA':<6} {'SLOT':<14} {'ROOM':<12}",
            "-" * 80,
        ]

        for r in rows:
            clip_lines.append(
                f"{r['Roll No']:<12} {r['Candidate Name'][:22]:<24} {r['Branch'][:10]:<12} {r['CGPA']:<6} {r['Slot']:<14} {r['Venue']:<12}"
            )

        clip_lines.append("-" * 80)
        clipboard_text = "\n".join(clip_lines)

        return RecruiterRosterExport(
            drive_id=drive.id,
            company_name=drive.company_name,
            drive_date=drive.drive_date,
            total_candidates=len(rows),
            csv_content=csv_content,
            clipboard_text=clipboard_text,
        )
