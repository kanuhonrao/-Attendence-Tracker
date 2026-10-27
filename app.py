import base64
import calendar
import datetime
import hashlib
import json
import math
import os
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Page Configuration (Removed DBIT from title)
st.set_page_config(
    page_title="Attendance & Interactive Calendar Tracker",
    layout="wide",
)

VISITOR_LOG_FILE = "student_visitors_log.csv"
STUDENT_DB_FILE = "saved_students_compact.json"
TIMETABLE_IMG_PATH = "timetable.jpg"

# Exclusive Admin Email (Admin log is ONLY visible when logged in with this email + password)
ADMIN_EMAIL = "honraokanishka@gmail.com"


# --- HELPER FUNCTIONS ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.strip().encode("utf-8")).hexdigest()


def get_ist_now():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    return utc_now + datetime.timedelta(hours=5, minutes=30)


def get_time_greeting():
    hour = get_ist_now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"


def load_all_students_db():
    if os.path.exists(STUDENT_DB_FILE):
        try:
            with open(STUDENT_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_student_compact(
    email,
    name,
    branch,
    batch,
    semesters_dict,
    daily_logs=None,
    daily_slot_ticks=None,
    password_hash=None,
    guide_completed=None,
    target_attendance_pct=None,
):
    db = load_all_students_db()
    key = email.strip().lower()
    existing_rec = db.get(key, {})

    compact_sems = {}
    for sem, df in semesters_dict.items():
        sem_data = {}
        for _, row in df.iterrows():
            unatt_val = int(row["Unattended"]) if "Unattended" in row else 0
            extra_val = int(row["Extra Lectures Attended"]) if "Extra Lectures Attended" in row else 0
            sem_data[row["Course Code"]] = [
                int(row["Importance (1-3)"]),
                unatt_val,
                extra_val,
            ]
        compact_sems[sem] = sem_data

    final_logs = existing_rec.get("daily_logs", {}) if daily_logs is None else daily_logs
    final_ticks = existing_rec.get("daily_slot_ticks", {}) if daily_slot_ticks is None else daily_slot_ticks
    final_pw = existing_rec.get("password_hash", "") if password_hash is None else password_hash
    final_guide = existing_rec.get("guide_completed", False) if guide_completed is None else guide_completed
    final_target = existing_rec.get("target_attendance_pct", 75) if target_attendance_pct is None else target_attendance_pct

    db[key] = {
        "email": key,
        "name": name.strip(),
        "branch": branch,
        "batch": batch,
        "password_hash": final_pw,
        "guide_completed": final_guide,
        "target_attendance_pct": int(final_target),
        "storage_mode": "unattended_v4",
        "last_updated": get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "data": compact_sems,
        "daily_logs": final_logs,
        "daily_slot_ticks": final_ticks,
    }
    with open(STUDENT_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f)


def update_student_visit(email, name, branch, batch):
    ist_time = get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST")
    if os.path.exists(VISITOR_LOG_FILE):
        log_df = pd.read_csv(VISITOR_LOG_FILE)
        if "Batch" not in log_df.columns:
            log_df["Batch"] = "Batch A"
        if "Email" in log_df.columns and email.lower() in log_df["Email"].str.lower().values:
            log_df.loc[
                log_df["Email"].str.lower() == email.lower(),
                ["Student Name", "Branch", "Batch", "Last Login Time"],
            ] = [name.strip(), branch, batch, ist_time]
        else:
            new_row = pd.DataFrame([{
                "Email": email.strip().lower(),
                "Student Name": name.strip(),
                "Branch": branch,
                "Batch": batch,
                "Last Login Time": ist_time,
            }])
            log_df = pd.concat([log_df, new_row], ignore_index=True)
    else:
        log_df = pd.DataFrame([{
            "Email": email.strip().lower(),
            "Student Name": name.strip(),
            "Branch": branch,
            "Batch": batch,
            "Last Login Time": ist_time,
        }])
    log_df.to_csv(VISITOR_LOG_FILE, index=False)


# --- BROWSER LOCALSTORAGE AUTO-LOGIN HELPERS ---
def save_credentials_to_browser(email: str, pw_hash: str):
    components.html(
        f"""
        <script>
        try {{
            localStorage.setItem("att_saved_email", {json.dumps(email)});
            localStorage.setItem("att_saved_token", {json.dumps(pw_hash)});
        }} catch (e) {{}}
        </script>
        """,
        height=0,
    )


def clear_credentials_from_browser():
    components.html(
        """
        <script>
        try {
            localStorage.removeItem("att_saved_email");
            localStorage.removeItem("att_saved_token");
        } catch (e) {}
        </script>
        """,
        height=0,
    )


def attempt_browser_auto_login():
    """Reads saved email + password token from browser localStorage and redirects with URL params."""
    components.html(
        """
        <script>
        (function() {
            try {
                const savedEmail = localStorage.getItem("att_saved_email");
                const savedToken = localStorage.getItem("att_saved_token");
                const urlParams = new URLSearchParams(window.parent.location.search);
                if (savedEmail && savedToken && !urlParams.get("email") && !urlParams.get("logged_out")) {
                    urlParams.set("email", savedEmail);
                    urlParams.set("token", savedToken);
                    window.parent.location.search = urlParams.toString();
                }
            } catch (e) {}
        })();
        </script>
        """,
        height=0,
    )


# --- CONTEXTUAL STEP GUIDE BESIDE LINKED ELEMENT ---
def apply_guide_blur_css():
    st.markdown(
        """
        <style>
        [data-testid="stVerticalBlock"] > div:has(> div.stMarkdown > div > .blur-target-block) {
            filter: blur(8px) brightness(0.38);
            pointer-events: none !important;
            user-select: none !important;
            transition: all 0.25s ease;
        }
        [data-testid="stSidebar"] {
            filter: blur(8px) brightness(0.38);
            pointer-events: none !important;
            user-select: none !important;
        }
        .locked-linked-preview {
            pointer-events: none !important;
            user-select: none !important;
            border: 2px dashed #3b82f6;
            border-radius: 10px;
            padding: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_side_guide_card(step_num, total_steps, title, message, state_key, arrow_dir="left", finish_tour=False):
    arrow_symbol = "&#8592; Linked Section" if arrow_dir == "left" else "&#8593; Linked Section Above"
    st.markdown(
        f"""
        <div id="active-guide-anchor" class="guide-callout-box blinking-guide-window">
            <div class="guide-step-pill">STEP {step_num} OF {total_steps} (ACTION REQUIRED)</div>
            <div style="color:#60a5fa; font-weight:800; font-size:14px; margin-bottom:6px;">
                {arrow_symbol}
            </div>
            <div class="guide-box-title">{title}</div>
            <div class="guide-box-desc">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Got it", key=f"got_it_{state_key}_{step_num}", type="primary", use_container_width=True):
        st.session_state[state_key] += 1
        if finish_tour and st.session_state.get("student_logged_in", False):
            st.session_state.guide_completed = True
            save_student_compact(
                st.session_state.student_email,
                st.session_state.student_name,
                st.session_state.student_branch,
                st.session_state.get("student_batch", "Batch A"),
                st.session_state.saved_semesters,
                st.session_state.daily_logs,
                st.session_state.daily_slot_ticks,
                guide_completed=True,
                target_attendance_pct=st.session_state.get("target_attendance_pct", 75),
            )
        st.rerun()

    components.html(
        """
        <script>
        (function() {
            function scrollToGuide() {
                try {
                    const parentDoc = window.parent.document;
                    const guideEl = parentDoc.getElementById('active-guide-anchor');
                    if (guideEl) {
                        guideEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                } catch (e) {}
            }
            setTimeout(scrollToGuide, 120);
            setTimeout(scrollToGuide, 450);
        })();
        </script>
        """,
        height=0,
    )


# --- GLOBAL CSS ---
st.markdown(
    """
    <style>
    @keyframes blinker {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.25; transform: scale(0.97); }
    }
    @keyframes guidePulse {
        0%, 100% {
            box-shadow: 0 0 12px rgba(59, 130, 246, 0.7), 0 0 28px rgba(37, 99, 235, 0.5);
            border-color: #60a5fa;
            transform: scale(1);
        }
        50% {
            box-shadow: 0 0 26px rgba(59, 130, 246, 1), 0 0 48px rgba(96, 165, 250, 0.95);
            border-color: #ffffff;
            transform: scale(1.015);
        }
    }
    @keyframes blueBtnBlink {
        0%, 100% {
            background-color: #2563eb !important;
            box-shadow: 0 0 10px rgba(37, 99, 235, 0.8);
            border: 2px solid #93c5fd !important;
        }
        50% {
            background-color: #1d4ed8 !important;
            box-shadow: 0 0 24px rgba(96, 165, 250, 1);
            border: 2px solid #ffffff !important;
        }
    }

    button[kind="primary"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        border-radius: 8px !important;
        animation: blueBtnBlink 1.1s infinite ease-in-out !important;
    }
    button[kind="primary"]:hover {
        background-color: #1e40af !important;
        color: #ffffff !important;
    }

    .missed-lectures-banner {
        background: linear-gradient(90deg, #0f172a, #1e3a8a, #0f172a);
        color: #ffffff;
        padding: 14px 20px;
        border: 2px solid #38bdf8;
        border-radius: 8px;
        font-size: 22px;
        font-weight: 900;
        letter-spacing: 1px;
        text-transform: uppercase;
        text-align: center;
        margin-top: 10px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    .blinking-guide-window {
        animation: guidePulse 1.15s infinite ease-in-out;
    }
    .blinking-batch-badge {
        background-color: #dc2626;
        color: #ffffff;
        padding: 3px 8px;
        border-radius: 5px;
        font-weight: 800;
        font-size: 11.5px;
        border: 1px solid #fecaca;
        animation: blinker 1s linear infinite;
        display: inline-block;
        margin-top: 4px;
    }
    .guide-callout-box {
        background: linear-gradient(135deg, #0f172a, #1e3a8a);
        color: #f8fafc;
        border: 3px solid #3b82f6;
        border-radius: 12px;
        padding: 18px 20px;
        position: relative;
        font-family: 'Segoe UI', sans-serif;
        margin-top: 8px;
        margin-bottom: 12px;
        z-index: 99999;
    }
    .guide-step-pill {
        background: #2563eb;
        color: #ffffff;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        letter-spacing: 0.5px;
        display: inline-block;
        margin-bottom: 8px;
        border: 1px solid #93c5fd;
    }
    .guide-box-title {
        font-size: 17px;
        font-weight: 700;
        color: #e0f2fe;
        margin-bottom: 6px;
    }
    .guide-box-desc {
        font-size: 13.5px;
        color: #e2e8f0;
        line-height: 1.45;
        margin-bottom: 8px;
    }
    .cal-legend {
        display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 12px;
        padding: 10px; background: rgba(30, 41, 59, 0.7); border: 1px solid #475569; border-radius: 8px;
    }
    .legend-item { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; }
    .dot-red { width: 14px; height: 14px; background: #ef4444; border-radius: 3px; display: inline-block; }
    .dot-green { width: 14px; height: 14px; background: #22c55e; border-radius: 3px; display: inline-block; }
    .dot-yellow { width: 14px; height: 14px; background: #eab308; border-radius: 3px; display: inline-block; }
    .dot-blue { width: 14px; height: 14px; background: #3b82f6; border-radius: 3px; display: inline-block; }

    .cal-hdr-cell {
        text-align: center;
        font-weight: 800;
        font-size: 13px;
        color: #f8fafc;
        background-color: #1e293b;
        border: 1.5px solid #64748b;
        padding: 8px 4px;
        margin-bottom: 2px;
    }
    .cal-cell {
        border-radius: 0px;
        padding: 8px 4px;
        text-align: center;
        font-weight: 700;
        font-size: 13px;
        min-height: 58px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        border: 1.5px solid #64748b;
        box-sizing: border-box;
    }
    .cal-red { background-color: #ef4444; color: #ffffff; border: 1.5px solid #991b1b; }
    .cal-green { background-color: #22c55e; color: #ffffff; border: 1.5px solid #166534; }
    .cal-yellow { background-color: #eab308; color: #111827; border: 1.5px solid #854d0e; }
    .cal-blue { background-color: #3b82f6; color: #ffffff; border: 1.5px solid #1e40af; }
    .cal-empty {
        background-color: rgba(15, 23, 42, 0.35);
        min-height: 58px;
        border: 1.5px solid #334155;
        box-sizing: border-box;
    }
    .cal-sub { font-size: 10px; font-weight: 800; margin-top: 3px; line-height: 1.1; }

    .vertical-tt-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        font-family: 'Segoe UI', sans-serif;
    }
    .vertical-tt-table th {
        background-color: #1e293b;
        color: #f8fafc;
        font-size: 16px;
        font-weight: 800;
        padding: 14px 12px;
        border: 2px solid #475569;
        text-align: center;
    }
    .vertical-tt-table td {
        padding: 16px 12px;
        border: 2px solid #475569;
        text-align: center;
        vertical-align: middle;
        font-size: 14.5px;
        line-height: 1.45;
        min-height: 74px;
    }
    .tt-slot-col {
        background-color: #0f172a;
        color: #e2e8f0;
        font-weight: 800;
        font-size: 14px;
        width: 15%;
    }
    .tt-cell-green {
        background-color: rgba(34, 197, 94, 0.28);
        color: #bbf7d0;
        font-weight: 700;
    }
    .tt-cell-yellow {
        background-color: rgba(234, 179, 8, 0.32);
        color: #fef08a;
        font-weight: 700;
    }
    .tt-cell-red {
        background-color: #ef4444;
        color: #ffffff;
        font-weight: 800;
        letter-spacing: 0.5px;
    }
    .tt-cell-blue {
        background-color: rgba(59, 130, 246, 0.22);
        color: #bfdbfe;
        font-weight: 600;
    }
    .creator-footer {
        text-align: center;
        margin-top: 40px;
        padding: 18px;
        border-top: 2px solid #334155;
        color: #e2e8f0;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- TIMETABLE DATA ---
TIME_SLOTS = [
    "1 (9:00 - 10:00)",
    "2 (10:00 - 11:00)",
    "Short Break (11:00 - 11:15)",
    "3 (11:15 - 12:15)",
    "4 (12:15 - 13:15)",
    "Lunch Break (13:15 - 14:00)",
    "5 (14:00 - 15:00)",
    "6 (15:00 - 16:00)",
    "7 (16:00 - 17:00)",
]

EVEN_WEEK_TIMETABLE_GRID = {
    "MON": ["AP", "Lab EC (A) / Lab AP (B) / FEM-I Tut (C)", "SHORT BREAK", "FEM-I", "EG", "LUNCH BREAK", "Lab CP (A) / Lab EG (B) / Lab BE&DE (C)", "Lab CP (A) / Lab EG (B) / Lab BE&DE (C)", "Remedial Lecture"],
    "TUE": ["EC", "EG", "SHORT BREAK", "BE&DE", "FEM-I", "LUNCH BREAK", "Lab AP (A) / FEM-I Tut (B) / Lab EC (C)", "UHV", "FE Mentoring Slot"],
    "WED": ["FEM-I Tut (A) / Lab EC (B) / Lab AP (C)", "AP", "SHORT BREAK", "CP", "CP", "LUNCH BREAK", "Workshop-I [WS-I] (A) / Workshop-I [WS-I] (B) / Workshop-I [WS-I] (C)", "Workshop-I [WS-I] (A) / Workshop-I [WS-I] (B) / Workshop-I [WS-I] (C)", "Extra Lecture Slot 1"],
    "THR": ["Lab EG (A) / Lab BE&DE (B) / Lab CP (C)", "Lab EG (A) / Lab BE&DE (B) / Lab CP (C)", "SHORT BREAK", "Lab BE&DE (A) / Lab CP (B) / Lab EG (C)", "Lab BE&DE (A) / Lab CP (B) / Lab EG (C)", "LUNCH BREAK", "BE&DE", "FEM-I", "Extra Lecture Slot 2"],
    "FRI": ["BE&DE", "FEM-I", "SHORT BREAK", "EG", "BE&DE", "LUNCH BREAK", "EC", "UHV", "Extra Lecture Slot 3"],
}

ODD_WEEK_TIMETABLE_GRID = {
    "MON": ["AP", "Lab EC (A) / Lab AP (B) / FEM-I Tut (C)", "SHORT BREAK", "FEM-I", "EG", "LUNCH BREAK", "Lab CP (A) / Lab EG (B) / Lab BE&DE (C)", "Lab CP (A) / Lab EG (B) / Lab BE&DE (C)", "Remedial Lecture"],
    "TUE": ["EC", "BE&DE", "SHORT BREAK", "FEM-I", "AP", "LUNCH BREAK", "Lab AP (A) / FEM-I Tut (B) / Lab EC (C)", "UHV", "FE Mentoring Slot"],
    "WED": ["FEM-I Tut (A) / Lab EC (B) / Lab AP (C)", "EC", "SHORT BREAK", "CP", "CP", "LUNCH BREAK", "Workshop-I [WS-I] (A) / Workshop-I [WS-I] (B) / Workshop-I [WS-I] (C)", "Workshop-I [WS-I] (A) / Workshop-I [WS-I] (B) / Workshop-I [WS-I] (C)", "Extra Lecture Slot 1"],
    "THR": ["Lab EG (A) / Lab BE&DE (B) / Lab CP (C)", "Lab EG (A) / Lab BE&DE (B) / Lab CP (C)", "SHORT BREAK", "Lab BE&DE (A) / Lab CP (B) / Lab EG (C)", "Lab BE&DE (A) / Lab CP (B) / Lab EG (C)", "LUNCH BREAK", "FEM-I", "BE&DE", "Extra Lecture Slot 2"],
    "FRI": ["EC", "BE&DE", "SHORT BREAK", "EG", "BE&DE", "LUNCH BREAK", "FEM-I", "AP", "UHV"],
}

EVEN_WEEK_RANGES = [
    (datetime.date(2026, 9, 21), datetime.date(2026, 9, 25)),
    (datetime.date(2026, 10, 5), datetime.date(2026, 10, 9)),
    (datetime.date(2026, 10, 26), datetime.date(2026, 10, 30)),
    (datetime.date(2026, 11, 9), datetime.date(2026, 11, 13)),
    (datetime.date(2026, 11, 23), datetime.date(2026, 11, 27)),
]

ODD_WEEK_RANGES = [
    (datetime.date(2026, 9, 7), datetime.date(2026, 9, 11)),
    (datetime.date(2026, 9, 28), datetime.date(2026, 10, 2)),
    (datetime.date(2026, 10, 12), datetime.date(2026, 10, 16)),
    (datetime.date(2026, 11, 1), datetime.date(2026, 11, 6)),
    (datetime.date(2026, 11, 16), datetime.date(2026, 11, 20)),
    (datetime.date(2026, 11, 30), datetime.date(2026, 12, 4)),
]


def get_week_type(d: datetime.date):
    for start, end in EVEN_WEEK_RANGES:
        if start <= d <= end:
            return "Even Week"
    for start, end in ODD_WEEK_RANGES:
        if start <= d <= end:
            return "Odd Week"
    return "Even Week" if d.isocalendar()[1] % 2 == 0 else "Odd Week"


def extract_batch_specific_entry(raw_entry: str, batch_letter: str):
    """
    If a timetable slot has batch-separated labs like 'Lab EC (A) / Lab AP (B) / FEM-I Tut (C)',
    returns ONLY the segment for the student's batch (e.g., 'Lab EC (A)') and True.
    """
    if "/" in raw_entry and ("(A)" in raw_entry or "(B)" in raw_entry or "(C)" in raw_entry):
        parts = [p.strip() for p in raw_entry.split("/")]
        for part in parts:
            if f"({batch_letter})" in part:
                return part, True
    return raw_entry, False


def match_subject_short_form(entry_text: str, subject_stats_dict: dict):
    """Matches a single lecture or batch-specific lab string to its subject short form."""
    if "Workshop" in entry_text or "WS-I" in entry_text:
        return "WS-I" if "WS-I" in subject_stats_dict else None
    # Sort by length descending so 'FEM-I' matches before 'EM'
    for sf_code in sorted(subject_stats_dict.keys(), key=len, reverse=True):
        if sf_code in entry_text:
            return sf_code
    return None


SEM1_OFFICIAL_MILESTONES = [
    {"Sr. No.": 1, "Academic Activity / Particulars": "Working days for all FE Engineering Programs", "Scheduled Dates": "07th September to 23rd December 2026"},
    {"Sr. No.": 2, "Academic Activity / Particulars": "FE Orientation", "Scheduled Dates": "12th September 2026"},
    {"Sr. No.": 3, "Academic Activity / Particulars": "Mid-Term Break (Ganesh Festival)", "Scheduled Dates": "14th September to 18th September 2026"},
    {"Sr. No.": 4, "Academic Activity / Particulars": "Mid Semester Examination FE (SEM-I)", "Scheduled Dates": "19th October to 24th October 2026"},
    {"Sr. No.": 5, "Academic Activity / Particulars": "Diwali Break", "Scheduled Dates": "07th November to 10th November 2026"},
    {"Sr. No.": 6, "Academic Activity / Particulars": "Oral/Practical Examination", "Scheduled Dates": "07th December to 12th December 2026"},
    {"Sr. No.": 7, "Academic Activity / Particulars": "End Semester Examination FE (SEM-I)", "Scheduled Dates": "14th December to 23rd December 2026"},
    {"Sr. No.": 8, "Academic Activity / Particulars": "Open House", "Scheduled Dates": "31st December 2026"},
    {"Sr. No.": 9, "Academic Activity / Particulars": "Results Declaration", "Scheduled Dates": "11th January 2027"},
    {"Sr. No.": 10, "Academic Activity / Particulars": "Supplementary Examination FE (SEM-I)", "Scheduled Dates": "01st February to 05th February 2027"},
    {"Sr. No.": 11, "Academic Activity / Particulars": "Commencement of New Term", "Scheduled Dates": "04th January 2027"},
]

SEM1_HOLIDAY_DATES = [
    {"Date": "2026-09-14", "Holiday Name": "Ganeshotsav Break", "Term": "Semester I (FE)"},
    {"Date": "2026-09-15", "Holiday Name": "Ganeshotsav Break", "Term": "Semester I (FE)"},
    {"Date": "2026-09-16", "Holiday Name": "Ganeshotsav Break", "Term": "Semester I (FE)"},
    {"Date": "2026-09-17", "Holiday Name": "Ganeshotsav Break", "Term": "Semester I (FE)"},
    {"Date": "2026-09-18", "Holiday Name": "Ganeshotsav Break", "Term": "Semester I (FE)"},
    {"Date": "2026-10-02", "Holiday Name": "Gandhi Jayanti", "Term": "Semester I (FE)"},
    {"Date": "2026-10-20", "Holiday Name": "Dussehra", "Term": "Semester I (FE)"},
    {"Date": "2026-11-07", "Holiday Name": "Diwali Break", "Term": "Semester I (FE)"},
    {"Date": "2026-11-08", "Holiday Name": "Diwali Break", "Term": "Semester I (FE)"},
    {"Date": "2026-11-09", "Holiday Name": "Diwali Break", "Term": "Semester I (FE)"},
    {"Date": "2026-11-10", "Holiday Name": "Diwali Break", "Term": "Semester I (FE)"},
    {"Date": "2026-11-24", "Holiday Name": "Guru Nanak Jayanti", "Term": "Semester I (FE)"},
]

YEARLY_HOLIDAYS = [
    {"Date": "2026-08-15", "Holiday Name": "Independence Day", "Term": "Odd Semester"},
    {"Date": "2026-10-02", "Holiday Name": "Gandhi Jayanti", "Term": "Odd Semester"},
    {"Date": "2026-10-20", "Holiday Name": "Dussehra", "Term": "Odd Semester"},
    {"Date": "2026-11-09", "Holiday Name": "Diwali", "Term": "Odd Semester"},
    {"Date": "2027-01-26", "Holiday Name": "Republic Day", "Term": "Even Semester"},
    {"Date": "2027-03-22", "Holiday Name": "Holi", "Term": "Even Semester"},
    {"Date": "2027-05-01", "Holiday Name": "Maharashtra Din", "Term": "Even Semester"},
]

SEMESTER_DATA = {
    "Semester I": [
        {"Course Category": "Compulsory", "Course Code": "25FE1BSC01", "Short Form": "FEM-I", "Course Name": "Fundamentals of Engineering Mathematics I", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 45, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1BSC02", "Short Form": "AP", "Course Name": "Applied Physics", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 35, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1BSC03", "Short Form": "EC", "Course Name": "Engineering Chemistry", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 35, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1ESC01", "Short Form": "EG", "Course Name": "Engineering Graphics", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 30, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1ESC02", "Short Form": "BE&DE", "Course Name": "Basic Electrical and Digital Electronics", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1VSEC01", "Short Form": "WS-I", "Course Name": "Workshop - 1", "Credits": 2, "Importance (1-3)": 2, "Total Lectures": 20, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1VSEC02", "Short Form": "CP", "Course Name": "Problem Solving using C programming", "Credits": 2, "Importance (1-3)": 3, "Total Lectures": 30, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1VEC01", "Short Form": "UHV", "Course Name": "Universal Human Values", "Credits": 2, "Importance (1-3)": 1, "Total Lectures": 20, "Unattended": 0, "Extra Lectures Attended": 0},
    ],
    "Semester II": [
        {"Course Category": "Compulsory", "Course Code": "25FE2BSC01", "Short Form": "FEM-II", "Course Name": "Fundamentals of Engineering Mathematics II", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 45, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2BSC02", "Short Form": "AP-II", "Course Name": "Applied Physics II", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 30, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2BSC03", "Short Form": "AC-II", "Course Name": "Applied Chemistry II", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 30, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2ESC01", "Short Form": "EM", "Course Name": "Engineering Mechanics", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2VSEC01", "Short Form": "WS-II", "Course Name": "Workshop - 2", "Credits": 2, "Importance (1-3)": 2, "Total Lectures": 20, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2VSEC02", "Short Form": "PY", "Course Name": "Python Programming", "Credits": 2, "Importance (1-3)": 3, "Total Lectures": 30, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2AEC01", "Short Form": "PCE", "Course Name": "Professional Communication & Ethics", "Credits": 2, "Importance (1-3)": 1, "Total Lectures": 25, "Unattended": 0, "Extra Lectures Attended": 0},
    ],
    "Semester III": [
        {"Course Category": "Compulsory", "Course Code": "25SE3BSC01", "Short Form": "EM-III", "Course Name": "Engineering Mathematics III", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE3PCC01", "Short Form": "DSA", "Course Name": "Data Structures and Algorithms", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE3PCC02", "Short Form": "DBMS", "Course Name": "Database Management Systems", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 35, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE3PCC03", "Short Form": "COA", "Course Name": "Computer Organization & Architecture", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Unattended": 0, "Extra Lectures Attended": 0},
    ],
    "Semester IV": [
        {"Course Category": "Compulsory", "Course Code": "25SE4BSC01", "Short Form": "EM-IV", "Course Name": "Engineering Mathematics IV", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE4PCC01", "Short Form": "AOA", "Course Name": "Analysis of Algorithms", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE4PCC02", "Short Form": "OS", "Course Name": "Operating Systems", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 35, "Unattended": 0, "Extra Lectures Attended": 0},
    ],
    "Semester V": [
        {"Course Category": "Compulsory", "Course Code": "25TE5PCC01", "Short Form": "TCS", "Course Name": "Theory of Computer Science", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE5PCC02", "Short Form": "SE", "Course Name": "Software Engineering", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE5PCC03", "Short Form": "CN", "Course Name": "Computer Networks", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
    ],
    "Semester VI": [
        {"Course Category": "Compulsory", "Course Code": "25TE6PCC01", "Short Form": "SPCC", "Course Name": "System Programming & Compiler Construction", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE6PCC02", "Short Form": "CSS", "Course Name": "Cryptography & System Security", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 35, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE6PCC04", "Short Form": "AI", "Course Name": "Artificial Intelligence", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
    ],
    "Semester VII": [
        {"Course Category": "Compulsory", "Course Code": "25BE7PCC01", "Short Form": "ML", "Course Name": "Machine Learning", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25BE7PCC02", "Short Form": "BDA", "Course Name": "Big Data Analytics", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
    ],
    "Semester VIII": [
        {"Course Category": "Compulsory", "Course Code": "25BE8PCC01", "Short Form": "DC", "Course Name": "Distributed Computing / Cloud Computing", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Unattended": 0, "Extra Lectures Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25BE8PRJ01", "Short Form": "MP-II", "Course Name": "Major Project - II", "Credits": 6, "Importance (1-3)": 3, "Total Lectures": 30, "Unattended": 0, "Extra Lectures Attended": 0},
    ],
}

BRANCH_OPTIONS = [
    "Basic Sciences and Humanities (FE)",
    "Electronics and Telecommunication Engineering",
    "Computer Engineering",
    "Information Technology",
    "Mechanical Engineering",
]

BATCH_OPTIONS = ["Batch A", "Batch B", "Batch C"]


def hydrate_semesters_for_user(user_obj):
    saved_student_data = user_obj.get("data", {})
    mode = user_obj.get("storage_mode", "")
    sem_dict_out = {}
    for sem, courses in SEMESTER_DATA.items():
        temp_df = pd.DataFrame(courses)
        if mode in ["unattended_v3", "unattended_v4"] and sem in saved_student_data:
            sem_dict = saved_student_data[sem]
            for idx, row in temp_df.iterrows():
                code = row["Course Code"]
                tot_lec = int(row["Total Lectures"])
                if code in sem_dict:
                    vals = sem_dict[code]
                    temp_df.loc[idx, "Importance (1-3)"] = vals[0]
                    temp_df.loc[idx, "Unattended"] = min(tot_lec, max(0, int(vals[1])))
                    temp_df.loc[idx, "Extra Lectures Attended"] = vals[2] if len(vals) > 2 else 0
        temp_df.index = range(1, len(temp_df) + 1)
        sem_dict_out[sem] = temp_df
    return sem_dict_out


# --- AUTO-LOGIN VIA URL QUERY PARAMS OR BROWSER LOCALSTORAGE ---
query_params = st.query_params
saved_email = query_params.get("email", "").strip().lower()
saved_token = query_params.get("token", "").strip()

if "student_logged_in" not in st.session_state:
    all_db = load_all_students_db()
    if saved_email and saved_email in all_db:
        user_record = all_db[saved_email]
        stored_pw_hash = user_record.get("password_hash", "")
        # Authenticate automatically if token matches stored password hash (or legacy account without password yet)
        if (stored_pw_hash and saved_token == stored_pw_hash) or (not stored_pw_hash):
            st.session_state.student_logged_in = True
            st.session_state.student_email = user_record.get("email", saved_email)
            st.session_state.student_name = user_record.get("name", "Student")
            st.session_state.student_branch = user_record.get("branch", BRANCH_OPTIONS[0])
            st.session_state.student_batch = user_record.get("batch", BATCH_OPTIONS[0])
            st.session_state.guide_completed = user_record.get("guide_completed", True)
            st.session_state.target_attendance_pct = int(user_record.get("target_attendance_pct", 75))
            # Skip step guide for returning remembered users
            st.session_state.dashboard_guide_step = 99 if st.session_state.guide_completed else 1
        else:
            st.session_state.student_logged_in = False
    else:
        st.session_state.student_logged_in = False

if "login_guide_step" not in st.session_state:
    # Only show login guide if there are no saved users in DB yet, or let user dismiss once
    st.session_state.login_guide_step = 1

if "dashboard_guide_step" not in st.session_state:
    st.session_state.dashboard_guide_step = 99 if st.session_state.get("guide_completed", False) else 1

# Hydrate session state for logged-in student
if st.session_state.get("student_logged_in", False) and "saved_semesters" not in st.session_state:
    email_key = st.session_state.student_email.strip().lower()
    all_db = load_all_students_db()
    user_obj = all_db.get(email_key, {})
    st.session_state.student_batch = user_obj.get("batch", BATCH_OPTIONS[0])
    st.session_state.guide_completed = user_obj.get("guide_completed", True)
    st.session_state.target_attendance_pct = int(user_obj.get("target_attendance_pct", 75))
    st.session_state.daily_logs = user_obj.get("daily_logs", {})
    st.session_state.daily_slot_ticks = user_obj.get("daily_slot_ticks", {})
    st.session_state.saved_semesters = hydrate_semesters_for_user(user_obj)

# --- STEP 0: LOGIN & PASSWORD AUTHENTICATION ---
if not st.session_state.get("student_logged_in", False):
    # Attempt silent auto-login from browser localStorage
    attempt_browser_auto_login()

    st.title("Attendance, Timetable & Calendar Tracker")
    st.subheader("Student Login & Password Verification")
    st.caption("Returning users are remembered automatically on their browser. First-time users: enter your details and set your password.")

    with st.form("student_login_form"):
        input_email = st.text_input("Enter Your Gmail Address (must end with @gmail.com):")
        input_password = st.text_input("Enter Your Password (if new user, this will be saved as your password):", type="password")
        input_name = st.text_input("Enter Your Real Full Name (Required for first-time registration):")
        input_branch = st.selectbox("Select Your Branch:", BRANCH_OPTIONS)
        input_batch = st.selectbox("Select Your College Batch:", BATCH_OPTIONS)
        remember_me = st.checkbox("Remember Me automatically on this browser (Never ask me to login again)", value=True)
        submit_btn = st.form_submit_button("Login / Register & Enter Dashboard")

        if submit_btn:
            clean_email = input_email.strip().lower()
            clean_name = input_name.strip()
            clean_pw = input_password.strip()

            if not clean_email.endswith("@gmail.com"):
                st.error("Invalid email domain. Please use a valid Gmail address ending with '@gmail.com'.")
            elif not clean_pw:
                st.error("Please enter a password to secure your account.")
            else:
                all_db = load_all_students_db()
                pw_hashed = hash_password(clean_pw)
                is_existing_user = clean_email in all_db

                if is_existing_user:
                    user_obj = all_db[clean_email]
                    stored_hash = user_obj.get("password_hash", "")
                    # Verify password if already set; if legacy account had no password, set it now
                    if stored_hash and stored_hash != pw_hashed:
                        st.error("Incorrect password for this Gmail account. Please try again.")
                        st.stop()
                    final_name = clean_name if clean_name else user_obj.get("name", "Student")
                    final_branch = user_obj.get("branch", input_branch)
                    final_batch = user_obj.get("batch", input_batch)
                    # Existing remembered user -> skip the step guide!
                    guide_done = True
                    st.session_state.dashboard_guide_step = 99
                else:
                    if not clean_name:
                        st.error("First-time registration requires your Real Full Name.")
                        st.stop()
                    user_obj = {}
                    final_name = clean_name
                    final_branch = input_branch
                    final_batch = input_batch
                    # Brand new user -> show step guide once
                    guide_done = False
                    st.session_state.dashboard_guide_step = 1

                st.session_state.student_email = clean_email
                st.session_state.student_name = final_name
                st.session_state.student_branch = final_branch
                st.session_state.student_batch = final_batch
                st.session_state.guide_completed = guide_done
                st.session_state.target_attendance_pct = int(user_obj.get("target_attendance_pct", 75))
                st.session_state.student_logged_in = True

                st.session_state.daily_logs = user_obj.get("daily_logs", {})
                st.session_state.daily_slot_ticks = user_obj.get("daily_slot_ticks", {})
                st.session_state.saved_semesters = hydrate_semesters_for_user(user_obj)

                save_student_compact(
                    clean_email,
                    final_name,
                    final_branch,
                    final_batch,
                    st.session_state.saved_semesters,
                    st.session_state.daily_logs,
                    st.session_state.daily_slot_ticks,
                    password_hash=pw_hashed,
                    guide_completed=guide_done,
                    target_attendance_pct=st.session_state.target_attendance_pct,
                )
                update_student_visit(clean_email, final_name, final_branch, final_batch)

                if remember_me:
                    st.query_params.clear()
                    st.query_params["email"] = clean_email
                    st.query_params["token"] = pw_hashed
                    save_credentials_to_browser(clean_email, pw_hashed)
                else:
                    st.query_params.clear()
                    clear_credentials_from_browser()

                st.rerun()

    st.markdown(
        '<div class="creator-footer">Designed and Created by Kanishka Maya Honrao</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# Ensure browser localStorage stays synced when logged in with URL params
if st.query_params.get("email") and st.query_params.get("token"):
    save_credentials_to_browser(st.query_params["email"], st.query_params["token"])

# --- MAIN DASHBOARD ---
active_step = st.session_state.dashboard_guide_step
guide_is_active = (not st.session_state.get("guide_completed", True)) and (active_step in [1, 2, 3, 4])
if guide_is_active:
    apply_guide_blur_css()

greeting = get_time_greeting()
st.title(f"{greeting}, {st.session_state.student_name}")
st.caption(f"**Branch:** {st.session_state.student_branch} | **Batch:** {st.session_state.get('student_batch', 'Batch A')} | **Verified Gmail:** {st.session_state.student_email}")

# --- TOP BAR: DESIRED ATTENDANCE PERCENTAGE INPUT (MINIMUM 75%) ---
st.markdown("### Custom Target Attendance Percentage")
t_col1, t_col2, t_col3 = st.columns([1.6, 1.4, 1])

with t_col1:
    preset_choice = st.radio(
        "Quick Select Desired Attendance %:",
        ["75% (Minimum)", "80%", "85%", "90%", "Custom %"],
        horizontal=True,
        index=0,
        disabled=guide_is_active,
    )

with t_col2:
    preset_map = {"75% (Minimum)": 75, "80%": 80, "85%": 85, "90%": 90}
    default_num_val = preset_map.get(preset_choice, st.session_state.get("target_attendance_pct", 75))
    target_att_pct = st.number_input(
        "Type Desired Attendance % (Min 75%):",
        min_value=75,
        max_value=100,
        value=int(default_num_val),
        step=1,
        disabled=guide_is_active,
    )
    if target_att_pct != st.session_state.get("target_attendance_pct", 75):
        st.session_state.target_attendance_pct = int(target_att_pct)
        save_student_compact(
            st.session_state.student_email,
            st.session_state.student_name,
            st.session_state.student_branch,
            st.session_state.get("student_batch", "Batch A"),
            st.session_state.saved_semesters,
            st.session_state.daily_logs,
            st.session_state.daily_slot_ticks,
            target_attendance_pct=int(target_att_pct),
        )

with t_col3:
    st.write("")
    if st.button("Replay Feature Guide", disabled=guide_is_active, use_container_width=True):
        st.session_state.guide_completed = False
        st.session_state.dashboard_guide_step = 1
        st.rerun()

target_ratio = target_att_pct / 100.0

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Student Profile")
st.sidebar.write(f"**Name:** {st.session_state.student_name}")
st.sidebar.write(f"**Email:** {st.session_state.student_email}")
st.sidebar.write(f"**Branch:** {st.session_state.student_branch}")

current_batch_idx = BATCH_OPTIONS.index(st.session_state.get("student_batch", BATCH_OPTIONS[0])) if st.session_state.get("student_batch") in BATCH_OPTIONS else 0
new_selected_batch = st.sidebar.selectbox("College Batch:", BATCH_OPTIONS, index=current_batch_idx, disabled=guide_is_active)
if new_selected_batch != st.session_state.get("student_batch"):
    st.session_state.student_batch = new_selected_batch
    save_student_compact(
        st.session_state.student_email,
        st.session_state.student_name,
        st.session_state.student_branch,
        st.session_state.student_batch,
        st.session_state.saved_semesters,
        st.session_state.daily_logs,
        st.session_state.daily_slot_ticks,
    )
    st.rerun()

if st.sidebar.button("Switch Student / Logout", disabled=guide_is_active):
    clear_credentials_from_browser()
    st.query_params.clear()
    st.query_params["logged_out"] = "1"
    st.session_state.student_logged_in = False
    st.session_state.pop("saved_semesters", None)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Select Semester")
selected_semester = st.sidebar.selectbox(
    "Choose Semester (1 to 8):",
    list(SEMESTER_DATA.keys()),
    index=0,
    disabled=guide_is_active,
)

if st.sidebar.button(f"Reset {selected_semester} Missed Lectures to 0", disabled=guide_is_active):
    reset_df = pd.DataFrame(SEMESTER_DATA[selected_semester])
    reset_df.index = range(1, len(reset_df) + 1)
    st.session_state.saved_semesters[selected_semester] = reset_df
    st.session_state.daily_logs = {}
    st.session_state.daily_slot_ticks = {}
    save_student_compact(
        st.session_state.student_email,
        st.session_state.student_name,
        st.session_state.student_branch,
        st.session_state.get("student_batch", "Batch A"),
        st.session_state.saved_semesters,
        st.session_state.daily_logs,
        st.session_state.daily_slot_ticks,
    )
    st.rerun()

odd_semesters = ["Semester I", "Semester III", "Semester V", "Semester VII"]
if selected_semester == "Semester I":
    sem_start_date = datetime.date(2026, 9, 7)
    sem_end_date = datetime.date(2026, 12, 23)
    st.sidebar.info("**FE Sem I Official Window:**\n07 Sep 2026 to 23 Dec 2026")
elif selected_semester in odd_semesters:
    sem_start_date = st.sidebar.date_input("Semester Start Date:", value=datetime.date(2026, 7, 15), disabled=guide_is_active)
    sem_end_date = st.sidebar.date_input("Semester End Date:", value=datetime.date(2026, 11, 30), disabled=guide_is_active)
else:
    sem_start_date = st.sidebar.date_input("Semester Start Date:", value=datetime.date(2027, 1, 4), disabled=guide_is_active)
    sem_end_date = st.sidebar.date_input("Semester End Date:", value=datetime.date(2027, 5, 15), disabled=guide_is_active)

target_credits = st.sidebar.number_input(
    f"Target Credits ({selected_semester}):",
    min_value=1,
    max_value=200,
    value=22,
    step=1,
    disabled=guide_is_active,
)


# --- HELPER TO COMPUTE DERIVED COLUMNS USING DYNAMIC TARGET ATTENDANCE % ---
def compute_attendance_metrics(base_df, target_pct_val: int):
    t_ratio = target_pct_val / 100.0
    df = base_df.copy()
    df["Credits"] = pd.to_numeric(df["Credits"], errors="coerce").fillna(3).astype(int)
    df["Importance (1-3)"] = pd.to_numeric(df["Importance (1-3)"], errors="coerce").fillna(2).astype(int)
    df["Total Lectures"] = pd.to_numeric(df["Total Lectures"], errors="coerce").fillna(1).replace(0, 1).astype(int)
    if "Unattended" not in df.columns:
        df["Unattended"] = 0
    df["Unattended"] = pd.to_numeric(df["Unattended"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    df["Unattended"] = df[["Unattended", "Total Lectures"]].min(axis=1)

    if "Extra Lectures Attended" not in df.columns:
        df["Extra Lectures Attended"] = 0
    df["Extra Lectures Attended"] = pd.to_numeric(df["Extra Lectures Attended"], errors="coerce").fillna(0).clip(lower=0).astype(int)

    df["Regular Attended"] = (df["Total Lectures"] - df["Unattended"]).clip(lower=0)
    df["Effective Attended"] = (df["Regular Attended"] + df["Extra Lectures Attended"]).clip(upper=df["Total Lectures"])
    df["Effective Unattended"] = (df["Total Lectures"] - df["Effective Attended"]).clip(lower=0)

    df["Unattended / Total"] = df["Unattended"].astype(str) + " / " + df["Total Lectures"].astype(str)
    df["Current Attendance %"] = ((df["Effective Attended"] / df["Total Lectures"]) * 100).round(2)

    df["Required for Target"] = df["Total Lectures"].apply(lambda tot: math.ceil(t_ratio * tot))
    df["Classes Needed for Target"] = (df["Required for Target"] - df["Effective Attended"]).clip(lower=0)
    df["Max Allowed Bunks"] = df["Total Lectures"] - df["Required for Target"]
    df["Safe Bunks Left"] = (df["Max Allowed Bunks"] - df["Effective Unattended"]).clip(lower=0)
    df["Status"] = df["Current Attendance %"].apply(
        lambda x: f"Safe (>={target_pct_val}%)" if x >= target_pct_val else f"Shortage (<{target_pct_val}%)"
    )
    return df


# --- SECTION 1: INTERACTIVE SUBJECT TABLE ---
sec1_wrapper = st.container()
with sec1_wrapper:
    if guide_is_active and active_step in [2, 3, 4]:
        st.markdown('<div class="blur-target-block"></div>', unsafe_allow_html=True)

    st.subheader(f"1. {selected_semester} Subjects & Unattended Lectures Input")
    st.markdown(
        '<div class="missed-lectures-banner">ENTER HOW MANY LECTURES YOU HAVE MISSED</div>',
        unsafe_allow_html=True,
    )
    st.caption("Double-click **Unattended** (missed lectures, default 0), **Extra Lectures Attended**, or **Importance (1-3)** to update. Synced with Section 3 Calendar Ticks and Section 4.")

    if guide_is_active and active_step == 1:
        s1_col_main, s1_col_guide = st.columns([2.2, 1])
    else:
        s1_col_main = st.container()
        s1_col_guide = None

    with s1_col_main:
        current_sem_df = st.session_state.saved_semesters[selected_semester]
        sec1_disabled_cols = (
            list(current_sem_df.columns)
            if guide_is_active
            else ["Course Category", "Course Code", "Short Form", "Course Name", "Credits", "Total Lectures"]
        )
        edited_sec1 = st.data_editor(
            current_sem_df,
            num_rows="fixed",
            disabled=sec1_disabled_cols,
            column_config={
                "Unattended": st.column_config.NumberColumn("Unattended Lectures (Missed)", min_value=0, default=0, step=1),
                "Extra Lectures Attended": st.column_config.NumberColumn("Extra Lectures Attended", min_value=0, default=0, step=1),
            },
            use_container_width=True,
            key=f"sec1_editor_{selected_semester}",
        )

        if not guide_is_active and not edited_sec1.equals(current_sem_df):
            st.session_state.saved_semesters[selected_semester] = edited_sec1.copy()
            save_student_compact(
                st.session_state.student_email,
                st.session_state.student_name,
                st.session_state.student_branch,
                st.session_state.get("student_batch", "Batch A"),
                st.session_state.saved_semesters,
                st.session_state.daily_logs,
                st.session_state.daily_slot_ticks,
            )
            st.rerun()

    if s1_col_guide is not None:
        with s1_col_guide:
            render_side_guide_card(
                1,
                4,
                "Step 1: Enter How Many Lectures You Have Missed",
                "This arrow points to Section 1. Enter any lectures you have missed in 'Unattended' and any 'Extra Lectures Attended'. Click the blinking blue 'Got it' button below to proceed.",
                "dashboard_guide_step",
                arrow_dir="left",
            )

df = compute_attendance_metrics(st.session_state.saved_semesters[selected_semester], target_att_pct)

subject_stats_by_short = {}
for _, r in df.iterrows():
    sf = r["Short Form"]
    subject_stats_by_short[sf] = {
        "code": r["Course Code"],
        "name": r["Course Name"],
        "unattended": int(r["Unattended"]),
        "regular_attended": int(r["Regular Attended"]),
        "extra": int(r["Extra Lectures Attended"]),
        "effective": int(r["Effective Attended"]),
        "total": int(r["Total Lectures"]),
        "pct": float(r["Current Attendance %"]),
        "req_target": int(r["Required for Target"]),
        "needed": int(r["Classes Needed for Target"]),
        "bunks": int(r["Safe Bunks Left"]),
    }

# --- SECTION 2: DASHBOARD METRICS ---
sec2_wrapper = st.container()
with sec2_wrapper:
    if guide_is_active:
        st.markdown('<div class="blur-target-block"></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(f"2. {selected_semester} {target_att_pct}% Target Summary (Based on Unattended & Extra Lectures)")

    overall_att = (df["Effective Attended"].sum() / df["Total Lectures"].sum()) * 100
    total_unattended = int(df["Unattended"].sum())
    total_safe_bunks = int(df["Safe Bunks Left"].sum())
    total_classes_needed = int(df["Classes Needed for Target"].sum())

    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Overall Attendance (with Extra)", f"{overall_att:.2f}%", delta=f"Safe (>={target_att_pct}%)" if overall_att >= target_att_pct else f"Below {target_att_pct}%", delta_color="normal" if overall_att >= target_att_pct else "inverse")
    mcol2.metric("Total Unattended Lectures (Detected)", f"{total_unattended} missed")
    mcol3.metric(f"Safe Bunks Left (for {target_att_pct}%)", f"{total_safe_bunks} bunks left")
    mcol4.metric(f"Classes Needed for {target_att_pct}%", f"{total_classes_needed} classes")

# --- SECTION 3: TABLE-BORDERED COMPACT CALENDAR & DAY CLICK INSPECTOR WITH UNATTENDED TICK ---
sec3_wrapper = st.container()
with sec3_wrapper:
    if guide_is_active and active_step in [1, 3, 4]:
        st.markdown('<div class="blur-target-block"></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(f"3. Interactive Table-Bordered Calendar & Daily Unattended Tick ({selected_semester})")

    if guide_is_active and active_step == 2:
        s3_col_main, s3_col_guide = st.columns([2.2, 1])
    else:
        s3_col_main = st.container()
        s3_col_guide = None

    with s3_col_main:
        active_holidays_list = SEM1_HOLIDAY_DATES if selected_semester == "Semester I" else YEARLY_HOLIDAYS
        holiday_map = {datetime.date.fromisoformat(h["Date"]): h["Holiday Name"] for h in active_holidays_list}
        today_date = get_ist_now().date()

        st.markdown(
            """
            <div class="cal-legend">
                <div class="legend-item"><span class="dot-red"></span> Red: Holiday & Weekends (Sat/Sun)</div>
                <div class="legend-item"><span class="dot-green"></span> Green: Past Day (All Attended / 0 Missed)</div>
                <div class="legend-item"><span class="dot-yellow"></span> Yellow: Past Unattended ('F' = Full Bunk / Short-Form = Missed Lectures)</div>
                <div class="legend-item"><span class="dot-blue"></span> Blue: Normal Working Day</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cal_months = [
            ("September 2026", 2026, 9),
            ("October 2026", 2026, 10),
            ("November 2026", 2026, 11),
            ("December 2026", 2026, 12),
        ] if selected_semester == "Semester I" else [
            ("July 2026", 2026, 7),
            ("August 2026", 2026, 8),
            ("September 2026", 2026, 9),
            ("October 2026", 2026, 10),
            ("November 2026", 2026, 11),
        ]

        if "selected_cal_date" not in st.session_state:
            st.session_state.selected_cal_date = today_date

        cal_col_left, cal_col_right = st.columns([1.25, 1.15])

        with cal_col_left:
            chosen_month_label = st.selectbox(
                "Select Month:",
                [m[0] for m in cal_months],
                index=1 if len(cal_months) > 1 else 0,
                disabled=guide_is_active,
            )
            _, c_year, c_month = next(m for m in cal_months if m[0] == chosen_month_label)

            hdr_cols = st.columns(7, gap="small")
            for idx, d_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                hdr_cols[idx].markdown(f"<div class='cal-hdr-cell'>{d_name}</div>", unsafe_allow_html=True)

            month_matrix = calendar.monthcalendar(c_year, c_month)
            for week in month_matrix:
                w_cols = st.columns(7, gap="small")
                for idx, day_num in enumerate(week):
                    if day_num == 0:
                        w_cols[idx].markdown('<div class="cal-empty"></div>', unsafe_allow_html=True)
                    else:
                        cell_date = datetime.date(c_year, c_month, day_num)
                        iso_str = cell_date.isoformat()
                        is_weekend = idx >= 5
                        is_holiday = cell_date in holiday_map

                        if is_holiday:
                            css_class = "cal-red"
                            sub_label = "HOLIDAY"
                        elif is_weekend:
                            css_class = "cal-red"
                            sub_label = "WKND"
                        elif cell_date <= today_date:
                            bunk_val = st.session_state.daily_logs.get(iso_str, "")
                            if bunk_val:
                                css_class = "cal-yellow"
                                sub_label = bunk_val
                            else:
                                css_class = "cal-green"
                                sub_label = "ATTENDED"
                        else:
                            bunk_val = st.session_state.daily_logs.get(iso_str, "")
                            if bunk_val:
                                css_class = "cal-yellow"
                                sub_label = bunk_val
                            else:
                                css_class = "cal-blue"
                                sub_label = get_week_type(cell_date).split()[0].upper()

                        with w_cols[idx]:
                            st.markdown(
                                f'<div class="cal-cell {css_class}"><div>{day_num}</div><div class="cal-sub">{sub_label}</div></div>',
                                unsafe_allow_html=True,
                            )
                            if st.button("View", key=f"btn_{iso_str}", use_container_width=True, disabled=guide_is_active):
                                st.session_state.selected_cal_date = cell_date

        with cal_col_right:
            inspected_date = st.session_state.selected_cal_date
            inspected_iso = inspected_date.isoformat()
            wk_type = get_week_type(inspected_date)
            weekday_idx = inspected_date.weekday()
            student_batch = st.session_state.get("student_batch", "Batch A")
            batch_letter = student_batch[-1].upper()

            st.markdown(f"#### Selected Day: **{inspected_date.strftime('%a, %d %b %Y')}**")
            st.write(f"**Timetable Rotation:** `{wk_type}` | **Your Batch:** `{student_batch}`")

            if inspected_date in holiday_map:
                st.error(f"**Official Holiday:** {holiday_map[inspected_date]} (No Lectures)")
            elif weekday_idx >= 5:
                st.error("**Weekend (Saturday/Sunday):** No Regular Lectures")
            else:
                day_names_map = {0: "MON", 1: "TUE", 2: "WED", 3: "THR", 4: "FRI"}
                d_key = day_names_map[weekday_idx]
                active_grid = EVEN_WEEK_TIMETABLE_GRID if wk_type == "Even Week" else ODD_WEEK_TIMETABLE_GRID
                day_slots = active_grid[d_key]

                saved_day_ticks = st.session_state.daily_slot_ticks.get(inspected_iso, {})

                st.caption("Tick **Unattended (Missed)** beside any lecture/lab below (available for past and current dates). Ticking automatically updates your subject Unattended counts and calendar badge!")

                daily_rows = []
                slot_subject_codes = []
                for s_idx, (slot_label, raw_subj_entry) in enumerate(zip(TIME_SLOTS, day_slots)):
                    # Filter multi-batch labs so ONLY the student's batch lab is shown and tracked
                    batch_filtered_entry, is_batch_lab = extract_batch_specific_entry(raw_subj_entry, batch_letter)
                    matched_sf = match_subject_short_form(batch_filtered_entry, subject_stats_by_short)
                    slot_subject_codes.append(matched_sf)

                    display_subj = batch_filtered_entry
                    if is_batch_lab:
                        display_subj = f"{batch_filtered_entry} [YOUR {student_batch.upper()} LAB]"

                    if matched_sf and matched_sf in subject_stats_by_short:
                        st_info = subject_stats_by_short[matched_sf]
                        need_str = (
                            f"Missed: {st_info['unattended']}/{st_info['total']} | Need {st_info['needed']} for {target_att_pct}% (Curr: {st_info['pct']}%)"
                            if st_info["needed"] > 0
                            else f"Missed: {st_info['unattended']}/{st_info['total']} | Safe: Bunk {st_info['bunks']} (Curr: {st_info['pct']}%)"
                        )
                    else:
                        need_str = "Break / Non-Credit Slot"

                    is_ticked = bool(saved_day_ticks.get(str(s_idx), False))
                    daily_rows.append({
                        "Unattended (Tick)": is_ticked,
                        "Time Slot": slot_label,
                        "Lecture / Lab (Batch Filtered)": display_subj,
                        f"{target_att_pct}% Status": need_str,
                    })

                daily_df_editor_source = pd.DataFrame(daily_rows)
                edited_daily_df = st.data_editor(
                    daily_df_editor_source,
                    num_rows="fixed",
                    disabled=["Time Slot", "Lecture / Lab (Batch Filtered)", f"{target_att_pct}% Status"] if not guide_is_active else list(daily_df_editor_source.columns),
                    column_config={
                        "Unattended (Tick)": st.column_config.CheckboxColumn("Unattended (Tick)", default=False),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"daily_tick_editor_{inspected_iso}_{student_batch}",
                )

                # Sync tick changes with global subject Unattended counts and calendar badge
                if not guide_is_active and not edited_daily_df["Unattended (Tick)"].equals(daily_df_editor_source["Unattended (Tick)"]):
                    new_ticks_for_day = {}
                    missed_short_forms_today = []
                    total_credit_slots_today = 0
                    ticked_credit_slots_today = 0

                    sem_df_ref = st.session_state.saved_semesters[selected_semester].copy()

                    for s_idx, matched_sf in enumerate(slot_subject_codes):
                        old_tick = bool(daily_df_editor_source.loc[s_idx, "Unattended (Tick)"])
                        new_tick = bool(edited_daily_df.loc[s_idx, "Unattended (Tick)"])
                        new_ticks_for_day[str(s_idx)] = new_tick

                        if matched_sf:
                            total_credit_slots_today += 1
                            if new_tick:
                                ticked_credit_slots_today += 1
                                if matched_sf not in missed_short_forms_today:
                                    missed_short_forms_today.append(matched_sf)

                            # Adjust Unattended count in main semester table by delta (+1 or -1)
                            if new_tick != old_tick:
                                delta = 1 if new_tick else -1
                                mask = sem_df_ref["Short Form"] == matched_sf
                                for r_i in sem_df_ref[mask].index:
                                    curr_u = int(sem_df_ref.loc[r_i, "Unattended"])
                                    max_t = int(sem_df_ref.loc[r_i, "Total Lectures"])
                                    sem_df_ref.loc[r_i, "Unattended"] = min(max_t, max(0, curr_u + delta))

                    st.session_state.daily_slot_ticks[inspected_iso] = new_ticks_for_day
                    st.session_state.saved_semesters[selected_semester] = sem_df_ref

                    # Update Calendar yellow badge ('F' if all credit slots missed, or short-forms)
                    if ticked_credit_slots_today == 0:
                        st.session_state.daily_logs.pop(inspected_iso, None)
                    elif total_credit_slots_today > 0 and ticked_credit_slots_today >= total_credit_slots_today:
                        st.session_state.daily_logs[inspected_iso] = "F"
                    else:
                        st.session_state.daily_logs[inspected_iso] = ", ".join(missed_short_forms_today)

                    save_student_compact(
                        st.session_state.student_email,
                        st.session_state.student_name,
                        st.session_state.student_branch,
                        st.session_state.get("student_batch", "Batch A"),
                        st.session_state.saved_semesters,
                        st.session_state.daily_logs,
                        st.session_state.daily_slot_ticks,
                    )
                    st.rerun()

                # Quick Full-Day Bunk / Clear buttons
                q_col1, q_col2 = st.columns(2)
                with q_col1:
                    if st.button("Tick Full Day Bunk ('F')", key=f"full_bunk_{inspected_iso}", use_container_width=True, disabled=guide_is_active):
                        sem_df_ref = st.session_state.saved_semesters[selected_semester].copy()
                        new_ticks_for_day = {}
                        for s_idx, matched_sf in enumerate(slot_subject_codes):
                            old_tick = bool(saved_day_ticks.get(str(s_idx), False))
                            if matched_sf:
                                new_ticks_for_day[str(s_idx)] = True
                                if not old_tick:
                                    mask = sem_df_ref["Short Form"] == matched_sf
                                    for r_i in sem_df_ref[mask].index:
                                        curr_u = int(sem_df_ref.loc[r_i, "Unattended"])
                                        max_t = int(sem_df_ref.loc[r_i, "Total Lectures"])
                                        sem_df_ref.loc[r_i, "Unattended"] = min(max_t, curr_u + 1)
                        st.session_state.daily_slot_ticks[inspected_iso] = new_ticks_for_day
                        st.session_state.daily_logs[inspected_iso] = "F"
                        st.session_state.saved_semesters[selected_semester] = sem_df_ref
                        save_student_compact(
                            st.session_state.student_email,
                            st.session_state.student_name,
                            st.session_state.student_branch,
                            st.session_state.get("student_batch", "Batch A"),
                            st.session_state.saved_semesters,
                            st.session_state.daily_logs,
                            st.session_state.daily_slot_ticks,
                        )
                        st.rerun()

                with q_col2:
                    if st.button("Clear All Ticks (Attended All)", key=f"clear_bunk_{inspected_iso}", use_container_width=True, disabled=guide_is_active):
                        sem_df_ref = st.session_state.saved_semesters[selected_semester].copy()
                        for s_idx, matched_sf in enumerate(slot_subject_codes):
                            old_tick = bool(saved_day_ticks.get(str(s_idx), False))
                            if matched_sf and old_tick:
                                mask = sem_df_ref["Short Form"] == matched_sf
                                for r_i in sem_df_ref[mask].index:
                                    curr_u = int(sem_df_ref.loc[r_i, "Unattended"])
                                    sem_df_ref.loc[r_i, "Unattended"] = max(0, curr_u - 1)
                        st.session_state.daily_slot_ticks.pop(inspected_iso, None)
                        st.session_state.daily_logs.pop(inspected_iso, None)
                        st.session_state.saved_semesters[selected_semester] = sem_df_ref
                        save_student_compact(
                            st.session_state.student_email,
                            st.session_state.student_name,
                            st.session_state.student_branch,
                            st.session_state.get("student_batch", "Batch A"),
                            st.session_state.saved_semesters,
                            st.session_state.daily_logs,
                            st.session_state.daily_slot_ticks,
                        )
                        st.rerun()

        if selected_semester == "Semester I":
            with st.expander("Official FE Academic Calendar Milestones (Odd Semester AY 2026-27)", expanded=False):
                st.dataframe(pd.DataFrame(SEM1_OFFICIAL_MILESTONES), hide_index=True, use_container_width=True)
        else:
            with st.expander(f"{selected_semester} & Full Yearly Holiday List (2026-27)", expanded=False):
                st.dataframe(pd.DataFrame(YEARLY_HOLIDAYS), hide_index=True, use_container_width=True)

    if s3_col_guide is not None:
        with s3_col_guide:
            render_side_guide_card(
                2,
                4,
                "Step 2: Calendar & Unattended Tick Column",
                "Click 'View' on any date (including past dates) and tick the 'Unattended (Tick)' box right beside any lecture/lab you missed. It automatically updates your total missed lectures everywhere! Click 'Got it' to continue.",
                "dashboard_guide_step",
                arrow_dir="left",
            )

# --- SECTION 4: EDITABLE & LINKED COLOUR-CODED SUBJECT TABLE ---
sec4_wrapper = st.container()
with sec4_wrapper:
    if guide_is_active and active_step in [1, 2, 4]:
        st.markdown('<div class="blur-target-block"></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(f"4. Editable Unattended Lectures, Extra Lectures, Attended Count & Safe Bunks ({target_att_pct}% Goal)")
    st.markdown(
        '<div class="missed-lectures-banner">ENTER HOW MANY LECTURES YOU HAVE MISSED</div>',
        unsafe_allow_html=True,
    )
    st.caption("Edit **Unattended** (default 0) or **Extra Lectures Attended** directly below. Linked with Section 1 and Section 3 Calendar Ticks.")

    if guide_is_active and active_step == 3:
        s4_col_main, s4_col_guide = st.columns([2.2, 1])
    else:
        s4_col_main = st.container()
        s4_col_guide = None

    with s4_col_main:
        sec4_display_cols = [
            "Short Form",
            "Course Code",
            "Course Name",
            "Unattended",
            "Extra Lectures Attended",
            "Regular Attended",
            "Unattended / Total",
            "Current Attendance %",
            "Required for Target",
            "Classes Needed for Target",
            "Safe Bunks Left",
            "Status",
        ]
        sec4_source_df = df[sec4_display_cols].copy()

        sec4_disabled_cols = (
            sec4_display_cols
            if guide_is_active
            else [
                "Short Form",
                "Course Code",
                "Course Name",
                "Regular Attended",
                "Unattended / Total",
                "Current Attendance %",
                "Required for Target",
                "Classes Needed for Target",
                "Safe Bunks Left",
                "Status",
            ]
        )

        edited_sec4 = st.data_editor(
            sec4_source_df,
            num_rows="fixed",
            disabled=sec4_disabled_cols,
            column_config={
                "Unattended": st.column_config.NumberColumn("Unattended (Missed)", min_value=0, default=0, step=1),
                "Extra Lectures Attended": st.column_config.NumberColumn("Extra Lectures Attended", min_value=0, default=0, step=1),
                "Current Attendance %": st.column_config.NumberColumn("Current Attendance %", format="%.2f%%"),
                "Required for Target": st.column_config.NumberColumn(f"Required for {target_att_pct}%"),
                "Classes Needed for Target": st.column_config.NumberColumn(f"Classes Needed for {target_att_pct}%"),
            },
            use_container_width=True,
            key=f"sec4_editor_{selected_semester}_{target_att_pct}",
        )

        if not guide_is_active and (
            not edited_sec4["Unattended"].equals(sec4_source_df["Unattended"])
            or not edited_sec4["Extra Lectures Attended"].equals(sec4_source_df["Extra Lectures Attended"])
        ):
            st.session_state.saved_semesters[selected_semester]["Unattended"] = edited_sec4["Unattended"].values
            st.session_state.saved_semesters[selected_semester]["Extra Lectures Attended"] = edited_sec4["Extra Lectures Attended"].values
            save_student_compact(
                st.session_state.student_email,
                st.session_state.student_name,
                st.session_state.student_branch,
                st.session_state.get("student_batch", "Batch A"),
                st.session_state.saved_semesters,
                st.session_state.daily_logs,
                st.session_state.daily_slot_ticks,
            )
            st.rerun()

        def style_attendance_row(row):
            if row["Current Attendance %"] >= target_att_pct:
                bg = "background-color: rgba(34, 197, 94, 0.25); color: #4ade80; font-weight: bold;"
            else:
                bg = "background-color: rgba(234, 179, 8, 0.28); color: #fde047; font-weight: bold;"
            return [bg] * len(row)

        with st.expander(f"View Colour-Highlighted Summary Table (Green >= {target_att_pct}%, Yellow < {target_att_pct}%)", expanded=True):
            st.info("Note: These calculations assume that you will attend all of your remaining upcoming lectures—so don't be a defaulter!")
            st.dataframe(
                sec4_source_df.style.apply(style_attendance_row, axis=1).format({"Current Attendance %": "{:.2f}%"}),
                use_container_width=True,
            )

    if s4_col_guide is not None:
        with s4_col_guide:
            render_side_guide_card(
                3,
                4,
                "Step 3: Editable Unattended & Extra Lectures Slot",
                "This arrow points to Section 4. Edit 'Unattended' and 'Extra Lectures Attended' right here, and it syncs back to Section 1. Click 'Got it' to continue.",
                "dashboard_guide_step",
                arrow_dir="left",
            )

# --- SECTION 5: VERTICAL LARGE COLOUR-CODED TIMETABLE (BATCH-SPECIFIC LAB ATTENDANCE) + IMAGE REMOVE/PASTE ---
sec5_wrapper = st.container()
with sec5_wrapper:
    if guide_is_active and active_step in [1, 2, 3]:
        st.markdown('<div class="blur-target-block"></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("5. Vertical Timetable (Batch-Specific Lab Attendance) & Timetable Image Manager")

    if guide_is_active and active_step == 4:
        s5_col_main, s5_col_guide = st.columns([2.2, 1])
    else:
        s5_col_main = st.container()
        s5_col_guide = None

    student_batch = st.session_state.get("student_batch", "Batch A")
    batch_letter = student_batch[-1].upper()

    def build_vertical_timetable_html(grid_dict):
        """
        Builds a large vertical HTML timetable where MON..FRI are columns and Time Slots are rows.
        For multi-batch labs, filters out other batches and shows ONLY the chosen batch's lab and its specific attendance.
        """
        days_order = ["MON", "TUE", "WED", "THR", "FRI"]
        html = '<table class="vertical-tt-table"><thead><tr>'
        html += '<th>TIME SLOT</th>'
        for d_col in days_order:
            html += f'<th>{d_col}</th>'
        html += '</tr></thead><tbody>'

        for slot_idx, slot_name in enumerate(TIME_SLOTS):
            html += '<tr>'
            html += f'<td class="tt-slot-col">{slot_name}</td>'
            for d_col in days_order:
                raw_val = grid_dict[d_col][slot_idx]
                batch_entry, is_batch_lab = extract_batch_specific_entry(raw_val, batch_letter)
                matched_sf = match_subject_short_form(batch_entry, subject_stats_by_short)

                cell_class = "tt-cell-blue"
                att_subtext = ""

                if "BREAK" in raw_val:
                    cell_class = "tt-cell-red"
                elif matched_sf and matched_sf in subject_stats_by_short:
                    info = subject_stats_by_short[matched_sf]
                    cell_class = "tt-cell-green" if info["pct"] >= target_att_pct else "tt-cell-yellow"
                    att_subtext = (
                        f"<div style='font-size:12px; margin-top:4px; opacity:0.95;'>"
                        f"Att: {info['pct']}% | Missed: {info['unattended']}/{info['total']}"
                        f"</div>"
                    )

                display_val = batch_entry
                if is_batch_lab:
                    # Removed 'BLINKING:' prefix as requested
                    display_val += f'<br><span class="blinking-batch-badge">YOUR {student_batch.upper()} LAB</span>'

                html += f'<td class="{cell_class}">{display_val}{att_subtext}</td>'
            html += '</tr>'
        html += '</tbody></table>'
        return html

    with s5_col_main:
        tt_tab1, tt_tab2, tt_tab3 = st.tabs([
            "Even Week Vertical Timetable",
            "Odd Week Vertical Timetable",
            "Official Timetable Image (Upload / Paste / Remove)",
        ])

        with tt_tab1:
            st.caption(f"**Even Week Effective Dates:** 21–25 Sept | 5–9 Oct | 26–30 Oct | 9–13 Nov | 23–27 Nov 2026 (Showing Lab Attendance Specifically for **{student_batch}** | Target: {target_att_pct}%)")
            st.markdown(build_vertical_timetable_html(EVEN_WEEK_TIMETABLE_GRID), unsafe_allow_html=True)

        with tt_tab2:
            st.caption(f"**Odd Week Effective Dates:** 7–11 Sept | 28 Sept–2 Oct | 12–16 Oct | 1–6 Nov | 16–20 Nov | 30 Nov–4 Dec 2026 (Showing Lab Attendance Specifically for **{student_batch}** | Target: {target_att_pct}%)")
            st.markdown(build_vertical_timetable_html(ODD_WEEK_TIMETABLE_GRID), unsafe_allow_html=True)

        with tt_tab3:
            if os.path.exists(TIMETABLE_IMG_PATH):
                img_top_col1, img_top_col2 = st.columns([4, 1])
                with img_top_col2:
                    if st.button("Remove Timetable Image", type="secondary", use_container_width=True, disabled=guide_is_active):
                        try:
                            os.remove(TIMETABLE_IMG_PATH)
                        except Exception:
                            pass
                        st.rerun()
                st.image(TIMETABLE_IMG_PATH, caption="Official First Year Engineering Timetable (Even & Odd Weeks)", use_container_width=True)
            else:
                st.info("No timetable image is currently saved. You can either **Upload an image file** OR **Paste a copied image (`Ctrl + V`)** below.")

            up_col1, up_col2 = st.columns(2)
            with up_col1:
                uploaded_tt = st.file_uploader(
                    "Option 1: Upload Timetable Image (PNG/JPG)",
                    type=["jpg", "jpeg", "png", "webp"],
                    disabled=guide_is_active,
                )
                if uploaded_tt is not None:
                    with open(TIMETABLE_IMG_PATH, "wb") as f:
                        f.write(uploaded_tt.getbuffer())
                    st.rerun()

            with up_col2:
                st.write("**Option 2: Paste Copied Image Only (`Ctrl + V`)**")
                # Interactive clipboard image paste zone converts pasted image to DataURL for instant saving
                components.html(
                    """
                    <div id="paste-zone" tabindex="0" style="
                        border: 2px dashed #38bdf8;
                        border-radius: 8px;
                        padding: 14px;
                        text-align: center;
                        color: #e2e8f0;
                        background: #0f172a;
                        font-family: 'Segoe UI', sans-serif;
                        cursor: pointer;
                    ">
                        Click here and press <b>Ctrl + V</b> to paste a copied image.<br>
                        <span id="paste-status" style="font-size: 12px; color: #94a3b8;">Only image clipboard data is accepted.</span>
                    </div>
                    <input type="text" id="b64-out" readonly style="width:100%; margin-top:6px; background:#1e293b; color:#38bdf8; border:1px solid #475569; padding:4px; font-size:11px; display:none;" />
                    <script>
                    const zone = document.getElementById('paste-zone');
                    const statusEl = document.getElementById('paste-status');
                    const outInput = document.getElementById('b64-out');
                    zone.addEventListener('paste', function(e) {
                        const items = (e.clipboardData || e.originalEvent.clipboardData).items;
                        let foundImg = false;
                        for (let i = 0; i < items.length; i++) {
                            if (items[i].type.indexOf('image') === 0) {
                                foundImg = true;
                                const blob = items[i].getAsFile();
                                const reader = new FileReader();
                                reader.onload = function(event) {
                                    outInput.value = event.target.result;
                                    outInput.style.display = 'block';
                                    outInput.select();
                                    navigator.clipboard.writeText(event.target.result).catch(()=>{});
                                    statusEl.innerHTML = "<b style='color:#4ade80;'>Image captured! Copy the code shown below (auto-copied) and paste into the 'Save Pasted Image Data' box below.</b>";
                                };
                                reader.readAsDataURL(blob);
                                break;
                            }
                        }
                        if (!foundImg) {
                            statusEl.innerHTML = "<b style='color:#ef4444;'>Rejected: Clipboard does not contain an image!</b>";
                        }
                    });
                    </script>
                    """,
                    height=125,
                )
                pasted_data_url = st.text_input(
                    "Save Pasted Image Data (Paste the auto-copied `data:image/...` string here):",
                    key="pasted_img_input",
                    disabled=guide_is_active,
                )
                if pasted_data_url:
                    if pasted_data_url.strip().startswith("data:image/") and ";base64," in pasted_data_url:
                        try:
                            b64_part = pasted_data_url.split(";base64,", 1)[1]
                            img_bytes = base64.b64decode(b64_part)
                            with open(TIMETABLE_IMG_PATH, "wb") as f:
                                f.write(img_bytes)
                            st.success("Pasted image saved!")
                            st.rerun()
                        except Exception:
                            st.error("Invalid image data.")
                    else:
                        st.error("Only valid copied images (`data:image/...`) are allowed.")

    if s5_col_guide is not None:
        with s5_col_guide:
            render_side_guide_card(
                4,
                4,
                "Step 4: Batch-Specific Lab Timetable & Image Manager",
                "This arrow points to Section 5. Labs now filter automatically to show ONLY your chosen Batch (A, B, or C) and its attendance. Click 'Got it' to finish the tour permanently!",
                "dashboard_guide_step",
                arrow_dir="left",
                finish_tour=True,
            )

# --- EXCLUSIVE ADMIN LOG (VISIBLE ONLY WHEN LOGGED IN AS KANISHKA'S GMAIL + VERIFIED PASSWORD) ---
if (
    st.session_state.get("student_logged_in", False)
    and st.session_state.get("student_email", "").strip().lower() == ADMIN_EMAIL
):
    st.sidebar.markdown("---")
    with st.sidebar.expander("View Student Log (Exclusive Admin Access)", expanded=False):
        if os.path.exists(VISITOR_LOG_FILE):
            log_df = pd.read_csv(VISITOR_LOG_FILE)
            log_df.index = range(1, len(log_df) + 1)
            st.dataframe(log_df)
        else:
            st.write("No students have logged in yet.")

# --- FOOTER SUBHEADING ---
st.markdown(
    '<div class="creator-footer">Designed and Created by Kanishka Maya Honrao</div>',
    unsafe_allow_html=True,
)
