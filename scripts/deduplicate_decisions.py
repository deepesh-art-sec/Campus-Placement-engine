from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import EligibilityDecisionModel
from sqlalchemy import select, func

db = SessionLocal()

# Find all duplicate (drive_id, student_id)
dups = (
    db.query(
        EligibilityDecisionModel.drive_id,
        EligibilityDecisionModel.student_id,
        func.count(EligibilityDecisionModel.id).label("cnt")
    )
    .group_by(EligibilityDecisionModel.drive_id, EligibilityDecisionModel.student_id)
    .having(func.count(EligibilityDecisionModel.id) > 1)
    .all()
)

print(f"Found {len(dups)} duplicate pairs in EligibilityDecisionModel.")
deleted_count = 0

for drive_id, student_id, cnt in dups:
    records = (
        db.query(EligibilityDecisionModel)
        .filter(
            EligibilityDecisionModel.drive_id == drive_id,
            EligibilityDecisionModel.student_id == student_id,
        )
        .order_by(EligibilityDecisionModel.evaluated_at.desc())
        .all()
    )
    # Keep the first (most recent) and delete the rest
    for rec in records[1:]:
        db.delete(rec)
        deleted_count += 1

db.commit()
print(f"Cleaned up {deleted_count} duplicate eligibility decision rows.")

remaining_dups = (
    db.query(EligibilityDecisionModel.drive_id, EligibilityDecisionModel.student_id)
    .group_by(EligibilityDecisionModel.drive_id, EligibilityDecisionModel.student_id)
    .having(func.count(EligibilityDecisionModel.id) > 1)
    .all()
)
print(f"Remaining duplicate pairs: {len(remaining_dups)}")
db.close()
