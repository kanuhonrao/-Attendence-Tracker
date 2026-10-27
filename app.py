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

# Page Configuration
st.set_page_config(
    page_title="Attendance & Interactive Calendar Tracker",
    layout="wide",
)

VISITOR_LOG_FILE = "student_visitors_log.csv"
STUDENT_DB_FILE = "saved_students_compact.json"
ADMIN_GLOBAL_EXTRAS_FILE = "admin_global_extras.json"
TIMETABLE_IMG_PATH = "timetable.jpg"

# Exclusive Admin Credentials
ADMIN_EMAIL = "honraokanishka@gmail.com"
ADMIN_PASSWORD_PLAIN = "G!nt0k1."


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


def load_admin_global_extras():
    if os.path.exists(ADMIN_GLOBAL_EXTRAS_FILE):
        try:
            with open(ADMIN_GLOBAL_EXTRAS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_admin_global_extras(extras_dict):
    try:
        with open(ADMIN_GLOBAL_EXTRAS_FILE, "w", encoding="utf-8") as f:
            json.dump(extras_dict, f)
    except Exception:
        pass


def save_local_remembered_session(email: str, token: str):
    try:
        with open(".remembered_session.json", "w", encoding="utf-8") as f:
            json.dump({"email": email.strip().lower(), "token": token}, f)
    except Exception:
        pass


def load_local_remembered_session():
    if os.path.exists(".remembered_session.json"):
        try:
            with open(".remembered_session.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def clear_local_remembered_session():
    if os.path.exists(".remembered_session.json"):
        try:
            os.remove(".remembered_session.json")
        except Exception:
            pass


def save_student_compact(
    email,
    name,
    branch,
    batch,
    semesters_dict,
    daily_logs=None,
    daily_slot_ticks=None,
    slot7_extra_map=None,
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
    final_slot7 = existing_rec.get("slot7_extra_map", {}) if slot7_extra_map is None else slot7_extra_map
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
        "storage_mode": "unattended_v6",
        "last_updated": get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "data": compact_sems,
        "daily_logs": final_logs,
        "daily_slot_ticks": final_ticks,
        "slot7_extra_map": final_slot7,
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


# --- CONTEXTUAL STEP GUIDE ---
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
    if st.button("Got it", key=f"got_it_{state_key}_{step_num}", type="primary", width="stretch"):
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
                st.session_state.slot7_extra_map,
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
    if "/" in raw_entry and ("(A)" in raw_entry or "(B)" in raw_entry or "(C)" in raw_entry):
        parts = [p.strip() for p in raw_entry.split("/")]
        for part in parts:
            if f"({batch_letter})" in part:
                return part, True
    return raw_entry, False


def match_subject_short_form(entry_text: str, subject_stats_dict: dict):
    """Matches either a Short Form (e.g., 'CP', 'FEM-I') OR a Course Code (e.g., '25FE1VSEC02')."""
    clean_up = entry_text.strip().upper()
    if not clean_up:
        return None
    if "WORKSHOP" in clean_up or "WS-I" in clean_up:
        return "WS-I" if "WS-I" in subject_stats_dict else None
    # Check exact or substring match for Course Code first
    for sf_code, info in subject_stats_dict.items():
        if info["code"].upper() in clean_up:
            return sf_code
    # Then check Short Form (longest first so FEM-I matches before EM)
    for sf_code in sorted(subject_stats_dict.keys(), key=len, reverse=True):
        if sf_code.upper() in clean_up:
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
    sem_dict_out = {}
    for sem, courses in SEMESTER_DATA.items():
        temp_df = pd.DataFrame(courses)
        if sem in saved_student_data:
            sem_dict = saved_student_data[sem]
            for idx, row in temp_df.iterrows():
                code = row["Course Code"]
                tot_lec = int(row["Total Lectures"])
                if code in sem_dict:
                    vals = sem_dict[code]
                    temp_df.loc[idx, "Importance (1-3)"] = vals[0]
                    temp_df.loc[idx, "Unattended"] = min(tot_lec, max(0, int(vals[1])))
                    base_extra = vals[2] if len(vals) > 2 else 0
                    temp_df.loc[idx, "Extra Lectures Attended"] = max(0, int(base_extra))
        temp_df.index = range(1, len(temp_df) + 1)
        sem_dict_out[sem] = temp_df
    return sem_dict_out


# --- AUTO-LOGIN ---
query_params = st.query_params
saved_email = query_params.get("email", "").strip().lower()
saved_token = query_params.get("token", "").strip()
local_rem = load_local_remembered_session()

if "student_logged_in" not in st.session_state:
    all_db = load_all_students_db()
    if not saved_email and local_rem and not query_params.get("logged_out"):
        saved_email = local_rem.get("email", "").strip().lower()
        saved_token = local_rem.get("token", "").strip()

    if saved_email and saved_email in all_db:
        user_record = all_db[saved_email]
        stored_pw_hash = user_record.get("password_hash", "")
        if (stored_pw_hash and saved_token == stored_pw_hash) or (not stored_pw_hash):
            st.session_state.student_logged_in = True
            st.session_state.student_email = user_record.get("email", saved_email)
            st.session_state.student_name = user_record.get("name", "Student")
            st.session_state.student_branch = user_record.get("branch", BRANCH_OPTIONS[0])
            st.session_state.student_batch = user_record.get("batch", BATCH_OPTIONS[0])
            st.session_state.guide_completed = True
            st.session_state.target_attendance_pct = int(user_record.get("target_attendance_pct", 75))
            st.session_state.dashboard_guide_step = 99
            st.query_params["email"] = saved_email
            if stored_pw_hash:
                st.query_params["token"] = stored_pw_hash
        else:
            st.session_state.student_logged_in = False
    else:
        st.session_state.student_logged_in = False

if "dashboard_guide_step" not in st.session_state:
    st.session_state.dashboard_guide_step = 99 if st.session_state.get("guide_completed", False) else 1

if st.session_state.get("student_logged_in", False) and "saved_semesters" not in st.session_state:
    email_key = st.session_state.student_email.strip().lower()
    all_db = load_all_students_db()
    user_obj = all_db.get(email_key, {})
    st.session_state.student_batch = user_obj.get("batch", BATCH_OPTIONS[0])
    st.session_state.guide_completed = user_obj.get("guide_completed", True)
    st.session_state.target_attendance_pct = int(user_obj.get("target_attendance_pct", 75))
    st.session_state.daily_logs = user_obj.get("daily_logs", {})
    st.session_state.daily_slot_ticks = user_obj.get("daily_slot_ticks", {})
    st.session_state.slot7_extra_map = user_obj.get("slot7_extra_map", {})
    st.session_state.saved_semesters = hydrate_semesters_for_user(user_obj)

# --- LOGIN SCREEN ---
if not st.session_state.get("student_logged_in", False):
    st.title("Attendance, Timetable & Calendar Tracker")
    st.subheader("Student Login & Password Verification")
    st.caption("Keep 'Remember Me' ticked so restarting the app or reopening the browser logs you in automatically.")

    with st.form("student_login_form"):
        input_email = st.text_input("Enter Your Gmail Address (must end with @gmail.com):")
        input_password = st.text_input("Enter Your Password:", type="password")
        input_name = st.text_input("Enter Your Real Full Name (Required for first-time registration):")
        input_branch = st.selectbox("Select Your Branch:", BRANCH_OPTIONS)
        input_batch = st.selectbox("Select Your College Batch:", BATCH_OPTIONS)
        remember_me = st.checkbox("Remember Me automatically", value=True)
        submit_btn = st.form_submit_button("Login / Register & Enter Dashboard")

        if submit_btn:
            clean_email = input_email.strip().lower()
            clean_name = input_name.strip()
            clean_pw = input_password.strip()

            if not clean_email.endswith("@gmail.com"):
                st.error("Invalid email domain. Please use a valid Gmail address ending with '@gmail.com'.")
            elif not clean_pw:
                st.error("Please enter a password.")
            else:
                # If logging in as Admin Gmail, enforce the Admin Password ("G!nt0k1.")
                if clean_email == ADMIN_EMAIL.lower() and clean_pw != ADMIN_PASSWORD_PLAIN:
                    st.error("Invalid password for Admin Gmail account.")
                    st.stop()

                all_db = load_all_students_db()
                pw_hashed = hash_password(clean_pw)
                is_existing_user = clean_email in all_db

                if is_existing_user:
                    user_obj = all_db[clean_email]
                    stored_hash = user_obj.get("password_hash", "")
                    if stored_hash and stored_hash != pw_hashed and clean_email != ADMIN_EMAIL.lower():
                        st.error("Incorrect password for this Gmail account.")
                        st.stop()
                    final_name = clean_name if clean_name else user_obj.get("name", "Kanishka Maya Honrao" if clean_email == ADMIN_EMAIL.lower() else "Student")
                    final_branch = user_obj.get("branch", input_branch)
                    final_batch = user_obj.get("batch", input_batch)
                    guide_done = True
                    st.session_state.dashboard_guide_step = 99
                else:
                    if not clean_name and clean_email != ADMIN_EMAIL.lower():
                        st.error("First-time registration requires your Real Full Name.")
                        st.stop()
                    user_obj = {}
                    final_name = clean_name if clean_name else "Kanishka Maya Honrao"
                    final_branch = input_branch
                    final_batch = input_batch
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
                st.session_state.slot7_extra_map = user_obj.get("slot7_extra_map", {})
                st.session_state.saved_semesters = hydrate_semesters_for_user(user_obj)

                save_student_compact(
                    clean_email,
                    final_name,
                    final_branch,
                    final_batch,
                    st.session_state.saved_semesters,
                    st.session_state.daily_logs,
                    st.session_state.daily_slot_ticks,
                    st.session_state.slot7_extra_map,
                    password_hash=pw_hashed,
                    guide_completed=guide_done,
                    target_attendance_pct=st.session_state.target_attendance_pct,
                )
                update_student_visit(clean_email, final_name, final_branch, final_batch)

                if remember_me:
                    st.query_params.clear()
                    st.query_params["email"] = clean_email
                    st.query_params["token"] = pw_hashed
                    save_local_remembered_session(clean_email, pw_hashed)
                else:
                    st.query_params.clear()
                    clear_local_remembered_session()

                st.rerun()

    st.markdown(
        '<div class="creator-footer">Designed and Created by Kanishka Maya Honrao</div>',
        unsafe_allow_html=True,
    )
    st.stop()

if st.query_params.get("email") and st.query_params.get("token"):
    save_local_remembered_session(st.query_params["email"], st.query_params["token"])

if "slot7_extra_map" not in st.session_state:
    st.session_state.slot7_extra_map = {}

# --- MAIN DASHBOARD ---
active_step = st.session_state.dashboard_guide_step
guide_is_active = (not st.session_state.get("guide_completed", True)) and (active_step in [1, 2, 3, 4])
if guide_is_active:
    apply_guide_blur_css()

greeting = get_time_greeting()
st.title(f"{greeting}, {st.session_state.student_name}")
st.caption(f"**Branch:** {st.session_state.student_branch} | **Batch:** {st.session_state.get('student_batch', 'Batch A')} | **Verified Gmail:** {st.session_state.student_email}")

# --- TOP BAR: DESIRED ATTENDANCE PERCENTAGE ---
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
            st.session_state.slot7_extra_map,
            target_attendance_pct=int(target_att_pct),
        )

with t_col3:
    st.write("")
    if st.button("Replay Feature Guide", disabled=guide_is_active, width="stretch"):
        st.session_state.guide_completed = False
        st.session_state.dashboard_guide_step = 1
        st.rerun()

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
        st.session_state.slot7_extra_map,
    )
    st.rerun()

# --- ADMIN POWER PANEL (EXCLUSIVELY FOR KANISHKA WITH PASSWORD "G!nt0k1.") ---
is_kanishka = st.session_state.student_email.strip().lower() == ADMIN_EMAIL.strip().lower()
if is_kanishka:
    st.sidebar.markdown("---")
    st.sidebar.header("Admin Power Panel")
    admin_auth = st.sidebar.text_input("Enter Admin Password:", type="password", key="sidebar_admin_pwd")
    if admin_auth == ADMIN_PASSWORD_PLAIN:
        st.sidebar.success("Admin Power Unlocked (Linked to your Gmail)")
        global_extras_current = load_admin_global_extras()
        st.sidebar.write("**Broadcast Extra Lectures (Visible to Everyone Else Other Than You):**")
        target_sem_for_admin = st.sidebar.selectbox("Select Semester:", list(SEMESTER_DATA.keys()), key="admin_sem_pick")
        admin_course_options = {f"{c['Short Form']} - {c['Course Name']} ({c['Course Code']})": c["Course Code"] for c in SEMESTER_DATA[target_sem_for_admin]}
        chosen_course_label = st.sidebar.selectbox("Select Subject:", list(admin_course_options.keys()), key="admin_subj_pick")
        chosen_course_code = admin_course_options[chosen_course_label]
        current_pushed_val = int(global_extras_current.get(chosen_course_code, 0))
        extra_count_to_push = st.sidebar.number_input(
            "Extra Lectures for All Other Students:",
            min_value=0,
            value=current_pushed_val,
            step=1,
            key="admin_extra_num",
        )

        if st.sidebar.button("Broadcast Extra Lectures to Other Students", width="stretch"):
            global_extras_current[chosen_course_code] = int(extra_count_to_push)
            save_admin_global_extras(global_extras_current)
            st.sidebar.success(f"Broadcasted {extra_count_to_push} extra lecture(s) for {chosen_course_code} to all other students!")

        if global_extras_current:
            st.sidebar.caption("Active Global Extra Lectures (Applied to other students):")
            st.sidebar.json(global_extras_current)

        with st.sidebar.expander("View Student Visitor Log (Admin Only)", expanded=False):
            if os.path.exists(VISITOR_LOG_FILE):
                log_df = pd.read_csv(VISITOR_LOG_FILE)
                log_df.index = range(1, len(log_df) + 1)
                st.dataframe(log_df, width="stretch")
            else:
                st.write("No students have logged in yet.")
    elif admin_auth:
        st.sidebar.error("Incorrect Admin Password.")

if st.sidebar.button("Switch Student / Logout", disabled=guide_is_active):
    clear_local_remembered_session()
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
    st.session_state.slot7_extra_map = {}
    save_student_compact(
        st.session_state.student_email,
        st.session_state.student_name,
        st.session_state.student_branch,
        st.session_state.get("student_batch", "Batch A"),
        st.session_state.saved_semesters,
        st.session_state.daily_logs,
        st.session_state.daily_slot_ticks,
        st.session_state.slot7_extra_map,
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


# --- HELPER TO COMPUTE DERIVED COLUMNS (INCLUDING ADMIN BROADCAST FOR NON-ADMIN STUDENTS) ---
def compute_attendance_metrics(base_df, target_pct_val: int, current_user_email: str):
    t_ratio = target_pct_val / 100.0
    is_admin_user = current_user_email.strip().lower() == ADMIN_EMAIL.strip().lower()
    global_extras = load_admin_global_extras()

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

    # Admin Broadcasted Extra Lectures: Visible ONLY to everyone else OTHER than Admin (Kanishka)
    if not is_admin_user:
        df["Admin Broadcast Extra"] = df["Course Code"].apply(lambda c: int(global_extras.get(c, 0)))
    else:
        df["Admin Broadcast Extra"] = 0

    df["Total Extra Lectures"] = df["Extra Lectures Attended"] + df["Admin Broadcast Extra"]
    df["Regular Attended"] = (df["Total Lectures"] - df["Unattended"]).clip(lower=0)
    df["Effective Attended"] = (df["Regular Attended"] + df["Total Extra Lectures"]).clip(upper=df["Total Lectures"])
    df["Effective Unattended"] = (df["Total Lectures"] - df["Effective Attended"]).clip(lower=0)

    df["Unattended / Total"] = df["Unattended"].astype(str) + " / " + df["Total Lectures"].astype(str)
    df["Current Attendance %"] = ((df["Effective Attended"] / df["Total Lectures"]) * 100).round(2)

    df["Required for Target"] = df["Total Lectures"].apply(lambda tot: math.ceil(t_ratio * tot))
    df["Classes Needed for Target"] = (df["Required for Target"] - df["Effective Attended"]).clip(lower=0)
    df["Max Allowed Bunks"] = df["Total Lectures"] - df["Required for Target"]
    df["Safe Bunks Left"] = (df["Max Allowed Bunks"] - df["Effective Unattended"]).clip(lower=0)
    df["Status"] = df["Current Attendance %"].apply(
        lambda x: f"Safe (>={target_att_pct}%)" if x >= target_att_pct else f"Shortage (<{target_att_pct}%)"
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
            width="stretch",
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
                st.session_state.slot7_extra_map,
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

df = compute_attendance_metrics(
    st.session_state.saved_semesters[selected_semester],
    target_att_pct,
    st.session_state.student_email,
)

# Show banner for non-admin students if Admin broadcasted global extra lectures
if not is_kanishka and int(df["Admin Broadcast Extra"].sum()) > 0:
    st.info(f"Admin Broadcast Active: {int(df['Admin Broadcast Extra'].sum())} extra college-wide lecture(s) have been automatically included in your attendance calculation.")

subject_stats_by_short = {}
for _, r in df.iterrows():
    sf = r["Short Form"]
    subject_stats_by_short[sf] = {
        "code": r["Course Code"],
        "name": r["Course Name"],
        "unattended": int(r["Unattended"]),
        "regular_attended": int(r["Regular Attended"]),
        "extra": int(r["Total Extra Lectures"]),
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

# --- SECTION 3: TABLE-BORDERED COMPACT CALENDAR & DAY CLICK INSPECTOR ---
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
                            if st.button("View", key=f"btn_{iso_str}", width="stretch", disabled=guide_is_active):
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
                saved_slot7_sf = st.session_state.slot7_extra_map.get(inspected_iso, "")

                st.caption(
                    "**Slots 1 to 6 (9:00 AM – 4:00 PM) are non-editable.** Joined bulk lectures (like CP 3–4 or 2-hour Labs) are merged into **1 single unit**. "
                    "**Only the 4:00 PM – 5:00 PM slot is editable** for Extra Lectures!"
                )

                # Extract slots and merge continuous identical subjects (e.g., CP slots 3 & 4) into ONE single bulk lecture
                raw_extracted_slots = []
                for s_idx, (slot_label, raw_subj_entry) in enumerate(zip(TIME_SLOTS, day_slots)):
                    if s_idx == 8 and saved_slot7_sf:
                        batch_filtered_entry = f"Extra Lecture: {saved_slot7_sf}"
                        is_batch_lab = False
                        matched_sf = saved_slot7_sf
                    else:
                        batch_filtered_entry, is_batch_lab = extract_batch_specific_entry(raw_subj_entry, batch_letter)
                        matched_sf = match_subject_short_form(batch_filtered_entry, subject_stats_by_short)
                    raw_extracted_slots.append((s_idx, slot_label, batch_filtered_entry, matched_sf, is_batch_lab))

                processed_slots_view = []
                i = 0
                while i < len(raw_extracted_slots):
                    s_idx, slot_label, entry_text, m_sf, is_lab = raw_extracted_slots[i]
                    # Merge consecutive identical subject slots (excluding breaks and slot 7) into 1 single bulk lecture unit
                    if (
                        m_sf
                        and s_idx < 8
                        and i + 1 < len(raw_extracted_slots)
                        and raw_extracted_slots[i + 1][3] == m_sf
                        and raw_extracted_slots[i + 1][0] < 8
                    ):
                        end_i = i + 1
                        while (
                            end_i < len(raw_extracted_slots)
                            and raw_extracted_slots[end_i][3] == m_sf
                            and raw_extracted_slots[end_i][0] < 8
                        ):
                            end_i += 1
                        end_i -= 1

                        start_slot_num = slot_label.split("(")[0].strip()
                        end_slot_num = raw_extracted_slots[end_i][1].split("(")[0].strip()
                        start_time_str = slot_label.split("(")[1].split("-")[0].strip()
                        end_time_str = raw_extracted_slots[end_i][1].split("-")[1].split(")")[0].strip()

                        combined_slot_label = f"Slots {start_slot_num}-{end_slot_num} ({start_time_str} - {end_time_str}) [1 Bulk Unit]"
                        combined_entry_label = f"{entry_text} (1 Combined Bulk Lecture)"
                        group_indices = list(range(i, end_i + 1))

                        processed_slots_view.append((group_indices[0], combined_slot_label, combined_entry_label, m_sf, is_lab, group_indices))
                        i = end_i + 1
                    else:
                        processed_slots_view.append((s_idx, slot_label, entry_text, m_sf, is_lab, [s_idx]))
                        i += 1

                daily_rows = []
                for s_idx, slot_label, display_subj, matched_sf, is_lab, g_indices in processed_slots_view:
                    if is_lab:
                        display_subj = f"{display_subj} [YOUR {student_batch.upper()} LAB]"

                    if matched_sf and matched_sf in subject_stats_by_short:
                        st_info = subject_stats_by_short[matched_sf]
                        if s_idx == 8 and saved_slot7_sf:
                            need_str = f"Auto-Added +1 Extra Lecture to {matched_sf} (Curr: {st_info['pct']}%)"
                        elif st_info["needed"] > 0:
                            need_str = f"Missed: {st_info['unattended']}/{st_info['total']} | Need {st_info['needed']} for {target_att_pct}% (Curr: {st_info['pct']}%)"
                        else:
                            need_str = f"Missed: {st_info['unattended']}/{st_info['total']} | Safe: Bunk {st_info['bunks']} (Curr: {st_info['pct']}%)"
                    else:
                        need_str = "Editable 4-5 PM Extra Slot" if s_idx == 8 else "Break / Non-Credit Slot"

                    is_ticked = any(bool(saved_day_ticks.get(str(g_sub), False)) for g_sub in g_indices)
                    daily_rows.append({
                        "Unattended (Tick)": is_ticked,
                        "Time Slot": slot_label,
                        "Lecture / Lab (Locked 9AM-4PM)": display_subj,
                        f"{target_att_pct}% Status": need_str,
                    })

                daily_df_editor_source = pd.DataFrame(daily_rows)

                # Lock ALL text columns in the table so 9 AM - 4 PM slots CANNOT be edited; only Unattended (Tick) is clickable here
                edited_daily_df = st.data_editor(
                    daily_df_editor_source,
                    num_rows="fixed",
                    disabled=["Time Slot", "Lecture / Lab (Locked 9AM-4PM)", f"{target_att_pct}% Status"]
                    if not guide_is_active
                    else list(daily_df_editor_source.columns),
                    column_config={
                        "Unattended (Tick)": st.column_config.CheckboxColumn("Unattended (Tick)", default=False),
                    },
                    hide_index=True,
                    width="stretch",
                    key=f"daily_tick_editor_{inspected_iso}_{student_batch}",
                )

                # Dedicated Editable 4:00 PM - 5:00 PM Slot Input (ONLY Slot 7 is editable!)
                st.markdown("##### Edit 4:00 PM – 5:00 PM Slot Only (Auto-Counts as Extra Lecture)")
                slot7_col1, slot7_col2 = st.columns([2.2, 1])
                with slot7_col1:
                    typed_slot7_code = st.text_input(
                        "Enter Subject Short Form or Course Code for 4:00 PM – 5:00 PM (e.g., CP, FEM-I, AP, EC, EG, BE&DE, WS-I, UHV):",
                        value=saved_slot7_sf,
                        key=f"slot7_input_{inspected_iso}",
                        disabled=guide_is_active,
                    )
                with slot7_col2:
                    st.write("")
                    st.write("")
                    apply_slot7_btn = st.button(
                        "Save 4-5 PM Extra Lecture",
                        key=f"save_slot7_{inspected_iso}",
                        width="stretch",
                        disabled=guide_is_active,
                    )

                if apply_slot7_btn and not guide_is_active:
                    sem_df_ref = st.session_state.saved_semesters[selected_semester].copy()
                    new_matched_sf = match_subject_short_form(typed_slot7_code, subject_stats_by_short) if typed_slot7_code.strip() else None

                    if typed_slot7_code.strip() and not new_matched_sf:
                        st.error("Unrecognized subject code/short-form. Use FEM-I, AP, EC, EG, BE&DE, WS-I, CP, or UHV (or exact course code).")
                    else:
                        # Remove previous extra lecture if one was already logged on this date's 4-5 PM slot
                        if saved_slot7_sf and saved_slot7_sf != new_matched_sf:
                            old_mask = sem_df_ref["Short Form"] == saved_slot7_sf
                            for r_i_sem in sem_df_ref[old_mask].index:
                                curr_ex = int(sem_df_ref.loc[r_i_sem, "Extra Lectures Attended"])
                                sem_df_ref.loc[r_i_sem, "Extra Lectures Attended"] = max(0, curr_ex - 1)

                        # Add +1 Extra Lecture Attended if a new valid subject was entered
                        if new_matched_sf and new_matched_sf != saved_slot7_sf:
                            new_mask = sem_df_ref["Short Form"] == new_matched_sf
                            for r_i_sem in sem_df_ref[new_mask].index:
                                curr_ex = int(sem_df_ref.loc[r_i_sem, "Extra Lectures Attended"])
                                sem_df_ref.loc[r_i_sem, "Extra Lectures Attended"] = curr_ex + 1

                        if new_matched_sf:
                            st.session_state.slot7_extra_map[inspected_iso] = new_matched_sf
                        else:
                            st.session_state.slot7_extra_map.pop(inspected_iso, None)

                        st.session_state.saved_semesters[selected_semester] = sem_df_ref
                        save_student_compact(
                            st.session_state.student_email,
                            st.session_state.student_name,
                            st.session_state.student_branch,
                            st.session_state.get("student_batch", "Batch A"),
                            st.session_state.saved_semesters,
                            st.session_state.daily_logs,
                            st.session_state.daily_slot_ticks,
                            st.session_state.slot7_extra_map,
                        )
                        st.rerun()

                # Sync Unattended Ticks (Bulk blocks count as 1 single lecture unit!)
                if not guide_is_active and not edited_daily_df["Unattended (Tick)"].equals(daily_df_editor_source["Unattended (Tick)"]):
                    sem_df_ref = st.session_state.saved_semesters[selected_semester].copy()
                    new_ticks_for_day = saved_day_ticks.copy()
                    missed_short_forms_today = []
                    total_credit_units_today = 0
                    ticked_credit_units_today = 0

                    for r_i, (s_head_idx, s_lab, orig_sub, matched_sf, i_lab, g_inds) in enumerate(processed_slots_view):
                        old_tick = bool(daily_df_editor_source.loc[r_i, "Unattended (Tick)"])
                        new_tick = bool(edited_daily_df.loc[r_i, "Unattended (Tick)"])

                        for g_sub in g_inds:
                            new_ticks_for_day[str(g_sub)] = new_tick

                        if matched_sf and s_head_idx < 8:
                            total_credit_units_today += 1
                            if new_tick:
                                ticked_credit_units_today += 1
                                if matched_sf not in missed_short_forms_today:
                                    missed_short_forms_today.append(matched_sf)

                            # Even if g_inds has 2 slots (like CP 3 & 4), delta is strictly +1 or -1 (1 single bulk lecture!)
                            if new_tick != old_tick:
                                delta = 1 if new_tick else -1
                                mask = sem_df_ref["Short Form"] == matched_sf
                                for r_i_sem in sem_df_ref[mask].index:
                                    curr_u = int(sem_df_ref.loc[r_i_sem, "Unattended"])
                                    max_t = int(sem_df_ref.loc[r_i_sem, "Total Lectures"])
                                    sem_df_ref.loc[r_i_sem, "Unattended"] = min(max_t, max(0, curr_u + delta))

                    st.session_state.daily_slot_ticks[inspected_iso] = new_ticks_for_day
                    st.session_state.saved_semesters[selected_semester] = sem_df_ref

                    if ticked_credit_units_today == 0:
                        st.session_state.daily_logs.pop(inspected_iso, None)
                    elif total_credit_units_today > 0 and ticked_credit_units_today >= total_credit_units_today:
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
                        st.session_state.slot7_extra_map,
                    )
                    st.rerun()

                q_col1, q_col2 = st.columns(2)
                with q_col1:
                    if st.button("Tick Full Day Bunk ('F')", key=f"full_bunk_{inspected_iso}", width="stretch", disabled=guide_is_active):
                        sem_df_ref = st.session_state.saved_semesters[selected_semester].copy()
                        new_ticks_for_day = {}
                        for r_i, (s_head_idx, s_lab, orig_sub, matched_sf, i_lab, g_inds) in enumerate(processed_slots_view):
                            was_ticked = any(bool(saved_day_ticks.get(str(g_sub), False)) for g_sub in g_inds)
                            if matched_sf and s_head_idx < 8:
                                for g_sub in g_inds:
                                    new_ticks_for_day[str(g_sub)] = True
                                if not was_ticked:
                                    mask = sem_df_ref["Short Form"] == matched_sf
                                    for r_i_sem in sem_df_ref[mask].index:
                                        curr_u = int(sem_df_ref.loc[r_i_sem, "Unattended"])
                                        max_t = int(sem_df_ref.loc[r_i_sem, "Total Lectures"])
                                        # Adds +1 per merged bulk unit
                                        sem_df_ref.loc[r_i_sem, "Unattended"] = min(max_t, curr_u + 1)
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
                            st.session_state.slot7_extra_map,
                        )
                        st.rerun()

                with q_col2:
                    if st.button("Clear All Ticks (Attended All)", key=f"clear_bunk_{inspected_iso}", width="stretch", disabled=guide_is_active):
                        sem_df_ref = st.session_state.saved_semesters[selected_semester].copy()
                        for r_i, (s_head_idx, s_lab, orig_sub, matched_sf, i_lab, g_inds) in enumerate(processed_slots_view):
                            was_ticked = any(bool(saved_day_ticks.get(str(g_sub), False)) for g_sub in g_inds)
                            if matched_sf and s_head_idx < 8 and was_ticked:
                                mask = sem_df_ref["Short Form"] == matched_sf
                                for r_i_sem in sem_df_ref[mask].index:
                                    curr_u = int(sem_df_ref.loc[r_i_sem, "Unattended"])
                                    sem_df_ref.loc[r_i_sem, "Unattended"] = max(0, curr_u - 1)
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
                            st.session_state.slot7_extra_map,
                        )
                        st.rerun()

        if selected_semester == "Semester I":
            with st.expander("Official FE Academic Calendar Milestones (Odd Semester AY 2026-27)", expanded=False):
                st.dataframe(pd.DataFrame(SEM1_OFFICIAL_MILESTONES), hide_index=True, width="stretch")
        else:
            with st.expander(f"{selected_semester} & Full Yearly Holiday List (2026-27)", expanded=False):
                st.dataframe(pd.DataFrame(YEARLY_HOLIDAYS), hide_index=True, width="stretch")

    if s3_col_guide is not None:
        with s3_col_guide:
            render_side_guide_card(
                2,
                4,
                "Step 2: Locked Slots 1-6, Bulk Lectures & Editable 4-5 PM Slot",
                "Slots 1-6 are locked. Joined classes like CP (Slots 3-4) are merged into 1 single bulk lecture unit. Only the 4:00 PM - 5:00 PM input box is editable and automatically adds +1 Extra Lecture! Click 'Got it'.",
                "dashboard_guide_step",
                arrow_dir="left",
            )

# --- SECTION 4: EDITABLE SUBJECT TABLE ---
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
            "Admin Broadcast Extra",
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
                "Admin Broadcast Extra",
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
                "Extra Lectures Attended": st.column_config.NumberColumn("Extra Lectures (Personal)", min_value=0, default=0, step=1),
                "Admin Broadcast Extra": st.column_config.NumberColumn("Admin Extra (Global)"),
                "Current Attendance %": st.column_config.NumberColumn("Current Attendance %", format="%.2f%%"),
                "Required for Target": st.column_config.NumberColumn(f"Required for {target_att_pct}%"),
                "Classes Needed for Target": st.column_config.NumberColumn(f"Classes Needed for {target_att_pct}%"),
            },
            width="stretch",
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
                st.session_state.slot7_extra_map,
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
                width="stretch",
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

# --- SECTION 5: VERTICAL LARGE TIMETABLE (MERGED BULK CELLS WITH ROWSPAN + BATCH-SPECIFIC LAB ATTENDANCE) ---
sec5_wrapper = st.container()
with sec5_wrapper:
    if guide_is_active and active_step in [1, 2, 3]:
        st.markdown('<div class="blur-target-block"></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("5. Vertical Timetable (Merged Bulk Lectures + Batch-Specific Lab Attendance) & Image Manager")

    if guide_is_active and active_step == 4:
        s5_col_main, s5_col_guide = st.columns([2.2, 1])
    else:
        s5_col_main = st.container()
        s5_col_guide = None

    student_batch = st.session_state.get("student_batch", "Batch A")
    batch_letter = student_batch[-1].upper()

    def build_vertical_timetable_html(grid_dict):
        """
        Builds a vertical HTML timetable where MON..FRI are columns, and continuous multi-hour bulk blocks
        (like Wednesday CP slots 3-4 or 2-hour Labs/Workshops) are merged into ONE single big cell using rowspan!
        """
        days_order = ["MON", "TUE", "WED", "THR", "FRI"]
        num_slots = len(TIME_SLOTS)

        # Precompute rowspan matrix so continuous duplicate slots in the same day merge into 1 big cell
        skip_cell = {d: [False] * num_slots for d in days_order}
        rowspan_map = {d: [1] * num_slots for d in days_order}

        for d_col in days_order:
            s_i = 0
            while s_i < num_slots:
                raw_curr = grid_dict[d_col][s_i]
                b_curr, _ = extract_batch_specific_entry(raw_curr, batch_letter)
                sf_curr = match_subject_short_form(b_curr, subject_stats_by_short)

                if sf_curr and s_i < 8:
                    span = 1
                    while (
                        s_i + span < 8
                        and match_subject_short_form(
                            extract_batch_specific_entry(grid_dict[d_col][s_i + span], batch_letter)[0],
                            subject_stats_by_short,
                        )
                        == sf_curr
                    ):
                        skip_cell[d_col][s_i + span] = True
                        span += 1
                    rowspan_map[d_col][s_i] = span
                    s_i += span
                else:
                    s_i += 1

        html = '<table class="vertical-tt-table"><thead><tr>'
        html += '<th>TIME SLOT</th>'
        for d_col in days_order:
            html += f'<th>{d_col}</th>'
        html += '</tr></thead><tbody>'

        for slot_idx, slot_name in enumerate(TIME_SLOTS):
            html += '<tr>'
            html += f'<td class="tt-slot-col">{slot_name}</td>'
            for d_col in days_order:
                if skip_cell[d_col][slot_idx]:
                    continue

                raw_val = grid_dict[d_col][slot_idx]
                batch_entry, is_batch_lab = extract_batch_specific_entry(raw_val, batch_letter)
                matched_sf = match_subject_short_form(batch_entry, subject_stats_by_short)
                r_span = rowspan_map[d_col][slot_idx]

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
                if r_span > 1:
                    display_val = f"<b>{batch_entry}</b><br><span style='font-size:11px; color:#38bdf8;'>[1 Combined Bulk Lecture ({r_span} Hrs)]</span>"
                if is_batch_lab:
                    display_val += f'<br><span class="blinking-batch-badge">YOUR {student_batch.upper()} LAB</span>'

                span_attr = f' rowspan="{r_span}"' if r_span > 1 else ""
                html += f'<td class="{cell_class}"{span_attr}>{display_val}{att_subtext}</td>'
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
            st.caption(f"**Even Week Effective Dates:** 21–25 Sept | 5–9 Oct | 26–30 Oct | 9–13 Nov | 23–27 Nov 2026 (Bulk Lectures Merged | Showing Lab Attendance for **{student_batch}** | Target: {target_att_pct}%)")
            st.markdown(build_vertical_timetable_html(EVEN_WEEK_TIMETABLE_GRID), unsafe_allow_html=True)

        with tt_tab2:
            st.caption(f"**Odd Week Effective Dates:** 7–11 Sept | 28 Sept–2 Oct | 12–16 Oct | 1–6 Nov | 16–20 Nov | 30 Nov–4 Dec 2026 (Bulk Lectures Merged | Showing Lab Attendance for **{student_batch}** | Target: {target_att_pct}%)")
            st.markdown(build_vertical_timetable_html(ODD_WEEK_TIMETABLE_GRID), unsafe_allow_html=True)

        with tt_tab3:
            if os.path.exists(TIMETABLE_IMG_PATH):
                img_top_col1, img_top_col2 = st.columns([4, 1])
                with img_top_col2:
                    if st.button("Remove Timetable Image", type="secondary", width="stretch", disabled=guide_is_active):
                        try:
                            os.remove(TIMETABLE_IMG_PATH)
                        except Exception:
                            pass
                        st.rerun()
                st.image(TIMETABLE_IMG_PATH, caption="Official First Year Engineering Timetable (Even & Odd Weeks)", width="stretch")
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
                "Step 4: Merged Bulk Timetable & Batch Lab Attendance",
                "This arrow points to Section 5. Multi-hour bulk lectures like CP and 2-hour labs are merged into 1 combined block, and your batch labs highlight automatically. Click 'Got it' to finish!",
                "dashboard_guide_step",
                arrow_dir="left",
                finish_tour=True,
            )

# --- FOOTER SUBHEADING ---
st.markdown(
    '<div class="creator-footer">Designed and Created by Kanishka Maya Honrao</div>',
    unsafe_allow_html=True,
)
