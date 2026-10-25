import datetime
import json
import math
import os
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="75% Attendance & Credit Tracker",
    layout="wide",
)

# File paths for storage
VISITOR_LOG_FILE = "student_visitors_log.csv"
STUDENT_DB_FILE = "saved_students_compact.json"


# --- HELPER FUNCTIONS ---
def get_time_greeting():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    hour = ist_now.hour

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


def save_student_compact(email, name, branch, semesters_dict):
    db = load_all_students_db()
    key = email.strip().lower()

    compact_sems = {}
    for sem, df in semesters_dict.items():
        sem_data = {}
        for _, row in df.iterrows():
            sem_data[row["Course Code"]] = [
                int(row["Importance (1-3)"]),
                int(row["Attended"]),
            ]
        compact_sems[sem] = sem_data

    db[key] = {
        "email": email.strip().lower(),
        "name": name.strip(),
        "branch": branch,
        "last_updated": (
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(hours=5, minutes=30)
        ).strftime("%Y-%m-%d %H:%M:%S IST"),
        "data": compact_sems,
    }
    with open(STUDENT_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f)


def update_student_visit(email, name, branch):
    ist_time = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=5, minutes=30)
    ).strftime("%Y-%m-%d %H:%M:%S IST")
    
    if os.path.exists(VISITOR_LOG_FILE):
        log_df = pd.read_csv(VISITOR_LOG_FILE)
        if "Email" in log_df.columns and email.lower() in log_df["Email"].str.lower().values:
            log_df.loc[log_df["Email"].str.lower() == email.lower(), ["Student Name", "Branch", "Last Login Time"]] = [name.strip(), branch, ist_time]
        else:
            new_row = pd.DataFrame([{
                "Email": email.strip().lower(),
                "Student Name": name.strip(),
                "Branch": branch,
                "Last Login Time": ist_time,
            }])
            log_df = pd.concat([log_df, new_row], ignore_index=True)
    else:
        log_df = pd.DataFrame([{
            "Email": email.strip().lower(),
            "Student Name": name.strip(),
            "Branch": branch,
            "Last Login Time": ist_time,
        }])
    log_df.to_csv(VISITOR_LOG_FILE, index=False)


# --- SIDEBAR: Theme Settings ---
st.sidebar.header("Appearance")
theme_mode = st.sidebar.radio("Theme Mode:", ["Dark Mode", "Light Mode"], index=0)

if theme_mode == "Dark Mode":
    st.markdown(
        """
        <style>
        .stApp { background-color: #0e1117; color: #fafafa; }
        [data-testid="stSidebar"] { background-color: #161b22; color: #fafafa; }
        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #fafafa !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        .stApp { background-color: #ffffff; color: #111827; }
        [data-testid="stSidebar"] { background-color: #f3f4f6; color: #111827; }
        h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #111827 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# --- SEMESTER COURSE DATABASE (Sem I to Sem VIII) ---
SEMESTER_DATA = {
    "Semester I": [
        {"Course Category": "Compulsory", "Course Code": "25FE1BSC01", "Course Name": "Fundamentals of Engineering Mathematics I", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 45, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1BSC02", "Course Name": "Applied Physics", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1BSC03", "Course Name": "Engineering Chemistry", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1ESC01", "Course Name": "Engineering Graphics", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 30, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1ESC02", "Course Name": "Basic Electrical and Digital Electronics", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1VSEC01", "Course Name": "Workshop - 1", "Credits": 2, "Importance (1-3)": 2, "Total Lectures": 20, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1VSEC02", "Course Name": "Problem Solving using C programming", "Credits": 2, "Importance (1-3)": 3, "Total Lectures": 30, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE1VEC01", "Course Name": "Universal Human Values", "Credits": 2, "Importance (1-3)": 1, "Total Lectures": 20, "Attended": 0},
    ],
    "Semester II": [
        {"Course Category": "Compulsory", "Course Code": "25FE2BSC01", "Course Name": "Fundamentals of Engineering Mathematics II", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 45, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2BSC02", "Course Name": "Applied Physics II", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 30, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2BSC03", "Course Name": "Applied Chemistry II", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 30, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2ESC01", "Course Name": "Engineering Mechanics", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2VSEC01", "Course Name": "Workshop - 2", "Credits": 2, "Importance (1-3)": 2, "Total Lectures": 20, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2VSEC02", "Course Name": "Python Programming", "Credits": 2, "Importance (1-3)": 3, "Total Lectures": 30, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25FE2AEC01", "Course Name": "Professional Communication & Ethics", "Credits": 2, "Importance (1-3)": 1, "Total Lectures": 25, "Attended": 0},
    ],
    "Semester III": [
        {"Course Category": "Compulsory", "Course Code": "25SE3BSC01", "Course Name": "Engineering Mathematics III", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE3PCC01", "Course Name": "Data Structures and Algorithms", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE3PCC02", "Course Name": "Database Management Systems", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE3PCC03", "Course Name": "Computer Organization & Architecture", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE3VSEC01", "Course Name": "Object Oriented Programming Lab", "Credits": 2, "Importance (1-3)": 2, "Total Lectures": 25, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE3CEP01", "Course Name": "Mini Project - 1A", "Credits": 2, "Importance (1-3)": 2, "Total Lectures": 20, "Attended": 0},
    ],
    "Semester IV": [
        {"Course Category": "Compulsory", "Course Code": "25SE4BSC01", "Course Name": "Engineering Mathematics IV", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE4PCC01", "Course Name": "Analysis of Algorithms", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE4PCC02", "Course Name": "Operating Systems", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE4PCC03", "Course Name": "Microprocessors", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE4VSEC01", "Course Name": "Web Development Lab", "Credits": 2, "Importance (1-3)": 2, "Total Lectures": 25, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25SE4CEP01", "Course Name": "Mini Project - 1B", "Credits": 2, "Importance (1-3)": 2, "Total Lectures": 20, "Attended": 0},
    ],
    "Semester V": [
        {"Course Category": "Compulsory", "Course Code": "25TE5PCC01", "Course Name": "Theory of Computer Science", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE5PCC02", "Course Name": "Software Engineering", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE5PCC03", "Course Name": "Computer Networks", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE5PCC04", "Course Name": "Data Warehousing & Mining", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Elective", "Course Code": "25TE5PEC01", "Course Name": "Department Optional Course - I", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 30, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE5CEP01", "Course Name": "Mini Project - 2A", "Credits": 2, "Importance (1-3)": 2, "Total Lectures": 20, "Attended": 0},
    ],
    "Semester VI": [
        {"Course Category": "Compulsory", "Course Code": "25TE6PCC01", "Course Name": "System Programming & Compiler Construction", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE6PCC02", "Course Name": "Cryptography & System Security", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE6PCC03", "Course Name": "Mobile Computing", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE6PCC04", "Course Name": "Artificial Intelligence", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Elective", "Course Code": "25TE6PEC01", "Course Name": "Department Optional Course - II", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 30, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25TE6CEP01", "Course Name": "Mini Project - 2B", "Credits": 2, "Importance (1-3)": 2, "Total Lectures": 20, "Attended": 0},
    ],
    "Semester VII": [
        {"Course Category": "Compulsory", "Course Code": "25BE7PCC01", "Course Name": "Machine Learning", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25BE7PCC02", "Course Name": "Big Data Analytics", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Elective", "Course Code": "25BE7PEC01", "Course Name": "Department Optional Course - III", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Elective", "Course Code": "25BE7PEC02", "Course Name": "Department Optional Course - IV", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Elective", "Course Code": "25BE7OEC01", "Course Name": "Institute Optional Course - I", "Credits": 3, "Importance (1-3)": 1, "Total Lectures": 30, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25BE7PRJ01", "Course Name": "Major Project - I", "Credits": 3, "Importance (1-3)": 3, "Total Lectures": 25, "Attended": 0},
    ],
    "Semester VIII": [
        {"Course Category": "Compulsory", "Course Code": "25BE8PCC01", "Course Name": "Distributed Computing / Cloud Computing", "Credits": 4, "Importance (1-3)": 3, "Total Lectures": 40, "Attended": 0},
        {"Course Category": "Elective", "Course Code": "25BE8PEC01", "Course Name": "Department Optional Course - V", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Elective", "Course Code": "25BE8PEC02", "Course Name": "Department Optional Course - VI", "Credits": 3, "Importance (1-3)": 2, "Total Lectures": 35, "Attended": 0},
        {"Course Category": "Elective", "Course Code": "25BE8OEC01", "Course Name": "Institute Optional Course - II", "Credits": 3, "Importance (1-3)": 1, "Total Lectures": 30, "Attended": 0},
        {"Course Category": "Compulsory", "Course Code": "25BE8PRJ01", "Course Name": "Major Project - II", "Credits": 6, "Importance (1-3)": 3, "Total Lectures": 30, "Attended": 0},
    ],
}

BRANCH_OPTIONS = [
    "Basic Sciences and Humanities (FE)",
    "Computer Engineering",
    "Information Technology",
    "Electronics and Telecommunication Engineering",
    "Mechanical Engineering",
]

# --- PERSISTENT LOGIN VIA URL QUERY PARAMS ---
query_params = st.query_params
saved_email = query_params.get("email", "")

if "student_logged_in" not in st.session_state:
    if saved_email:
        all_db = load_all_students_db()
        user_record = all_db.get(saved_email.strip().lower(), {})
        if user_record:
            st.session_state.student_logged_in = True
            st.session_state.student_email = user_record.get("email", saved_email)
            st.session_state.student_name = user_record.get("name", "Student")
            st.session_state.student_branch = user_record.get("branch", "Computer Engineering")
        else:
            st.session_state.student_logged_in = False
    else:
        st.session_state.student_logged_in = False

# Load student data automatically if logged in
if st.session_state.get("student_logged_in", False):
    email_key = st.session_state.student_email.strip().lower()
    all_db = load_all_students_db()
    saved_student_data = all_db.get(email_key, {}).get("data", {})

    st.session_state.saved_semesters = {}
    for sem, courses in SEMESTER_DATA.items():
        temp_df = pd.DataFrame(courses)
        if sem in saved_student_data:
            sem_dict = saved_student_data[sem]
            for idx, row in temp_df.iterrows():
                code = row["Course Code"]
                if code in sem_dict:
                    temp_df.loc[idx, "Importance (1-3)"] = sem_dict[code][0]
                    temp_df.loc[idx, "Attended"] = sem_dict[code][1]
        temp_df.index = range(1, len(temp_df) + 1)
        st.session_state.saved_semesters[sem] = temp_df

# --- STEP 0: LOGIN & GMAIL VERIFICATION TO PREVENT IMPERSONATION ---
if not st.session_state.get("student_logged_in", False):
    st.title("DBIT 75% Attendance & Priority Tracker")
    st.subheader("Secure Gmail & Student Verification")
    st.write(
        "To prevent impersonation and protect your attendance records, please enter "
        "your Gmail address (ending with @gmail.com), your real full name, and your branch."
    )

    with st.form("student_login_form"):
        input_email = st.text_input("Enter Your Gmail Address (must end with @gmail.com):")
        input_name = st.text_input("Enter Your Real Full Name (As per college records):")
        input_branch = st.selectbox("Select Your Branch:", BRANCH_OPTIONS)
        submit_btn = st.form_submit_button("Authenticate & Enter Dashboard")

        if submit_btn:
            clean_email = input_email.strip().lower()
            clean_name = input_name.strip()

            if not clean_email.endswith("@gmail.com"):
                st.error("Invalid email domain. Please use a valid Gmail address ending with '@gmail.com'.")
            elif not clean_name:
                st.error("Please enter your real full name.")
            else:
                st.session_state.student_email = clean_email
                st.session_state.student_name = clean_name
                st.session_state.student_branch = input_branch
                st.session_state.student_logged_in = True

                # Save query params for persistent browser memory
                st.query_params["email"] = clean_email

                all_db = load_all_students_db()
                saved_student_data = all_db.get(clean_email, {}).get("data", {})

                st.session_state.saved_semesters = {}
                for sem, courses in SEMESTER_DATA.items():
                    temp_df = pd.DataFrame(courses)
                    if sem in saved_student_data:
                        sem_dict = saved_student_data[sem]
                        for idx, row in temp_df.iterrows():
                            code = row["Course Code"]
                            if code in sem_dict:
                                temp_df.loc[idx, "Importance (1-3)"] = sem_dict[code][0]
                                temp_df.loc[idx, "Attended"] = sem_dict[code][1]
                    temp_df.index = range(1, len(temp_df) + 1)
                    st.session_state.saved_semesters[sem] = temp_df

                save_student_compact(clean_email, clean_name, input_branch, st.session_state.saved_semesters)
                update_student_visit(clean_email, clean_name, input_branch)
                st.rerun()

    st.sidebar.markdown("---")
    with st.sidebar.expander("View Student Log (Admin)"):
        if os.path.exists(VISITOR_LOG_FILE):
            log_df = pd.read_csv(VISITOR_LOG_FILE)
            log_df.index = range(1, len(log_df) + 1)
            st.dataframe(log_df)
        else:
            st.write("No students have logged in yet.")

    st.stop()

# --- MAIN DASHBOARD ---
greeting = get_time_greeting()
st.title(f"{greeting}, {st.session_state.student_name}!")
st.subheader(f"Branch: {st.session_state.student_branch} | Gmail: {st.session_state.student_email}")
st.write(
    "Select your Semester from the sidebar, enter your attended lectures, "
    "and track how many classes you need to achieve 75% attendance."
)

st.sidebar.markdown("---")
st.sidebar.header("Student Profile")
st.sidebar.write(f"**Name:** {st.session_state.student_name}")
st.sidebar.write(f"**Email:** {st.session_state.student_email}")
st.sidebar.write(f"**Branch:** {st.session_state.student_branch}")
if st.sidebar.button("Switch Student / Logout"):
    st.query_params.clear()
    st.session_state.student_logged_in = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Select Your Semester")
selected_semester = st.sidebar.selectbox(
    "Choose Semester (1 to 8):",
    list(SEMESTER_DATA.keys()),
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.header("Save / Load Your Data")
uploaded_file = st.sidebar.file_uploader("Upload your saved CSV", type=["csv"])

if uploaded_file is not None:
    loaded_df = pd.read_csv(uploaded_file)
    loaded_df.index = range(1, len(loaded_df) + 1)
    st.session_state.saved_semesters[selected_semester] = loaded_df
    save_student_compact(
        st.session_state.student_email,
        st.session_state.student_name,
        st.session_state.student_branch,
        st.session_state.saved_semesters,
    )

if st.sidebar.button(f"Reset {selected_semester} to Default"):
    reset_df = pd.DataFrame(SEMESTER_DATA[selected_semester])
    reset_df.index = range(1, len(reset_df) + 1)
    st.session_state.saved_semesters[selected_semester] = reset_df
    save_student_compact(
        st.session_state.student_email,
        st.session_state.student_name,
        st.session_state.student_branch,
        st.session_state.saved_semesters,
    )
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Credit Settings")
target_credits = st.sidebar.number_input(
    f"Target Credits for {selected_semester}:",
    min_value=1,
    max_value=200,
    value=22,
    step=1,
)

# --- INTERACTIVE TABLE ---
st.subheader(f"1. {selected_semester} Subjects & Attendance")
st.caption(
    "Double-click any cell in the 'Importance (1-3)' or 'Attended' column to update your data."
)

edited_df = st.data_editor(
    st.session_state.saved_semesters[selected_semester],
    num_rows="fixed",
    disabled=["Course Category", "Course Code", "Course Name", "Credits", "Total Lectures"],
    column_config={
        "Importance (1-3)": st.column_config.NumberColumn(
            "Importance (1=Low, 3=High)", min_value=1, max_value=3, step=1
        ),
        "Total Lectures": st.column_config.NumberColumn(
            "Total Lectures Held", min_value=1, step=1
        ),
        "Attended": st.column_config.NumberColumn(
            "Lectures Attended", min_value=0, step=1
        ),
    },
)

st.session_state.saved_semesters[selected_semester] = edited_df.copy()
save_student_compact(
    st.session_state.student_email,
    st.session_state.student_name,
    st.session_state.student_branch,
    st.session_state.saved_semesters,
)
update_student_visit(
    st.session_state.student_email,
    st.session_state.student_name,
    st.session_state.student_branch,
)

# --- CALCULATIONS ---
if not edited_df.empty:
    df = edited_df.copy()

    df["Credits"] = pd.to_numeric(df["Credits"], errors="coerce").fillna(3).astype(int)
    df["Importance (1-3)"] = pd.to_numeric(df["Importance (1-3)"], errors="coerce").fillna(2).astype(int)
    df["Total Lectures"] = pd.to_numeric(df["Total Lectures"], errors="coerce").fillna(1).astype(int)
    df["Attended"] = pd.to_numeric(df["Attended"], errors="coerce").fillna(0).astype(int)

    df["Total Lectures"] = df["Total Lectures"].replace(0, 1)

    df["Current Attendance %"] = (
        (df["Attended"] / df["Total Lectures"]) * 100
    ).round(2)


    def calc_needed(row):
        att = row["Attended"]
        tot = row["Total Lectures"]
        if (att / tot) >= 0.75:
            return 0
        return max(0, math.ceil((0.75 * tot - att) / 0.25))


    def calc_bunks(row):
        att = row["Attended"]
        tot = row["Total Lectures"]
        if (att / tot) < 0.75:
            return 0
        return max(0, math.floor((att / 0.75) - tot))


    df["Classes Needed for 75%"] = df.apply(calc_needed, axis=1)
    df["Safe Bunks Left"] = df.apply(calc_bunks, axis=1)

    df["Status"] = df["Current Attendance %"].apply(
        lambda x: "Safe (>=75%)" if x >= 75 else "Shortage (<75%)"
    )

    df["Needs Attention"] = df["Classes Needed for 75%"] > 0
    df_sorted = df.sort_values(
        by=[
            "Needs Attention",
            "Importance (1-3)",
            "Credits",
            "Classes Needed for 75%",
        ],
        ascending=[False, False, False, False],
    ).drop(columns=["Needs Attention"])

    df_sorted.index = range(1, len(df_sorted) + 1)

    st.markdown("---")
    st.subheader(f"2. {selected_semester} Academic Dashboard")

    current_credits = int(df["Credits"].sum())
    credits_needed = max(0, int(target_credits - current_credits))
    overall_att = (df["Attended"].sum() / df["Total Lectures"].sum()) * 100
    total_classes_needed = int(df["Classes Needed for 75%"].sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Enrolled Credits", f"{current_credits}")
    col2.metric(
        "Credits Still Needed",
        f"{credits_needed}",
        delta=f"Target: {target_credits}",
        delta_color="off",
    )
    col3.metric(
        "Overall Attendance",
        f"{overall_att:.2f}%",
        delta="Safe" if overall_att >= 75 else "Below 75%",
        delta_color="normal" if overall_att >= 75 else "inverse",
    )
    col4.metric("Total Lectures to Recover", f"{total_classes_needed} classes")

    st.subheader("3. Priority Lecture Planner (Sorted by Urgency, Importance & Credits)")
    st.dataframe(df_sorted)

    st.markdown("---")
    st.subheader(f"4. {selected_semester} Visual Attendance Comparison")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.write("**Attended vs. Minimum Required Lectures (75% Target)**")
        lecture_compare_df = pd.DataFrame({
            "Attended Lectures": df["Attended"].values,
            "Required for 75%": df["Total Lectures"].apply(lambda x: math.ceil(0.75 * x)).values,
        }, index=df["Course Name"])
        st.bar_chart(lecture_compare_df)

    with chart_col2:
        st.write("**Current Attendance Percentage (%) by Subject**")
        pct_compare_df = pd.DataFrame({
            "Current Attendance %": df["Current Attendance %"].values,
        }, index=df["Course Name"])
        st.bar_chart(pct_compare_df)

    csv_data = edited_df.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        label=f"Download {selected_semester} Data",
        data=csv_data,
        file_name=f"{st.session_state.student_name.lower().replace(' ', '_')}_{selected_semester.lower().replace(' ', '_')}_attendance.csv",
        mime="text/csv",
    )

st.sidebar.markdown("---")
with st.sidebar.expander("View Student Log (Admin)"):
    if os.path.exists(VISITOR_LOG_FILE):
        log_df = pd.read_csv(VISITOR_LOG_FILE)
        log_df.index = range(1, len(log_df) + 1)
        st.dataframe(log_df)
    else:
        st.write("No students have logged in yet.")
