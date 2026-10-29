file_path = "backend/tests/test_api_workflows.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add delete and SlotModel, ScheduleModel to imports if not present
import_target = "from backend.app.storage.models.entities import CompanyModel, DriveModel, StudentModel"
import_replacement = "from sqlalchemy import delete\nfrom backend.app.storage.models.entities import CompanyModel, DriveModel, StudentModel, SlotModel, ScheduleModel"
assert import_target in content, "import target not found"
content = content.replace(import_target, import_replacement, 1)

# Change drive date to 2026, 12, 30
date_target = "drive_date=datetime.date(2026, 11, 20),"
date_replacement = "drive_date=datetime.date(2026, 12, 30),"
assert date_target in content, "date target not found"
content = content.replace(date_target, date_replacement, 1)

# Change setup_pipeline_data signature and add teardown cleanup
fixture_target = '''@pytest.fixture
def setup_pipeline_data() -> tuple[str, str, str]:'''

fixture_replacement = '''@pytest.fixture
def setup_pipeline_data() -> Generator[tuple[str, str, str], None, None]:'''
assert fixture_target in content, "fixture signature target not found"
content = content.replace(fixture_target, fixture_replacement, 1)

return_target = '''    res = (str(d.id), str(s1.id), str(s2.id))
    db.close()
    return res'''

return_replacement = '''    res = (str(d.id), str(s1.id), str(s2.id))
    db.close()
    yield res
    cleanup_db = SessionLocal()
    cleanup_db.execute(delete(SlotModel).where(SlotModel.drive_id == "drv_pipe_01"))
    cleanup_db.execute(delete(ScheduleModel).where(ScheduleModel.id == "sched_drv_pipe_01"))
    cleanup_db.commit()
    cleanup_db.close()'''

assert return_target in content, "return target not found"
content = content.replace(return_target, return_replacement, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("test_api_workflows.py updated successfully!")
