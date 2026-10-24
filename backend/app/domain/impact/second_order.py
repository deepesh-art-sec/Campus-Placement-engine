"""
Second-order downstream effect analyzer.
Traces causal interaction chains across drives and offer policies when candidate shortlists change.
Example: Candidate newly eligible for Drive A -> If selected at 10 LPA -> Blocked from Drive B (6 LPA).
"""

from __future__ import annotations

from backend.app.domain.impact.models import SecondOrderEffect
from backend.app.domain.models import Drive, Student
from backend.app.domain.policy.models import CollegeOfferPolicy


class SecondOrderAnalyzer:
    """Analyzes cross-drive policy interactions triggered by shortlist revisions."""

    def trace_downstream_effects(
        self,
        source_drive: Drive,
        newly_eligible_students: list[Student],
        all_drives: list[Drive],
        policy: CollegeOfferPolicy,
    ) -> list[SecondOrderEffect]:
        effects: list[SecondOrderEffect] = []
        source_ctc = source_drive.ctc_lpa

        # Find subsequent drives scheduled on or after source_drive
        subsequent_drives = [
            d for d in all_drives
            if d.id != source_drive.id and d.drive_date >= source_drive.drive_date
        ]

        for stu in newly_eligible_students:
            for target_drive in subsequent_drives:
                # Scenario: Student accepts/receives offer from source_drive
                target_ctc = target_drive.ctc_lpa

                # 1. Progressive Multiplier Policy interaction
                if policy.upgrade_ctc_multiplier > 1.0:
                    multiplier = policy.upgrade_ctc_multiplier
                    threshold_needed = max(policy.dream_threshold_lpa, source_ctc * multiplier)

                    if target_ctc < threshold_needed:
                        chain = (
                            f"Candidate '{stu.name}' ({stu.roll_no}) eligible for '{source_drive.company_name}' ({source_ctc:.1f} LPA). "
                            f"An offer at {source_ctc:.1f} LPA mandates subsequent drives exceed {threshold_needed:.1f} LPA "
                            f"under Clause 2.1 ('Dream Upgrade Multiplier'). Target drive '{target_drive.company_name}' "
                            f"offers {target_ctc:.1f} LPA (< {threshold_needed:.1f} LPA) and will be locked out."
                        )
                        effects.append(
                            SecondOrderEffect(
                                student_id=stu.id,
                                student_name=stu.name,
                                source_drive_id=source_drive.id,
                                source_drive_name=source_drive.company_name,
                                target_drive_id=target_drive.id,
                                target_drive_name=target_drive.company_name,
                                causal_chain=chain,
                                clause_cited="Clause 2.1: Dream Upgrade Multiplier Threshold",
                                action_required=f"Advise student that Drive A offer eliminates eligibility for '{target_drive.company_name}'.",
                            )
                        )

                # 2. Strict One Offer / Standard cap interaction
                elif target_ctc < policy.dream_threshold_lpa or policy.max_total_offers == 1:
                    chain = (
                        f"Candidate '{stu.name}' ({stu.roll_no}) became shortlisted for '{source_drive.company_name}'. "
                        f"Under Clause 1.1 ('Strict One Offer'), an offer from '{source_drive.company_name}' "
                        f"will immediately disqualify candidate from sitting for '{target_drive.company_name}'."
                    )
                    effects.append(
                        SecondOrderEffect(
                            student_id=stu.id,
                            student_name=stu.name,
                            source_drive_id=source_drive.id,
                            source_drive_name=source_drive.company_name,
                            target_drive_id=target_drive.id,
                            target_drive_name=target_drive.company_name,
                            causal_chain=chain,
                            clause_cited="Clause 1.1: Single Offer Cap",
                            action_required="Notify candidate of mandatory lock-in if selected by source drive.",
                        )
                    )

        return effects
