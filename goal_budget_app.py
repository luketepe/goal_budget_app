import datetime
import bcrypt
import json
import os
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

# --- Initialize session state ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "expenses" not in st.session_state:
    st.session_state.expenses = []

# --- Constants ---
USERS_FILE = "users.json"

# --- User management functions ---
def load_users():
    """Load all users from JSON file and convert deadlines to dates."""
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    except json.JSONDecodeError:
        users = {}

    # Convert deadline strings to date objects
    for user_data in users.values():
        for exp in user_data.get("expenses", []):
            if isinstance(exp.get("deadline"), str):
                exp["deadline"] = datetime.date.fromisoformat(exp["deadline"])
    return users

def save_users(users):
    """Save users to JSON file, converting dates to strings."""
    users_copy = {}
    for username, data in users.items():
        users_copy[username] = data.copy()
        expenses_copy = []
        for exp in data.get("expenses", []):
            exp_copy = exp.copy()
            if isinstance(exp_copy.get("deadline"), datetime.date):
                exp_copy["deadline"] = exp_copy["deadline"].isoformat()
            expenses_copy.append(exp_copy)
        users_copy[username]["expenses"] = expenses_copy
    with open(USERS_FILE, "w") as f:
        json.dump(users_copy, f, indent=2)

def sign_up(username, password, name):
    """Create a new user account."""
    users = load_users()
    if username in users:
        return False, "Username already exists"
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[username] = {"name": name, "password": hashed_pw, "expenses": []}
    save_users(users)
    return True, "Account created successfully"

def authenticate(username, password):
    """Authenticate an existing user."""
    users = load_users()
    if username in users and bcrypt.checkpw(password.encode(), users[username]["password"].encode()):
        return True, users[username]
    return False, None

# --- Streamlit UI ---
st.title("Goal & Budget App")

# --- Login / Sign Up ---
mode = st.radio("Select mode", ["Login", "Sign Up"])
current_user = None

if mode == "Sign Up":
    name = st.text_input("Name")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    if st.button("Create Account"):
        if password != confirm_password:
            st.error("Passwords do not match")
        else:
            success, msg = sign_up(username, password, name)
            if success:
                st.success(msg)
                st.session_state.current_user = username  # <--- add this
            else:
                st.error(msg)

elif mode == "Login":
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        success, user_data = authenticate(username, password)
        if success:
            st.success(f"Welcome {user_data['name']}!")
            st.session_state.current_user = username
            current_user = username
        else:
            st.error("Invalid username or password")

# --- Main App after Login ---
if st.session_state.current_user:
    current_user = st.session_state.current_user
    users = load_users()
    user_data = users[current_user]

    # Initialize default expenses if empty
    if not user_data.get("expenses"):
        today = datetime.date.today()
        user_data["expenses"] = [
            {"name": "Rent", "target": 1200.0, "deadline": today.replace(day=30)},
            {"name": "Utilities", "target": 125.0, "deadline": today.replace(day=30)},
            {"name": "Electric", "target": 50.0, "deadline": today.replace(day=30)},
            {"name": "Internet", "target": 30.0, "deadline": today.replace(day=30)},
            {"name": "Auto Insurance", "target": 500.0, "deadline": today + relativedelta(months=+6)},
            {"name": "Renters Insurance", "target": 150.0, "deadline": today + relativedelta(months=+12)},
        ]
        save_users(users)

    # Load expenses into session_state
    if "expenses" not in st.session_state:
        st.session_state.expenses = user_data["expenses"]

    # --- Paycheck Input ---
    st.subheader("Your Paycheck Info")
    paycheck = st.number_input("Enter this paycheck amount:", min_value=0.0, step=50.0)
    pay_date = st.date_input("Paycheck Date", value=datetime.date.today())

    # --- Editable Goals ---
    st.subheader("Your Expenses / Goals")
    for i, goal in enumerate(st.session_state.expenses):
        col1, col2, col3, col4 = st.columns([3,2,3,1])
        with col1:
            st.session_state.expenses[i]["name"] = st.text_input("Category Name", value=goal["name"], key=f"name_{i}")
        with col2:
            st.session_state.expenses[i]["target"] = st.number_input(
                "Target Amount", min_value=0.0, value=float(goal["target"]), step=10.0, key=f"target_{i}"
            )
        with col3:
            st.session_state.expenses[i]["deadline"] = st.date_input(
                "Deadline", value=goal["deadline"], key=f"deadline_{i}"
            )
        # --- Deleting a goal ---
        with col4:
            if st.button(f"Delete Goal {i + 1}", key=f"delete_{i}"):
                st.session_state.expenses.pop(i)
                users[current_user]["expenses"] = st.session_state.expenses
                save_users(users)  # Save immediately
                st.experimental_rerun()  # Optional, to refresh UI

    # --- Adding a goal ---
    if st.button("Add New Goal"):
        st.session_state.expenses.append({
            "name": "New Goal",
            "target": 0,
            "deadline": datetime.date.today()  # <-- must include deadline
        })
        users[current_user]["expenses"] = st.session_state.expenses
        save_users(users)  # Save immediately

    # Save updated expenses
    users[current_user]["expenses"] = st.session_state.expenses
    save_users(users)

    # --- Compute Allocations ---
    # --- Ensure deadlines exist and are proper datetime objects ---
    for goal in st.session_state.expenses:
        if "deadline" not in goal or not goal["deadline"]:
            goal["deadline"] = datetime.date.today()
        elif isinstance(goal["deadline"], str):
            goal["deadline"] = datetime.datetime.strptime(goal["deadline"], "%m-%d-%Y").date()

    df = pd.DataFrame(st.session_state.expenses)
    df["deadline"] = pd.to_datetime(df["deadline"])
    df["days_until_deadline"] = (df["deadline"] - pd.to_datetime(pay_date)).dt.days
    days_between_paychecks = 14
    df["paychecks_left"] = (df["days_until_deadline"] / days_between_paychecks).apply(lambda x: max(int(x)+1,1))
    df["per_paycheck"] = df["target"] / df["paychecks_left"]

    total_allocations = df["per_paycheck"].sum()
    leftover = max(paycheck - total_allocations, 0)

    # --- Display Allocations ---
    st.subheader("Allocations This Paycheck")
    st.dataframe(df[["name","target","deadline","paychecks_left","per_paycheck"]])
    st.write(f"**Total Allocations This Paycheck:** ${total_allocations:,.2f}")
    st.write(f"**Leftover / Spending Money:** ${leftover:,.2f}")

    # --- Pie Chart ---
    allocations_dict = {row["name"]: row["per_paycheck"] for _, row in df.iterrows()}
    allocations_dict["Leftover"] = leftover
    fig, ax = plt.subplots()
    ax.pie(allocations_dict.values(), labels=allocations_dict.keys(), autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    st.pyplot(fig)
