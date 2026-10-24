"""
Algorithmic headline generator for what-if simulation impact reports.
Produces concise, accurate, plain-English executive summaries computed dynamically from live data.
"""

from __future__ import annotations

from backend.app.domain.impact.models import ChangeRequest, ChangeType, StudentClashImpact


def generate_headline(
    change: ChangeRequest,
    added_count: int,
    removed_count: int,
    clashes_count: int,
    clash_sample: StudentClashImpact | None = None,
    second_order_count: int = 0,
) -> str:
    """Generates an institutional executive headline from change parameters and impact metrics."""
    core_phrase = ""

    if change.change_type == ChangeType.CGPA_CUTOFF:
        old_val = float(change.old_value) if change.old_value is not None else 0.0
        new_val = float(change.new_value) if change.new_value is not None else 0.0

        if new_val < old_val:
            noun = "student" if added_count == 1 else "students"
            core_phrase = f"Lowering the CGPA cut-off from {old_val:.1f} to {new_val:.1f} adds {added_count} {noun}"
        else:
            noun = "student" if removed_count == 1 else "students"
            core_phrase = f"Raising the CGPA cut-off from {old_val:.1f} to {new_val:.1f} removes {removed_count} {noun}"

    elif change.change_type == ChangeType.PERCENTAGE_CUTOFF:
        qual = change.target_field or "academic"
        old_val = float(change.old_value) if change.old_value is not None else 0.0
        new_val = float(change.new_value) if change.new_value is not None else 0.0
        if new_val < old_val:
            core_phrase = f"Lowering the {qual} cut-off from {old_val:.1f}% to {new_val:.1f}% adds {added_count} students"
        else:
            core_phrase = f"Raising the {qual} cut-off from {old_val:.1f}% to {new_val:.1f}% removes {removed_count} students"

    elif change.change_type == ChangeType.BRANCH_ADDED:
        b_name = change.branch_name or "new branch"
        core_phrase = f"Adding {b_name} to eligible branches adds {added_count} students"

    elif change.change_type == ChangeType.BRANCH_REMOVED:
        b_name = change.branch_name or "branch"
        core_phrase = f"Removing {b_name} from eligible branches removes {removed_count} students"

    elif change.change_type == ChangeType.BACKLOG_RULE:
        if added_count > 0:
            core_phrase = f"Relaxing the backlog criteria adds {added_count} students"
        elif removed_count > 0:
            core_phrase = f"Restricting the backlog criteria removes {removed_count} students"
        else:
            core_phrase = "Revising the backlog criteria leaves candidate count unchanged"

    elif change.change_type == ChangeType.GAP_YEAR:
        if added_count > 0:
            core_phrase = f"Expanding permissible education gap adds {added_count} students"
        else:
            core_phrase = f"Tightening education gap limit removes {removed_count} students"

    elif change.change_type == ChangeType.DRIVE_DATE_SHIFT:
        core_phrase = f"Shifting drive date from {change.old_value} to {change.new_value}"

    elif change.change_type == ChangeType.MANUAL_STUDENT_ADD:
        core_phrase = f"Manually adding candidate {change.student_id} ({change.mandatory_reason})"

    elif change.change_type == ChangeType.MANUAL_STUDENT_REMOVE:
        core_phrase = f"Manually removing candidate {change.student_id} ({change.mandatory_reason})"

    elif change.change_type == ChangeType.POLICY_TOGGLE:
        toggle = change.toggle_name or "rule toggle"
        core_phrase = f"Switching policy toggle '{toggle}' to {change.new_value}"

    elif change.change_type == ChangeType.PANEL_COUNT:
        core_phrase = f"Adjusting panel allocation to {change.new_value} panels"

    elif change.change_type == ChangeType.ROOM_UNAVAILABLE:
        core_phrase = f"Decommissioning room {change.room_id}"

    else:
        core_phrase = f"Applying revision to {change.drive_id}"

    # Secondary clause: Clashes and second-order impacts
    tail_phrase = ""
    if clashes_count > 0:
        if clash_sample:
            noun = "them" if clashes_count > 1 else "candidate"
            tail_phrase = f"; {clashes_count} of {noun} clash with {clash_sample.conflicting_drive_name} at {clash_sample.conflicting_slot_time}."
        else:
            noun = "clashes" if clashes_count != 1 else "clash"
            tail_phrase = f"; {clashes_count} schedule {noun} detected."
    else:
        tail_phrase = "; 0 clashes detected."

    if second_order_count > 0:
        tail_phrase += f" ({second_order_count} downstream policy interactions identified)."

    return f"{core_phrase}{tail_phrase}"
