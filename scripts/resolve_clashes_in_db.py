import sqlite3

conn = sqlite3.connect("placement_engine.db")
c = conn.cursor()

# 1. Delete test slots and schedule for sched_drv_pipe_01
c.execute("DELETE FROM slots WHERE schedule_id = 'sched_drv_pipe_01'")
c.execute("DELETE FROM schedules WHERE id = 'sched_drv_pipe_01'")
print(f"Deleted draft test schedule and slots for sched_drv_pipe_01. Rows affected: {c.rowcount}")

# 2. Reschedule Google slots on 2026-11-21 to afternoon (13:00 - 14:30)
google_updates = [
    ("slot_16dac3977a", "2026-11-21 13:00:00.000000", "2026-11-21 13:30:00.000000"),
    ("slot_4dcb0eb602", "2026-11-21 13:00:00.000000", "2026-11-21 13:30:00.000000"),
    ("slot_7d22270ec1", "2026-11-21 13:30:00.000000", "2026-11-21 14:00:00.000000"),
    ("slot_f15dd0e200", "2026-11-21 13:30:00.000000", "2026-11-21 14:00:00.000000"),
    ("slot_3b1f7a573a", "2026-11-21 14:00:00.000000", "2026-11-21 14:30:00.000000"),
]
for slot_id, st, et in google_updates:
    c.execute("UPDATE slots SET start_time = ?, end_time = ? WHERE id = ?", (st, et, slot_id))
print(f"Updated {len(google_updates)} Google slots to afternoon shift.")

# 3. Reschedule Wipro slot for Arjun Joshi (BT210005) on 2026-11-20
# Cisco is 09:00 - 09:30. Move Wipro slot to 11:30 - 12:00 in room_cabin_101
c.execute("""
    UPDATE slots 
    SET start_time = '2026-11-20 11:30:00.000000', end_time = '2026-11-20 12:00:00.000000'
    WHERE id = 'slot_816286f89e'
""")
print("Updated Wipro slot for Arjun Joshi to 11:30 - 12:00.")

# 4. Reschedule Qualcomm slot for Arjun Joshi (BT210005) on 2026-11-23
# Deloitte is 09:00 - 09:30. Move Qualcomm slot to 11:30 - 12:00 in room_cabin_102
c.execute("""
    UPDATE slots 
    SET start_time = '2026-11-23 11:30:00.000000', end_time = '2026-11-23 12:00:00.000000'
    WHERE id = 'slot_0d4545ea78'
""")
print("Updated Qualcomm slot for Arjun Joshi to 11:30 - 12:00.")

conn.commit()

# Verify remaining clashes
c.execute("""
    SELECT s1.id, s2.id, s1.student_id, s1.drive_id, s2.drive_id, s1.start_time, s1.end_time
    FROM slots s1
    JOIN slots s2 ON s1.student_id = s2.student_id 
                 AND s1.id < s2.id
                 AND max(s1.start_time, s2.start_time) < min(s1.end_time, s2.end_time)
""")
remaining = c.fetchall()
print(f"\nRemaining overlapping clashes across ALL slots in DB: {len(remaining)}")

c.execute("SELECT count(*) FROM slots")
print(f"Total slots in DB now: {c.fetchone()[0]}")
