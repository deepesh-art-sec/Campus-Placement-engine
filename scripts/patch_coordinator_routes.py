import os

file_path = "backend/app/api/routes/coordinator_routes.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add imports
import_target = "from backend.app.storage.models.entities import ("
import_replacement = "from backend.app.scheduler.clash_service import count_unresolved_clashes, detect_db_slot_clashes\nfrom backend.app.storage.models.entities import ("
assert import_target in content, "import target not found"
content = content.replace(import_target, import_replacement, 1)

# Replace loop in get_coordinator_overview_metrics
old_loop = """    # Clashes count
    slots = db.execute(select(SlotModel)).scalars().all()
    clashes_count = 0
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            if (
                slots[i].student_id == slots[j].student_id
                and slots[i].start_time == slots[j].start_time
            ):
                clashes_count += 1"""

new_calc = """    # Clashes count
    clashes_count = count_unresolved_clashes(db)"""

assert old_loop in content, "clashes count target not found"
content = content.replace(old_loop, new_calc, 1)

# Add GET /clashes endpoint right before POST /clashes/preference
clash_route_target = """# 5. Clash Preference (Module 6)
# -----------------------------------------------------------------------------

@router.post("/clashes/preference")"""

clash_route_replacement = """# 5. Clash Preference (Module 6)
# -----------------------------------------------------------------------------

@router.get("/clashes")
def get_coordinator_clashes(
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    \"\"\"Retrieves all cross-drive student schedule clashes with resolution status.\"\"\"
    return detect_db_slot_clashes(db)


@router.post("/clashes/preference")"""

assert clash_route_target in content, "clash route target not found"
content = content.replace(clash_route_target, clash_route_replacement, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("coordinator_routes.py updated successfully!")
