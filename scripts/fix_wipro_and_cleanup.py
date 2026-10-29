import sqlite3

conn = sqlite3.connect("placement_engine.db")
c = conn.cursor()

# 1. Update Wipro slot for Arjun Joshi (stu_bt210005)
c.execute("""
    UPDATE slots 
    SET start_time = '2026-11-20 11:30:00.000000', end_time = '2026-11-20 12:00:00.000000'
    WHERE drive_id = 'drv_wipro' AND student_id = 'stu_bt210005'
""")
print(f"Updated Arjun Joshi's Wipro slot. Rows affected: {c.rowcount}")

# 2. Delete test slots for drv_pipe_01
c.execute("DELETE FROM slots WHERE drive_id = 'drv_pipe_01'")
print(f"Deleted drv_pipe_01 test slots. Rows affected: {c.rowcount}")
c.execute("DELETE FROM schedules WHERE id = 'sched_drv_pipe_01'")

conn.commit()

# Verify clashes
c.execute("""
    SELECT s1.id, s2.id, s1.student_id, s1.drive_id, s2.drive_id, s1.start_time, s1.end_time
    FROM slots s1
    JOIN slots s2 ON s1.student_id = s2.student_id 
                 AND s1.id < s2.id
                 AND max(s1.start_time, s2.start_time) < min(s1.end_time, s2.end_time)
""")
clashes = c.fetchall()
print("Remaining overlapping slot clashes:", len(clashes))
conn.close()
