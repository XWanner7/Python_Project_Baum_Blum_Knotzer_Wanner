import streamlit as st
from datetime import datetime, timedelta

# --- Configuration ---
st.set_page_config(page_title="Study Planner", layout="wide", page_icon="📚")

# --- Session State Initialization ---
if "subjects" not in st.session_state:
    st.session_state.subjects = []


# Calculates the percentage of completed study hours.
# The function takes the completed hours and total required hours as input.
# It avoids division by zero and caps the progress at 100 percent.
def calculate_progress(completed, total):
    if total == 0:
        return 0.0
    return min((completed / total) * 100, 100.0)


# Classifies the workload based on the required daily study hours.
# The function returns a text label that shows whether the workload is easy,
# manageable, intense, or very intense.
def classify_workload(daily_hours):
    if daily_hours <= 1.5:
        return "Easy"
    elif daily_hours <= 3:
        return "Manageable"
    elif daily_hours <= 5:
        return "Intense"
    else:
        return "Very intense"


# Determines the priority of a subject based on how many days are left.
# The fewer days are left before the exam, the higher the priority becomes.
def get_priority(days_left):
    if days_left <= 3:
        return "High"
    elif days_left <= 7:
        return "Medium"
    else:
        return "Low"


# Displays the sidebar navigation.
# The function shows the app title, the current date, and lets the user choose
# which page of the study planner should be opened.
def show_navigation():
    st.sidebar.title("Study Planner")
    st.sidebar.write(f"Date: {datetime.now().strftime('%Y-%m-%d')}")

    return st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Add Subject", "Update Progress", "Weekly Plan", "Delete Subject"]
    )


# Displays the dashboard page.
# The function calculates total hours, remaining hours, overall progress,
# subject progress, workload levels, priorities, and risk warnings.
def show_dashboard():
    st.title("📊 Dashboard")

    if not st.session_state.subjects:
        st.info("No subjects available yet. Add new subjects via the menu.")
        return

    total_req = sum(s["total_hours"] for s in st.session_state.subjects)
    total_comp = sum(s["completed_hours"] for s in st.session_state.subjects)
    total_rem = sum(max(0, s["total_hours"] - s["completed_hours"]) for s in st.session_state.subjects)
    overall_prog = calculate_progress(total_comp, total_req)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Subjects", len(st.session_state.subjects))
    col2.metric("Total Hours", f"{total_req:.1f}h")
    col3.metric("Remaining Hours", f"{total_rem:.1f}h")
    col4.metric("Overall Progress", f"{overall_prog:.1f}%")

    st.progress(overall_prog / 100)
    st.divider()

    st.subheader("Subject Overview")
    risks = []

    for subject in st.session_state.subjects:
        show_subject_card(subject, risks)

    st.divider()
    show_risk_message(risks)


# Displays one subject card on the dashboard.
# The function calculates the remaining hours, daily target, progress,
# workload, and priority for one subject and presents them visually.
def show_subject_card(subject, risks):
    rem_hours = max(0, subject["total_hours"] - subject["completed_hours"])
    daily_h = rem_hours / subject["days_left"] if subject["days_left"] > 0 else 0
    progress = calculate_progress(subject["completed_hours"], subject["total_hours"])
    priority = get_priority(subject["days_left"])

    if daily_h > 5 or subject["days_left"] <= 3:
        risks.append(subject["name"])

    with st.container(border=True):
        scol1, scol2, scol3 = st.columns([2, 3, 2])

        with scol1:
            st.markdown(f"### {subject['name']}")
            priority_color = "red" if priority == "High" else "orange" if priority == "Medium" else "green"
            st.markdown(f"**Priority:** :{priority_color}[{priority}]")

        with scol2:
            st.write(
                f"**Progress:** {subject['completed_hours']:.1f}h / "
                f"{subject['total_hours']:.1f}h ({progress:.1f}%)"
            )
            st.progress(progress / 100)

        with scol3:
            st.write(f"**Days left:** {subject['days_left']}")
            st.write(f"**Daily target:** {daily_h:.1f}h ({classify_workload(daily_h)})")


# Displays a risk message for the dashboard.
# If risky subjects were found, the function shows a warning.
# Otherwise, it confirms that the workload is currently on track.
def show_risk_message(risks):
    if risks:
        st.warning(
            f"Warning, high risk for the following subjects: {', '.join(risks)}. "
            "The exams are very close or the daily workload is extremely high."
        )
    else:
        st.success("Risk Analysis: Everything is on track. No critical workload detected.")


# Displays the page for adding a new subject.
# The function uses a form to collect subject name, days until the exam,
# and required study hours, then stores the subject in session state.
def show_add_subject_page():
    st.title("➕ Add New Subject")

    with st.form("add_subject_form", clear_on_submit=True):
        name = st.text_input("Subject Name (e.g., Corporate Finance)")
        col1, col2 = st.columns(2)
        days_left = col1.number_input("Days until exam", min_value=1, step=1)
        total_hours = col2.number_input("Total study hours needed", min_value=0.5, step=0.5)

        submitted = st.form_submit_button("Save")

        if submitted:
            save_subject(name, days_left, total_hours)


# Saves a new subject after validating the input.
# The function checks whether the name is empty or already exists.
# If the input is valid, it appends a new subject dictionary to session state.
def save_subject(name, days_left, total_hours):
    clean_name = name.strip()

    if not clean_name:
        st.error("Please enter a valid subject name.")
    elif any(s["name"].lower() == clean_name.lower() for s in st.session_state.subjects):
        st.error("This subject already exists.")
    else:
        total_daily_hours = 0
        for subject in st.session_state.subjects:
            remaining = max(0, subject["total_hours"] - subject["completed_hours"])
            total_daily_hours += remaining / subject["days_left"]

        new_daily_hours = total_hours / days_left

        if total_daily_hours + new_daily_hours > 14:
            st.error("Study plan exceeds the maximum limit of 14 study hours per day.")
            return

        st.session_state.subjects.append({
            "name": clean_name,
            "days_left": days_left,
            "total_hours": total_hours,
            "completed_hours": 0.0
        })
        st.success(f"Subject '{clean_name}' was successfully added.")


# Displays the page for updating study progress.
# The function lets the user select a subject and add newly completed study hours.
# The completed hours are capped at the total required hours.
def show_update_progress_page():
    st.title("📈 Update Progress")

    if not st.session_state.subjects:
        st.info("There are no subjects to update yet.")
        return

    subject_names = [s["name"] for s in st.session_state.subjects]
    selected_name = st.selectbox("Select a subject", subject_names)
    subject = next(s for s in st.session_state.subjects if s["name"] == selected_name)

    st.write(f"Studied so far: {subject['completed_hours']} out of {subject['total_hours']} hours")

    with st.form("update_progress_form"):
        add_hours = st.number_input("Enter additional studied hours", min_value=0.0, step=0.5)
        submitted = st.form_submit_button("Update")

        if submitted:
            update_subject_progress(subject, add_hours)


# Updates the completed hours of one selected subject.
# The function only accepts values greater than zero and then refreshes the app
# so the new progress is shown immediately.
def update_subject_progress(subject, add_hours):
    if add_hours > 0:
        subject["completed_hours"] = min(subject["total_hours"], subject["completed_hours"] + add_hours)
        st.success("Progress saved!")
        st.rerun()
    else:
        st.warning("Please enter a value greater than 0.")


# Displays the weekly study plan page.
# The function finds all unfinished subjects and distributes their remaining
# study hours across the next seven days or until the exam date.
def show_weekly_plan_page():
    st.title("📅 Weekly Study Plan")

    active_subjects = [s for s in st.session_state.subjects if s["total_hours"] > s["completed_hours"]]

    if not active_subjects:
        st.info("There are currently no open study goals.")
        return

    # Start the 7-day plan with the current day instead of always starting on Monday
    weekdays = [
        (datetime.now() + timedelta(days=i)).strftime("%A")
        for i in range(7)
    ]

    plan_data = create_weekly_plan_data(active_subjects, weekdays)
    display_weekly_plan(plan_data, weekdays)


# Creates the weekly plan data structure.
# The function calculates daily study hours for each active subject and assigns
# them to the relevant weekdays.
def create_weekly_plan_data(active_subjects, weekdays):
    plan_data = {day: [] for day in weekdays}

    for subject in active_subjects:
        planning_days = min(subject["days_left"], 7)
        rem_hours = subject["total_hours"] - subject["completed_hours"]
        daily_hours = rem_hours / planning_days

        for i in range(planning_days):
            day_name = weekdays[i]
            plan_data[day_name].append(f"{subject['name']}: {daily_hours:.1f}h")

    return plan_data


# Displays the weekly plan in seven columns.
# Each column represents one weekday and shows the planned study tasks for that day.
def display_weekly_plan(plan_data, weekdays):
    cols = st.columns(7)

    for i, day in enumerate(weekdays):
        with cols[i]:
            st.markdown(f"**{day}**")
            if plan_data[day]:
                for task in plan_data[day]:
                    st.write(task)
            else:
                st.write("Free")


# Displays the page for deleting a subject.
# The function lets the user select a subject and removes it permanently
# from the session state after clicking the delete button.
def show_delete_subject_page():
    st.title("🗑️ Delete Subject")

    if not st.session_state.subjects:
        st.info("No subjects available to delete.")
        return

    subject_names = [s["name"] for s in st.session_state.subjects]
    selected_name = st.selectbox("Which subject should be deleted?", subject_names)

    if st.button("Permanently delete", type="primary"):
        st.session_state.subjects = [s for s in st.session_state.subjects if s["name"] != selected_name]
        st.success(f"Subject '{selected_name}' was deleted.")
        st.rerun()


# Controls which page is shown based on the sidebar selection.
# The function receives the selected menu option and calls the matching page function.
def show_selected_page(menu):
    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Add Subject":
        show_add_subject_page()
    elif menu == "Update Progress":
        show_update_progress_page()
    elif menu == "Weekly Plan":
        show_weekly_plan_page()
    elif menu == "Delete Subject":
        show_delete_subject_page()


# Main function that starts the Streamlit app.
# It displays the navigation first and then opens the selected page.
def main():
    menu = show_navigation()
    show_selected_page(menu)


main()
