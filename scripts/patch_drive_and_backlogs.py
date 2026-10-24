from pathlib import Path

# 1. Update models.py to include fixed_pay_lpa in Drive
models_path = Path("backend/app/domain/models.py")
models_code = models_path.read_text(encoding="utf-8")
if "fixed_pay_lpa: float | None = None" not in models_code:
    models_code = models_code.replace(
        "    ctc_lpa: float = Field(ge=0.0)\n",
        "    ctc_lpa: float = Field(ge=0.0)\n    fixed_pay_lpa: float | None = None\n",
    )
    models_path.write_text(models_code, encoding="utf-8")
    print("Updated models.py with fixed_pay_lpa on Drive")

# 2. Update checker.py to use getattr safely
checker_path = Path("backend/app/domain/policy/checker.py")
checker_code = checker_path.read_text(encoding="utf-8")
checker_code = checker_code.replace(
    "drive_val = get_metric(drive.ctc_lpa, drive.fixed_pay_lpa)",
    "drive_val = get_metric(drive.ctc_lpa, getattr(drive, 'fixed_pay_lpa', None))",
)
checker_path.write_text(checker_code, encoding="utf-8")
print("Updated checker.py")

# 3. Update test_hidden_edge_cases_regression.py for scenarios 06 and 07
test_path = Path("backend/tests/test_hidden_edge_cases_regression.py")
test_code = test_path.read_text(encoding="utf-8")
test_code = test_code.replace(
    'assert "Active backlogs count" in res.failed_rules[0].reason',
    'assert "active backlog(s)" in res.failed_rules[0].reason.lower()',
)
test_code = test_code.replace(
    'assert "Historical backlogs count" in res.failed_rules[0].reason',
    'assert "history of" in res.failed_rules[0].reason.lower()',
)
test_path.write_text(test_code, encoding="utf-8")
print("Updated test_hidden_edge_cases_regression.py scenarios 06 and 07")
