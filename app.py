import os
import atexit
import logging
from datetime import timedelta, datetime, time as dt_time
from typing import Optional

from flask import Flask, request, jsonify, render_template, redirect
from psycopg2 import pool
import psycopg2.extras

# ==============================
# CONFIGURATION
# ==============================

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres.jhlsanuygopfwcqpkmqu:arra805048050@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
)


MIN_DB_CONN = 1
MAX_DB_CONN = 10

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("timetalk")

# ==============================
# DATABASE POOL
# ==============================

db_pool: Optional[pool.ThreadedConnectionPool] = None


def init_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = pool.ThreadedConnectionPool(
            MIN_DB_CONN,
            MAX_DB_CONN,
            DATABASE_URL
        )
    return db_pool


def close_db_pool():
    global db_pool
    if db_pool:
        db_pool.closeall()


atexit.register(close_db_pool)
#free sloter
def find_free_slots(tasks, duration):

    slots = []

    start_day = 8 * 60
    end_day = 22 * 60

    for t in tasks:

        start_time = t["start"]
        end_time = t["end_time"]

        # convert time to minutes
        start = start_time.hour * 60 + start_time.minute
        end = end_time.hour * 60 + end_time.minute

        if start - start_day >= duration:
            slots.append({
                "start": f"{start_day//60:02d}:{start_day%60:02d}",
                "end": f"{(start_day+duration)//60:02d}:{(start_day+duration)%60:02d}"
            })

        start_day = end

    if end_day - start_day >= duration:
        slots.append({
            "start": f"{start_day//60:02d}:{start_day%60:02d}",
            "end": f"{(start_day+duration)//60:02d}:{(start_day+duration)%60:02d}"
        })

    return slots


        
      



# ==============================
# DB HELPERS
# ==============================


def get_conn():
    return init_db_pool().getconn()


def release_conn(conn):
    db_pool.putconn(conn)


def fetchall(query, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        release_conn(conn)


def execute(query, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
    finally:
        release_conn(conn)

# ==============================
# DATABASE INIT
# ==============================


def init_schema():
    execute("""
    CREATE TABLE IF NOT EXISTS tasks(
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        day TEXT NOT NULL,
        start TIME NOT NULL,
        end_time TIME NOT NULL,
        priority TEXT DEFAULT 'Medium'
    )
    """)
execute("""
CREATE TABLE IF NOT EXISTS time_debt(
    id SERIAL PRIMARY KEY,
    minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
execute("""
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS deadline DATE
""")

# ==============================
# TIME UTILITIES
# ==============================


def parse_time_str(t):
    return datetime.strptime(t, "%H:%M").time()


def time_to_minutes(t):
    return t.hour * 60 + t.minute


def minutes_to_time_str(m):
    return f"{m//60:02d}:{m%60:02d}"

# ==============================
# VALIDATION
# ==============================

VALID_DAYS = [
    "Monday","Tuesday","Wednesday",
    "Thursday","Friday","Saturday","Sunday"
]

VALID_PRIORITIES = ["Low","Medium","High"]


def validate_day(day):
    if day not in VALID_DAYS:
        raise ValueError("Invalid day")
    return day


def validate_priority(p):
    if p not in VALID_PRIORITIES:
        return "Medium"
    return p

# ==============================
# DATABASE TASK FUNCTIONS
# ==============================


def add_task_db(title, day, start, end, priority):

    execute("""
    INSERT INTO tasks(title,day,start,end_time,priority)
    VALUES(%s,%s,%s,%s,%s)
    """,(title,day,start,end,priority))


def delete_task_db(task_id):
    execute("DELETE FROM tasks WHERE id=%s",(task_id,))


def tasks_by_day_db(day):

    return fetchall("""
    SELECT * FROM tasks
    WHERE day=%s
    ORDER BY start
    """,(day,))

# ==============================
# ROUTES
# ==============================


@app.route("/")
def home():

    today = datetime.today().strftime("%A")
    tasks = tasks_by_day_db(today)

    return render_template(
        "home.html",
        tasks=tasks,
        today=today
    )


@app.route("/schedule")
def schedule():

    data = {d: tasks_by_day_db(d) for d in VALID_DAYS}

    return render_template(
        "schedule.html",
        data=data
    )


@app.route("/add",methods=["GET","POST"])
def add_task():

    if request.method == "POST":

        title = request.form["title"]
        day = validate_day(request.form["day"])

        start = parse_time_str(request.form["start"])
        end = parse_time_str(request.form["end"])

        priority = validate_priority(
            request.form["priority"]
        )

        add_task_db(title,day,start,end,priority)

        return redirect("/schedule")

    return render_template("add.html")


@app.route("/delete/<int:task_id>")
def delete(task_id):

    delete_task_db(task_id)
    return redirect("/schedule")

# ==============================
# ADD AUTO (FROM SLOT)
# ==============================


@app.route("/add_auto",methods=["POST"])
def add_auto():

    try:

        data = request.get_json()

        add_task_db(
            data["title"],
            validate_day(data["day"]),
            parse_time_str(data["start"]),
            parse_time_str(data["end"]),
            validate_priority(data["priority"])
        )

        return jsonify({"status":"ok"})

    except Exception as e:

        return jsonify({"error":str(e)}),400


        #debtttttt
@app.route("/add_debt", methods=["POST"])
def add_debt():

    data = request.get_json()

    hours = int(data.get("hours",0))
    minutes = int(data.get("minutes",0))

    total = hours*60 + minutes

    if total <= 0:
        return jsonify({"msg":"Invalid time"})

    execute("""
    INSERT INTO time_debt(minutes)
    VALUES(%s)
    """,[total])

    return jsonify({"msg":"Debt added"})


#debtt222222222
@app.route("/get_debt")
def get_debt():

    rows = fetchall("SELECT minutes FROM time_debt")

    total = sum(r["minutes"] for r in rows)

    hours = total // 60
    minutes = total % 60

    return jsonify({
        "hours":hours,
        "minutes":minutes
    })
#cancel button for deadline
@app.route("/delete_deadline", methods=["POST"])
def delete_deadline():
    data = request.get_json()
    did = data.get("id")

    if not did:
        return jsonify({"error": "No ID provided"}), 400

    # Note: Ensure you are deleting from 'tasks' because 
    # your 'add_deadline' function inserts into the 'tasks' table.
    execute("""
    DELETE FROM tasks
    WHERE id=%s
    """, [did])

    return jsonify({"msg": "Deadline removed"})


# ==============================
# SLOT FINDER
# ==============================


@app.route("/find_slot",methods=["POST"])
def find_slot():

    data = request.get_json()

    day = validate_day(data["day"])
    duration = int(data["duration"])

    start_range = parse_time_str(data["start"])
    end_range = parse_time_str(data["end"])

    tasks = tasks_by_day_db(day)

    blocks = []

    for t in tasks:

        blocks.append(
            (
                time_to_minutes(t["start"]),
                time_to_minutes(t["end_time"])
            )
        )

    blocks.sort()

    slots = []

    current = time_to_minutes(start_range)

    for s,e in blocks:

        if s - current >= duration:

            slots.append({
                "start":minutes_to_time_str(current),
                "end":minutes_to_time_str(current+duration)
            })

        current = max(current,e)

    if time_to_minutes(end_range)-current >= duration:

        slots.append({
            "start":minutes_to_time_str(current),
            "end":minutes_to_time_str(current+duration)
        })

    return jsonify(slots[:5])



    #dd



#find free slot

def find_free_slots(tasks, duration):
    slots = []

    # Operating hours: 08:00 to 22:00
    day_start = 8 * 60
    day_end = 22 * 60

    current = day_start

    # Loop through existing tasks to find gaps between them
    for t in tasks:
        start_time = t["start"]
        end_time = t["end_time"]

        # Convert datetime.time objects to total minutes
        start = start_time.hour * 60 + start_time.minute
        end = end_time.hour * 60 + end_time.minute

        # Fill gaps found BEFORE the current task starts
        while current + duration <= start:
            slot_start = current
            slot_end = current + duration

            slots.append({
                "start": f"{slot_start//60:02d}:{slot_start%60:02d}",
                "end": f"{slot_end//60:02d}:{slot_end%60:02d}"
            })

            current += duration

        # Move 'current' pointer to the end of the current task
        current = max(current, end)

    # Fill remaining time from the last task until the end of the day
    while current + duration <= day_end:
        slot_start = current
        slot_end = current + duration

        slots.append({
            "start": f"{slot_start//60:02d}:{slot_start%60:02d}",
            "end": f"{slot_end//60:02d}:{slot_end%60:02d}"
        })

        current += duration

    return slots
    #freee lot scheduler

   
   
          

    #auto schduler
@app.route("/auto_schedule", methods=["POST"])
def auto_schedule():
    try:
        data = request.get_json(force=True)
        title = data.get("title")
        hours = int(data.get("hours"))
        deadline = data.get("deadline")

        from datetime import datetime, timedelta

        today = datetime.now().date()
        # Ensure the date format matches what you send from HTML
        deadline_date = datetime.strptime(deadline.split('T')[0], "%Y-%m-%d").date()

        total_minutes = hours * 60
        session = 60 # 1-hour blocks

        days_count = (deadline_date - today).days + 1
        if days_count <= 0:
            return jsonify({"msg": "Deadline passed"})

        sessions_needed = total_minutes // session
        sessions_left = sessions_needed
        inserted = 0

        # Loop through each day from today until the deadline
        for i in range(days_count):
            if sessions_left <= 0:
                break
                
            day_date = today + timedelta(days=i)
            day_name = day_date.strftime("%A")

            # Fetch existing tasks for this specific day
            rows = fetchall("""
                SELECT start, end_time
                FROM tasks
                WHERE day=%s
                ORDER BY start
            """, [day_name])

            tasks = []
            for r in rows:
                tasks.append({
                    "start": r["start"],
                    "end_time": r["end_time"]
                })

            # Logic to find empty space between existing tasks
            free_slots = find_free_slots(tasks, session)

            for slot in free_slots:
                if sessions_left <= 0:
                    break

                execute("""
                    INSERT INTO tasks(title, day, start, end_time, priority)
                    VALUES(%s, %s, %s, %s, %s)
                """, [title, day_name, slot["start"], slot["end"], "Medium"])

                sessions_left -= 1
                inserted += 1

        # SUCCESS RETURN: Must be outside the for-loops
        return jsonify({"msg": f"Success! {inserted} sessions of 1 hour scheduled."})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"msg": str(e)})

      
                 

       

 
           

     
    # ==============================
# SLOT FINDER PAGE
# ==============================

@app.route("/finder")
def finder_page():
    return render_template("finder.html")

    #deadline
@app.route("/deadlines_home")
def deadlines_home():

    rows = fetchall("""
        SELECT id, title, deadline
        FROM tasks
        WHERE deadline IS NOT NULL
        ORDER BY deadline
        LIMIT 5
    """)

    from datetime import date, datetime
    today = date.today()

    result = []

    for r in rows:

        d = r.get("deadline")

        # skip bad rows
        if not d:
            continue

        # convert datetime to date
        if isinstance(d, datetime):
            d = d.date()

        # calculate days
        days_left = (d - today).days

        result.append({
            "id": r.get("id"),
            "title": r.get("title"),
            "deadline": d.strftime("%Y-%m-%d"),
            "days_left": days_left
        })

    return jsonify(result)


    
    #deadline page task 

@app.route("/add_deadline", methods=["POST"])
def add_deadline():
    data = request.json
    try:
        execute("""
            INSERT INTO tasks (title, day, start, end_time, priority, deadline)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data["title"],
            "Deadline",      # Tagging as a deadline
            None,            # No start time for deadlines
            None,            # No end_time for deadlines
            "Medium",        # Default priority
            data["deadline"] # The actual deadline timestamp
        ))
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# ==============================
# WEEKLY AUTO SCHEDULER
# ==============================


@app.route("/weekly_auto", methods=["POST"])
def weekly_auto():

    try:
        data = request.get_json()

        title = data["title"]
        duration = int(data["duration"])
        priority = validate_priority(data["priority"])

        created = 0

        for day in VALID_DAYS:

            tasks = tasks_by_day_db(day)

            blocks = []

            for t in tasks:
                blocks.append(
                    (
                        time_to_minutes(t["start"]),
                        time_to_minutes(t["end_time"])
                    )
                )

            blocks.sort()

            # daily working range
            start_day = 8 * 60
            end_day = 22 * 60

            current = start_day

            for s, e in blocks:

                if s - current >= duration:

                    start_time = minutes_to_time_str(current)
                    end_time = minutes_to_time_str(current + duration)

                    add_task_db(
                        title,
                        day,
                        parse_time_str(start_time),
                        parse_time_str(end_time),
                        priority
                    )

                    created += 1
                    break

                current = max(current, e)

            # if still space after last task
            if end_day - current >= duration:

                start_time = minutes_to_time_str(current)
                end_time = minutes_to_time_str(current + duration)

                add_task_db(
                    title,
                    day,
                    parse_time_str(start_time),
                    parse_time_str(end_time),
                    priority
                )

                created += 1

        return jsonify({"created": created})

    except Exception as e:
        return jsonify({"error": str(e)}), 400
# ==============================
# deadline
# ==============================
@app.route("/deadline")
def deadline_page():

    rows = fetchall("""
        SELECT id,title,deadline
        FROM tasks
        WHERE deadline IS NOT NULL
        ORDER BY deadline
    """)

    tasks = []

    from datetime import datetime,date

    for r in rows:

        d = r["deadline"]

        if isinstance(d, datetime):
            d = d.date()

        tasks.append({
            "id": r["id"],
            "title": r["title"],
            "deadline": d.strftime("%Y-%m-%d")
        })

    return render_template(
        "deadline.html",
        tasks=tasks
    )
# ==============================
# MANUAL WEEKLY TASK
# ==============================

# ==============================
# MANUAL WEEKLY TASK
# ==============================

@app.route("/manual-weekly", methods=["POST"])
def manual_weekly():

    try:
        data = request.get_json()

        title = data["title"]
        start = parse_time_str(data["start"])
        end = parse_time_str(data["end"])
        priority = validate_priority(data["priority"])

        created = 0

        # insert task for every day
        for day in VALID_DAYS:

            add_task_db(
                title,
                day,
                start,
                end,
                priority
            )

            created += 1

        return jsonify({
            "status": "ok",
            "created": created
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400
# TASKS TODAY (NOTIFICATIONS)
# ==============================

@app.route("/tasks_today")
def tasks_today():

    today = datetime.today().strftime("%A")

    rows = tasks_by_day_db(today)

    tasks = []

    for r in rows:

        tasks.append({
            "id": r["id"],
            "title": r["title"],
            "day": r["day"],
            "start": str(r["start"]),
            "end": str(r["end_time"]),
            "priority": r["priority"]
        })

    return jsonify(tasks)

# ==============================
# ANALYTICS
# ==============================


@app.route("/analytics")
def analytics():

    day_data=[]
    hour_data=[]

    for d in VALID_DAYS:

        rows = fetchall(
        "SELECT start,end_time FROM tasks WHERE day=%s",
        (d,)
        )

        day_data.append(len(rows))

        hours=0

        for r in rows:

            hours += (
                time_to_minutes(r["end_time"])
                - time_to_minutes(r["start"])
            )/60

        hour_data.append(round(hours,1))

    priority_rows = fetchall(
        "SELECT priority,COUNT(*) as cnt FROM tasks GROUP BY priority"
    )

    priority_labels=[r["priority"] for r in priority_rows]
    priority_data=[r["cnt"] for r in priority_rows]

    return render_template(
        "analytics.html",
        day_labels=VALID_DAYS,
        day_data=day_data,
        hour_data=hour_data,
        priority_labels=priority_labels,
        priority_data=priority_data
    )

# ==============================
# START SERVER
# ==============================


if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    init_db_pool()
    init_schema()
    app.run(host="0.0.0.0",port=port)