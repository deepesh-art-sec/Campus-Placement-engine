"""
High-performance explanation templating engine for student and officer communications.
"""

from __future__ import annotations

from typing import Any


class TemplateEngine:
    """Renders formatted explanations for students and officers with high performance."""

    def __init__(self, language: str = "en") -> None:
        self.language = language

    def render_student(self, rule_type: str, status: str, **kwargs: Any) -> str:
        if status == "pass":
            if rule_type == "cgpa_min":
                return f"CGPA requirement met ({kwargs.get('actual', 0.0):.2f} >= {kwargs.get('required', 0.0):.2f})."
            elif rule_type == "percentage_min":
                return f"{kwargs.get('qualification', '')} percentage met ({kwargs.get('actual', 0.0):.2f}% >= {kwargs.get('required', 0.0):.2f}%)."
            elif rule_type == "branch_in":
                return f"Branch requirement met ({kwargs.get('actual', '')} is eligible)."
            elif rule_type == "active_backlogs_max":
                return f"Active backlogs requirement met ({kwargs.get('actual', 0)} <= {kwargs.get('required', 0)})."
            elif rule_type == "historical_backlogs_max":
                return f"Historical backlogs requirement met ({kwargs.get('actual', 0)} <= {kwargs.get('required', 0)})."
            elif rule_type == "gap_years_max":
                return f"Education gap requirement met ({kwargs.get('actual', 0)} <= {kwargs.get('required', 0)})."
            elif rule_type == "age_max":
                return f"Age requirement met ({kwargs.get('actual', 0.0):.1f} <= {kwargs.get('required', 0.0):.1f})."
            elif rule_type == "semester_min":
                return f"Semester criteria met ({kwargs.get('actual', 0)} >= {kwargs.get('required', 0)})."
            elif rule_type == "program_in":
                return f"Program requirement met ({kwargs.get('actual', '')} is eligible)."
            return "Requirement met."

        elif status == "fail":
            if rule_type == "cgpa_min":
                return f"Not eligible: your CGPA is {kwargs.get('actual', 0.0):.2f} and this company needs {kwargs.get('required', 0.0):.2f} or above."
            elif rule_type == "percentage_min":
                return f"Not eligible: your {kwargs.get('qualification', '')} percentage is {kwargs.get('actual', 0.0):.2f}%, below the required {kwargs.get('required', 0.0):.2f}%."
            elif rule_type == "branch_in":
                return f"Not eligible: your branch ({kwargs.get('actual', '')}) is not among the eligible branches ({kwargs.get('required_list', '')})."
            elif rule_type == "active_backlogs_max":
                return f"Not eligible: you have {kwargs.get('actual', 0)} active backlog(s); this company requires at most {kwargs.get('required', 0)}."
            elif rule_type == "historical_backlogs_max":
                return f"Not eligible: you have a history of {kwargs.get('actual', 0)} backlog(s); this company requires clean academic history (max {kwargs.get('required', 0)})."
            elif rule_type == "gap_years_max":
                return f"Not eligible: you have {kwargs.get('actual', 0)} year(s) of education gap; company allows at most {kwargs.get('required', 0)} year(s)."
            elif rule_type == "age_max":
                return f"Not eligible: your age is {kwargs.get('actual', 0.0):.1f} years; company requires age under {kwargs.get('required', 0.0):.1f} years."
            elif rule_type == "semester_min":
                return f"Not eligible: you are in semester {kwargs.get('actual', 0)}; this drive requires semester {kwargs.get('required', 0)} or above."
            elif rule_type == "program_in":
                return f"Not eligible: your program ({kwargs.get('actual', '')}) is not eligible for this drive ({kwargs.get('required_list', '')})."
            return f"Rule {rule_type} failed."

        return f"Needs review: {kwargs.get('message', 'Manual verification required.')}"

    def render_officer(self, rule_id: str, rule_type: str, status: str, data_source: str, **kwargs: Any) -> str:
        msg = self.render_student(rule_type, status, **kwargs)
        return f"[{rule_id}][{status.upper()}] source={data_source} | {msg}"
