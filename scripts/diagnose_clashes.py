import sqlite3
import json

conn = sqlite3.connect("placement_engine.db")
c = conn.cursor()

c.execute("SELECT id, company_name, status, drive_date, created_at FROM drives WHERE id = 'drv_pipe_01'")
print("Drive drv_pipe_01:", c.fetchall())

c.execute("SELECT id, name, status, created_at FROM schedules WHERE id = 'sched_drv_pipe_01'")
print("Schedule sched_drv_pipe_01:", c.fetchall())

c.execute("SELECT id, company_name, status, drive_date FROM drives ORDER BY drive_date")
print("\nAll Drives:")
for row in c.fetchall():
    print(row)

c.execute("SELECT id, name, status, drive_ids_json FROM schedules")
print("\nAll Schedules:")
for row in c.fetchall():
    print(row)

c.execute("SELECT id, request_type, title, status, target_id FROM coordinator_requests")
print("\nCoordinator Requests:")
for row in c.fetchall():
    print(row)
