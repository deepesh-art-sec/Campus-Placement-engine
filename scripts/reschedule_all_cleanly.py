import sys
sys.path.insert(0, ".")

from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import UserModel, DriveModel, SlotModel
from backend.app.api.routes.schedule_routes import generate_schedule, ScheduleGenerateRequest
from backend.app.scheduler.clash_service import detect_db_slot_clashes, count_unresolved_clashes

db = SessionLocal()
officer = db.query(UserModel).filter(UserModel.role == "officer").first()

# Drives to schedule in logical order
# 1. First mass drives or baseline drives:
drives_to_schedule = [
    "drv_campus_partner",
    "drv_wipro",
    "drv_cisco",
    "drv_tcs",
    "drv_amazon",
    "drv_google",
    "drv_infosys",
    "drv_deloitte",
    "drv_qualcomm",
]

for drive_id in drives_to_schedule:
    drive = db.query(DriveModel).filter(DriveModel.id == drive_id).first()
    if not drive:
        print(f"Drive {drive_id} not found, skipping")
        continue
    print(f"Generating clash-free schedule for {drive.company_name} ({drive.id}) on {drive.drive_date}...")
    try:
        res = generate_schedule(
            req=ScheduleGenerateRequest(drive_id=drive_id),
            current_user=officer,
            db=db,
        )
        print(f"  -> Generated: {res.get('scheduled_items_count')} slots, zero_clashes={res.get('zero_clashes_verified')}, clashes={res.get('clash_count')}")
    except Exception as e:
        print(f"  -> ERROR generating {drive_id}: {e}")

clashes = detect_db_slot_clashes(db)
unresolved = count_unresolved_clashes(db)
print("\n" + "=" * 50)
print(f"FINAL AUDIT RESULT:")
print(f"Total detected clashes in DB: {len(clashes)}")
print(f"Total unresolved clashes in DB: {unresolved}")
for c in clashes:
    print(f"  [{c.get('conflict_type')}] {c.get('student_name')} | {c.get('drive_a_company')} ({c.get('drive_a_time')}) vs {c.get('drive_b_company')} ({c.get('drive_b_time')}) in {c.get('room_name')}")
print("=" * 50)

db.close()
