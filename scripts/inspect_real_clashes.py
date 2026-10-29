import sqlite3

conn = sqlite3.connect("placement_engine.db")
c = conn.cursor()

c.execute("""
    SELECT s1.id, s2.id, s1.student_id, st.roll_no, st.name, st.branch,
           s1.drive_id, d1.company_name, s1.start_time, s1.end_time,
           s2.drive_id, d2.company_name, s2.start_time, s2.end_time
    FROM slots s1
    JOIN slots s2 ON s1.student_id = s2.student_id 
                 AND s1.start_time = s2.start_time 
                 AND s1.id < s2.id
    JOIN students st ON st.id = s1.student_id
    JOIN drives d1 ON d1.id = s1.drive_id
    JOIN drives d2 ON d2.id = s2.drive_id
    WHERE s1.drive_id != 'drv_pipe_01' AND s2.drive_id != 'drv_pipe_01'
""")
clashes = c.fetchall()
print(f"Non-pipe Clashes ({len(clashes)}):")
for row in clashes:
    print(f"Student: {row[3]} ({row[4]}, {row[5]})")
    print(f"  Drive 1: {row[7]} ({row[6]}) at {row[8]} - {row[9]}")
    print(f"  Drive 2: {row[11]} ({row[10]}) at {row[12]} - {row[13]}")
