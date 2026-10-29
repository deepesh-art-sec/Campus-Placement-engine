import sqlite3

conn = sqlite3.connect("placement_engine.db")
c = conn.cursor()

drives = ["drv_amazon", "drv_google", "drv_cisco", "drv_wipro", "drv_deloitte", "drv_qualcomm"]
for d in drives:
    c.execute("""
        SELECT s.id, s.student_id, st.roll_no, st.name, s.room_id, s.start_time, s.end_time
        FROM slots s
        JOIN students st ON st.id = s.student_id
        WHERE s.drive_id = ?
        ORDER BY s.start_time
    """, (d,))
    rows = c.fetchall()
    print(f"\n--- Drive {d} ({len(rows)} slots) ---")
    for r in rows[:10]:
        print(f"  Slot {r[0]}: {r[2]} ({r[3]}) in {r[4]} from {r[5]} to {r[6]}")
    if len(rows) > 10:
        print(f"  ... and {len(rows) - 10} more slots")
