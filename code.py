import streamlit as st
import google.generativeai as genai
import hashlib
import json
import pandas as pd
import re
from datetime import datetime, timedelta
import time

# Configure your Gemini API key (replace with your actual API key)
genai.configure(api_key="AIzaSyASXv2rN1IEkpBCVwAxBH7n-JPOtuhTkDc")

try:
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    st.error(f"Error initializing gemini-2.0-flash: {e}")
    st.stop()

# --- Utility Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username, password):
    try:
        with open("users.txt", "r") as f:
            for line in f:
                stored_username, stored_password = line.strip().split(":")
                if username == stored_username and hash_password(password) == stored_password:
                    return True
    except FileNotFoundError:
        return False
    return False

# --- UI Components ---
def signup():
    st.subheader("✨ Sign Up ✨")
    new_username = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    if st.button("🌟 Sign Up 🌟"):
        if new_username and new_password:
            hashed_password = hash_password(new_password)
            try:
                with open("users.txt", "a") as f:
                    f.write(f"{new_username}:{hashed_password}\n")
                st.success("🎉 Sign up successful! Welcome! 🎉")
            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.warning("Please enter both username and password.")

def login():
    st.subheader("🔑 Login 🔑")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("🚀 Login 🚀"):
        if check_credentials(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("✨ Logged in successfully! ✨")
        else:
            st.error("Invalid username or password.")

def create_timetable_flow():
    st.header("📝 Task Details 📝")
    tasks = []
    task_count = st.number_input("Number of tasks", min_value=1, step=1)

    with st.expander("Enter Task Details 🌈"):
        for i in range(task_count):
            st.subheader(f"Task {i + 1} 🎈")
            col1, col2, col3 = st.columns(3)
            with col1:
                task_description = st.text_input(f"Description", key=f"desc_{i}")
            with col2:
                deadline = st.date_input(f"Deadline", key=f"deadline_{i}")
            with col3:
                expected_time = st.number_input(f"Hours", min_value=1, step=1, key=f"hours_{i}")
            tasks.append({
                "description": task_description,
                "deadline": str(deadline),
                "expected_time": expected_time
            })

    if st.button("✨ Generate Priority List ✨"):
        st.subheader("Priority List: 📋")
        for task in tasks:
            st.markdown(f"- {task['description']} (Deadline: {task['deadline']}, Time: {task['expected_time']} hours)")
        st.session_state.tasks = tasks
        st.session_state.next_page_timetable = True

    if 'next_page_timetable' not in st.session_state:
        st.session_state.next_page_timetable = False

    if st.session_state.next_page_timetable:
        timetable_days_hours_distraction()

def timetable_days_hours_distraction():
    st.header("📅 Study Preferences 📅")
    col1, col2 = st.columns(2)
    with col1:
        study_days = st.multiselect("Study Days: 📆", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        study_hours = st.number_input("Hours per day: ⏰", min_value=1, step=1)
        rest_hours = st.number_input("Rest hours per day: 😴", min_value=0, step=1)

    with col2:
        study_times = st.text_input("Study timings (e.g., 9:00 AM - 12:00 PM) 🕒")
        timetable_duration = st.text_input("Timetable duration (e.g., 1 week, 1 month) ⏳")
        distractions = st.text_area("Potential distractions and time taken 🚨")

    if st.button("🚀 Generate Timetable 🚀"):
        create_final_timetable(st.session_state.tasks, study_days, study_hours, study_times, distractions, rest_hours, timetable_duration)

def create_final_timetable(tasks, study_days, study_hours, study_times, distractions, rest_hours, timetable_duration):
    st.header("🎉 Final Timetable 🎉")

    # Calculate total available study hours
    total_available_hours = len(study_days) * study_hours
    total_task_hours = sum(task["expected_time"] for task in tasks)

    if total_task_hours > total_available_hours:
        st.warning(f"Warning: Not enough study hours to complete all tasks. You need {total_task_hours} hours but only have {total_available_hours} hours available.")
        # Suggest increasing study hours or days
        recommended_hours = total_task_hours // len(study_days) + (total_task_hours % len(study_days) > 0)  # Calculate recommended hours per day
        st.warning(f"Recommended: Increase study hours to {recommended_hours} per day or add more study days.")
        return  # Don't generate the timetable

    prompt = f"""
    Generate a study timetable in JSON format based on:
    Tasks: {tasks}
    Study Days: {study_days}
    Study Hours per Day: {study_hours}
    Study Times: {study_times}
    Potential Distractions: {distractions}
    Rest Hours per Day: {rest_hours}
    Timetable Duration: {timetable_duration}

    The JSON should be formatted EXACTLY as follows, with no extra text:
    {{
        "timetable": [
            {{"date": "YYYY-MM-DD", "day": "Day of week", "start_time": "HH:MM", "end_time": "HH:MM", "tasks": ["Task 1", "Task 2", ...]}}
        ]
    }}
    Ensure that the 'day' key value matches one of the study days given.
    """

    try:
        with st.spinner('Generating Timetable...'):
            response = model.generate_content(prompt)

            if response.text:
                try:
                    timetable_data = json.loads(response.text)

                    if "timetable" in timetable_data and isinstance(timetable_data["timetable"], list):
                        df = pd.DataFrame(timetable_data["timetable"])
                        if not df.empty:
                            st.dataframe(df.style.set_table_styles(
                                [{'selector': 'th, td', 'props': [('text-align', 'left')]}]
                            ))
                        else:
                            st.warning("Generated timetable is empty.")
                    else:
                        st.error("Invalid 'timetable' structure in the JSON response.")
                        st.write(response.text)

                except json.JSONDecodeError:
                    st.error("Invalid JSON format from the model. Attempting to extract data...")

                    date_pattern = r'"date":\s*"([^"]*)"'
                    day_pattern = r'"day":\s*"([^"]*)"'
                    start_time_pattern = r'"start_time":\s*"([^"]*)"'
                    end_time_pattern = r'"end_time":\s*"([^"]*)"'
                    tasks_pattern = r'"tasks":\s*\[([^\]]*)\]'

                    dates = re.findall(date_pattern, response.text)
                    days = re.findall(day_pattern, response.text)
                    start_times = re.findall(start_time_pattern, response.text)
                    end_times = re.findall(end_time_pattern, response.text)
                    tasks_lists = re.findall(tasks_pattern, response.text)

                    if dates and days and start_times and end_times and tasks_lists:
                        data = []
                        for i in range(min(len(dates), len(days), len(start_times), len(end_times), len(tasks_lists))):
                            tasks_str = tasks_lists[i]
                            tasks_clean = [t.strip().strip('"') for t in tasks_str.split(',')]
                            data.append({
                                "date": dates[i],
                                "day": days[i],
                                "start_time": start_times[i],
                                "end_time": end_times[i],
                                "tasks": tasks_clean
                            })

                        if data:
                            df = pd.DataFrame(data)
                            st.dataframe(df.style.set_table_styles(
                                [{'selector': 'th, td', 'props': [('text-align', 'left')]}]
                            ))
                        else:
                            st.error("Could not extract enough data to create a table.")
                            st.write(response.text)
                    else:
                        st.error("Could not extract data using regular expressions.")
                        st.write(response.text)

                except Exception as e:
                    st.error(f"An error occurred during DataFrame creation: {e}")
                    st.write(response.text)

            else:
                st.error("The model did not return any text.")

    except Exception as e:
        st.error(f"An error occurred: {e}")

def create_exam_schedule_flow():
    st.header("📚 Exam Study Planner 📚")
    exam_count = st.number_input("Number of Exams", min_value=1, step=1)
    exams = []

    for i in range(exam_count):
        st.subheader(f"Exam {i + 1} 🎓")
        exam_name = st.text_input(f"Exam Name", key=f"exam_name_{i}")
        exam_date = st.date_input(f"Exam Date", key=f"exam_date_{i}")

        lessons = []
        lesson_count = st.number_input(f"Number of Lessons in {exam_name}", min_value=1, step=1, key=f"lesson_count_{i}")

        for j in range(lesson_count):
            st.subheader(f"Lesson {j + 1} 📖")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                lesson_name = st.text_input(f"Lesson Name", key=f"lesson_name_{i}_{j}")
            with col2:
                pages = st.number_input(f"Number of Pages", min_value=1, step=1, key=f"pages_{i}_{j}")
            with col3:
                difficulty = st.number_input(f"Difficulty (1-5)", min_value=1, max_value=5, step=1, key=f"difficulty_{i}_{j}")

            lessons.append({
                "lesson_name": lesson_name,
                "pages": pages,
                "difficulty": difficulty,
            })

        exams.append({
            "exam_name": exam_name,
            "exam_date": exam_date,
            "lessons": lessons
        })

    if st.button("🚀 Generate Exam Schedule 🚀"):
        create_final_exam_schedule(exams)

def create_final_exam_schedule(exams):
    st.header("🎉 Recommended Exam Preparation Schedule 🎉")
    schedule_data = []
    current_date = datetime.now().date()
    with st.spinner("Generating exam schedule... ⏳"):
        time.sleep(1) # simulate some work

        for exam in exams:
            exam_date = exam["exam_date"]
            days_until_exam = (exam_date - current_date).days

            if days_until_exam <= 1:
                st.warning(f"Warning: Exam '{exam['exam_name']}' is today or in the past.")
                continue  # Skip to the next exam

            total_pages = sum(lesson["pages"] for lesson in exam["lessons"])
            daily_pages = total_pages // days_until_exam
            remaining_pages = total_pages % days_until_exam

            for day in range(days_until_exam):
                study_date = current_date + timedelta(days=day)
                pages_to_study = daily_pages

                if day == days_until_exam - 1:
                    pages_to_study += remaining_pages  # Add the remaining pages to the last day

                schedule_data.append({
                    "Exam Name": exam["exam_name"],
                    "Date": study_date.strftime("%Y-%m-%d"),
                    "Pages to Study": pages_to_study,
                })

        if schedule_data:
            df = pd.DataFrame(schedule_data)
            st.dataframe(df.style.set_table_styles([{'selector': 'th, td', 'props': [('text-align', 'left')]}]))
        else:
            st.warning("No exam schedules to display.")

# --- Main App ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

if not st.session_state.logged_in:
    choice = st.radio("Choose:", ["Login 🔑", "Sign Up ✨"])
    if choice == "Sign Up ✨":
        signup()
    else:
        login()
else:
    st.markdown(f"<h1 style='text-align: center;'>🎉 Welcome, {st.session_state.username}! 🎉</h1>", unsafe_allow_html=True)
    st.header("What are you here for? 🤔")
    purpose = st.radio("Choose your purpose:", [
        "To create a timetable with progress checker 📅",
        "To create a schedule for exam preparation with progress checker 📚"
    ])
    if st.button("🚀 Next 🚀"):
        st.session_state.purpose = purpose
        st.session_state.next_page = True

    if 'next_page' in st.session_state and st.session_state.next_page:
        if st.session_state.purpose == "To create a timetable with progress checker 📅":
            create_timetable_flow()
        else:
            create_exam_schedule_flow()

# --- Styling ---
st.markdown(
    """
    <style>
    .stRadio > label > div[data-baseweb="radio"] > div {
        display: flex;
        align-items: center;
    }
    .stRadio > label > div[data-baseweb="radio"] > div > div {
        margin-left: 5px;
    }
    .stButton > button {
        background-color: #90EE90;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        transition: transform 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.05);
    }
    .stTextInput > div > div > input {
        border-radius: 5px;
        border: 1px solid #ccc;
        padding: 8px;
    }
    .stDateInput > div > div > input {
        border-radius: 5px;
        border: 1px solid #ccc;
        padding: 8px;
    }
    .stNumberInput > div > div > input {
        border-radius: 5px;
        border: 1px solid #ccc;
        padding: 8px;
    }
    .stTextArea > div > div > textarea {
        border-radius: 5px;
        border: 1px solid #ccc;
        padding: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
