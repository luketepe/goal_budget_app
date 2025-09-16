# goal_budget_app.py
import datetime
import bcrypt
import json
import math
import os
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

# ----------------------------
# Constants / Filenames
# ----------------------------
USERS_FILE = "users.json"
col1, col2 = st.columns([2,3])
with col1:
    paycheck = st.number_input("Enter paycheck amount", min_value = 0.0, step = 25.0, value = 0.0)
with col2:
    additional_income = st.number_input("Enter additional income", min_value = 0.0, step = 25.0, value = 0.0)
total_money = paycheck + additional_income

pay_frequency = st.selectbox("Pay frequency", ["Weekly", "Biweekly", "Monthly"], index = 1)
if pay_frequency == "Weekly":
    days_between_paychecks = 7
elif pay_frequency == "Monthly":
    days_between_paychecks = 30
else:
    days_between_paychecks =14

# ----------------------------
# Helpers: load/save users (handles date conversion)
# ----------------------------
def load_users():
    """Load users from file, converting date strings to date objects where needed."""
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    except json.JSONDecodeError:
        users = {}

    # Convert date strings to date objects for each goal
    for user_data in users.values():
        for exp in user_data.get("expenses", []):
            # deadline
            if isinstance(exp.get("deadline"), str):
                try:
                    exp["deadline"] = datetime.date.fromisoformat(exp["deadline"])
                except Exception:
                    exp["deadline"] = datetime.date.today()
            # created
            if isinstance(exp.get("created"), str):
                try:
                    exp["created"] = datetime.date.fromisoformat(exp["created"])
                except Exception:
                    exp["created"] = datetime.date.today()
            # ensure numeric fields exist
            if "target" not in exp:
                exp["target"] = 0.0
            if "saved_so_far" not in exp:
                exp["saved_so_far"] = 0.0
    return users

def save_users(users):
    """Save users to JSON; convert date objects to isoformat strings."""
    users_copy = {}
    for username, data in users.items():
        users_copy[username] = data.copy()
        expenses_copy = []
        for exp in data.get("expenses", []):
            exp_copy = exp.copy()
            # convert date objects
            if isinstance(exp_copy.get("deadline"), (datetime.date, datetime.datetime)):
                exp_copy["deadline"] = exp_copy["deadline"].isoformat()
            if isinstance(exp_copy.get("created"), (datetime.date, datetime.datetime)):
                exp_copy["created"] = exp_copy["created"].isoformat()
            expenses_copy.append(exp_copy)
        users_copy[username]["expenses"] = expenses_copy
    with open(USERS_FILE, "w") as f:
        json.dump(users_copy, f, indent=2)

# ----------------------------
# Authentication / User mgmt
# ----------------------------
def sign_up(username, password, name):
    users = load_users()
    if username in users:
        return False, "Username already exists"
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[username] = {"name": name, "password": hashed_pw, "expenses": []}
    save_users(users)
    return True, "Account created successfully"

def authenticate(username, password):
    users = load_users()
    if username in users and bcrypt.checkpw(password.encode(), users[username]["password"].encode()):
        return True, users[username]
    return False, None

# ----------------------------
# Streamlit session init
# ----------------------------
st.set_page_config(page_title="Goal & Budget App", layout="wide")
st.title("Goal & Budget App")

if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "expenses" not in st.session_state:
    st.session_state.expenses = []

# ----------------------------
# Login / Sign up UI
# ----------------------------
mode = st.radio("Select mode", ["Login", "Sign Up"], horizontal=True)

if mode == "Sign Up":
    with st.form("signup_form"):
        name = st.text_input("Name")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        create = st.form_submit_button("Create Account")
        if create:
            if password != confirm_password:
                st.error("Passwords do not match")
            elif not username or not password:
                st.error("Username and password cannot be empty")
            else:
                success, msg = sign_up(username, password, name)
                if success:
                    st.success(msg)
                    st.session_state.current_user = username
                    # Immediately sync session expenses after creating account
                    users = load_users()
                    st.session_state.expenses = users[username].get("expenses", [])
                    st.experimental_rerun()
                else:
                    st.error(msg)

elif mode == "Login":
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_pw")
        login = st.form_submit_button("Login")
        if login:
            success, user_data = authenticate(username, password)
            if success:
                st.success(f"Welcome {user_data['name']}!")
                st.session_state.current_user = username
                # Sync session expenses from file on login
                users = load_users()
                st.session_state.expenses = users[username].get("expenses", [])
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

# ----------------------------
# Main App for logged-in users
# ----------------------------
if st.session_state.current_user:
    current_user = st.session_state.current_user
    users = load_users()

    # Ensure user's structure exists (in case file changed externally)
    if current_user not in users:
        users[current_user] = {"name": current_user, "password": "", "expenses": []}

    # Always re-sync session_state.expenses from file at the start of each run
    user_data = users[current_user]
    # ensure default keys for existing goals
    if "expenses" not in user_data:
        user_data["expenses"] = []
    # update session state to file copy (so edits persist properly)
    st.session_state.expenses = user_data["expenses"]

    # If user has no expenses, initialize some sensible defaults (with created dates)
    if not st.session_state.expenses:
        today = datetime.date.today()
        defaults = [
            {"name": "Rent", "target": 1200.0, "deadline": today.replace(day=28) if today.day <=28 else (today + relativedelta(months=+1)).replace(day=28),
             "created": today - relativedelta(months=2), "saved_so_far": 0.0},
            {"name": "Utilities", "target": 125.0, "deadline": today.replace(day=28) if today.day <=28 else (today + relativedelta(months=+1)).replace(day=28),
             "created": today - relativedelta(months=2), "saved_so_far": 0.0},
            {"name": "Auto Insurance", "target": 500.0, "deadline": today + relativedelta(months=6), "created": today, "saved_so_far": 0.0},
        ]
        st.session_state.expenses = defaults
        users[current_user]["expenses"] = st.session_state.expenses
        save_users(users)
        st.experimental_rerun()

    # ----------------------------
    # Paycheck inputs
    # ----------------------------
    st.subheader("Paycheck Info")
    col_pay1, col_pay2, col_pay3 = st.columns([2,2,1])
    with col_pay1:
        paycheck = st.number_input("Enter this paycheck amount", min_value=0.0, step=25.0, value=0.0)
    with col_pay2:
        pay_date = st.date_input("Paycheck Date", value=datetime.date.today())
    with col_pay3:
        # Allow user to choose paycheck frequency quickly (convenience)
        freq = st.selectbox("Pay frequency", ["Bi-weekly (14d)", "Weekly (7d)", "Monthly (30d)"], index=0)
        if freq.startswith("Weekly"):
            days_between_paychecks = 7
        elif freq.startswith("Monthly"):
            days_between_paychecks = 30
        else:
            days_between_paychecks = 14

    # ----------------------------
    # Editable Goals UI
    # ----------------------------
    st.subheader("Your Expenses / Goals")
    # Ensure each goal has necessary keys
    for goal in st.session_state.expenses:
        if "name" not in goal:
            goal["name"] = "Unnamed Goal"
        if "target" not in goal:
            goal["target"] = 0.0
        if "deadline" not in goal or not goal["deadline"]:
            goal["deadline"] = datetime.date.today()
        if "created" not in goal or not goal["created"]:
            # assume created today if missing
            goal["created"] = datetime.date.today()
        if isinstance(goal.get("deadline"), str):
            try:
                goal["deadline"] = datetime.date.fromisoformat(goal["deadline"])
            except Exception:
                goal["deadline"] = datetime.date.today()
        if isinstance(goal.get("created"), str):
            try:
                goal["created"] = datetime.date.fromisoformat(goal["created"])
            except Exception:
                goal["created"] = datetime.date.today()
        if "saved_so_far" not in goal:
            goal["saved_so_far"] = 0.0

    # Render editable rows
    remove_index = None
    for i, goal in enumerate(list(st.session_state.expenses)):  # use list() because we may mutate
        st.markdown("---")
        cols = st.columns([2, 1, 1, 1, 1])
        with cols[0]:
            st.session_state.expenses[i]["name"] = st.text_input("Category", value=goal["name"], key=f"name_{i}")
        with cols[1]:
            st.session_state.expenses[i]["target"] = st.number_input(
                "Target Amount", min_value=0.0, value=float(goal["target"]), step=10.0, key=f"target_{i}"
            )
        with cols[2]:
            st.session_state.expenses[i]["deadline"] = st.date_input(
                "Deadline", value=goal["deadline"], key=f"deadline_{i}"
            )
        with cols[3]:
            st.session_state.expenses[i]["saved_so_far"] = st.number_input(
                "Saved so far", min_value=0.0, value=float(goal.get("saved_so_far", 0.0)), step=5.0, key=f"saved_{i}"
            )
        with cols[4]:
            if st.button("Delete", key=f"delete_{i}"):
                remove_index = i

        # progress bar and quick info under the row
        # We'll compute display values below, but give a placeholder that will update on rerun
        st.write(f"Created: {st.session_state.expenses[i].get('created')}, Deadline: {st.session_state.expenses[i].get('deadline')}")

    # Delete performed after loop to avoid index shift issues
    if remove_index is not None:
        st.session_state.expenses.pop(remove_index)
        users[current_user]["expenses"] = st.session_state.expenses
        save_users(users)
        st.experimental_rerun()

    # Add new goal button
    if st.button("Add New Goal"):
        new_goal = {
            "name": "New Goal",
            "target": 0.0,
            "deadline": datetime.date.today(),
            "created": datetime.date.today(),
            "saved_so_far": 0.0,
        }
        st.session_state.expenses.append(new_goal)
        users[current_user]["expenses"] = st.session_state.expenses
        save_users(users)
        st.experimental_rerun()

    # Save any edits made in-place
    users[current_user]["expenses"] = st.session_state.expenses
    save_users(users)

    # ----------------------------
    # Allocation computations
    # ----------------------------
    df = pd.DataFrame(st.session_state.expenses)
    # Normalize dates and numeric columns
    df["deadline"] = pd.to_datetime(df["deadline"]).dt.date
    df["created"] = pd.to_datetime(df["created"]).dt.date
    df["target"] = pd.to_numeric(df["target"], errors="coerce").fillna(0.0)
    df["saved_so_far"] = pd.to_numeric(df["saved_so_far"], errors="coerce").fillna(0.0)

    # days until deadline relative to the paycheck date (user-provided)
    df["days_until_deadline"] = (pd.to_datetime(df["deadline"]) - pd.to_datetime(pay_date)).dt.days

    # number of paychecks left INCLUDING the current paycheck (minimum 1)
    df["paychecks_left"] = df["days_until_deadline"].apply(lambda d: max(math.ceil(d / days_between_paychecks), 1))

    # total planned paychecks for the goal based on created->deadline interval (minimum 1)
    df["total_paychecks"] = ((pd.to_datetime(df["deadline"]) - pd.to_datetime(df["created"])).dt.days).apply(
        lambda d: max(math.ceil(max(d, 0) / days_between_paychecks), 1)
    )

    # how many paychecks have already elapsed since creation (cannot be negative)
    df["paychecks_elapsed"] = (df["total_paychecks"] - df["paychecks_left"]).apply(lambda x: max(int(x), 0))

    # planned per paycheck across the whole plan
    df["planned_per_paycheck"] = df.apply(lambda r: (r["target"] / r["total_paychecks"]) if r["total_paychecks"] > 0 else 0.0, axis=1)

    # Auto-saved amount (based on planned_per_paycheck * elapsed) — used only if saved_so_far is zero
    df["auto_saved"] = df["planned_per_paycheck"] * df["paychecks_elapsed"]

    # If user provided saved_so_far > 0, keep it. If 0 or missing, auto-fill with auto_saved
    df["effective_saved"] = df.apply(
        lambda r: r["saved_so_far"] if (r["saved_so_far"] is not None and r["saved_so_far"] > 0) else r["auto_saved"], axis=1
    )

    # remaining and per-paycheck recalculated
    df["remaining"] = (df["target"] - df["effective_saved"]).apply(lambda x: max(x, 0.0))
    df["per_paycheck"] = df.apply(
        lambda r: (r["remaining"] / r["paychecks_left"]) if r["paychecks_left"] > 0 else r["remaining"], axis=1
    )

    # Totals
    total_allocations = df["per_paycheck"].sum()
    leftover = max(paycheck - total_allocations, 0.0)

    # ----------------------------
    # Display results
    # ----------------------------
    st.subheader("Allocations This Paycheck")
    display_df = df[["name", "target", "deadline", "created", "effective_saved", "remaining", "paychecks_left", "per_paycheck", "planned_per_paycheck"]].copy()
    display_df = display_df.rename(columns={
        "effective_saved": "saved_so_far (effective)",
        "planned_per_paycheck": "planned_per_paycheck (whole plan)"
    })
    # Format numbers nicely
    pd.options.display.float_format = "${:,.2f}".format
    st.dataframe(display_df.reset_index(drop=True))

    st.write(f"**Total Allocations This Paycheck:** ${total_allocations:,.2f}")
    st.write(f"**Leftover / Spending Money:** ${leftover:,.2f}")

    # Per-goal progress bars (visual)
    st.subheader("Progress Toward Each Goal")
    for idx, row in df.iterrows():
        col1, col2 = st.columns([3,1])
        with col1:
            st.write(f"**{row['name']}** — Target: ${row['target']:,.2f} • Saved: ${row['effective_saved']:,.2f} • Remaining: ${row['remaining']:,.2f}")
            # progress as fraction of target, clipped 0..1
            prog = 0.0
            if row["target"] > 0:
                prog = min(max(row["effective_saved"] / row["target"], 0.0), 1.0)
            st.progress(prog)
        with col2:
            st.write(f"{int(prog*100)}%")

    # Pie chart of allocations (including leftover)
    st.subheader("This Paycheck: Allocation Pie")
    allocations = df.set_index("name")["per_paycheck"].to_dict()
    if leftover > 0:
        allocations["Leftover"] = leftover

    if allocations:
        # Remove zero entries to prevent Matplotlib warnings
        allocations_nonzero = {k: float(v) for k, v in allocations.items() if float(v) > 0}
        if allocations_nonzero:
            fig, ax = plt.subplots()
            ax.pie(allocations_nonzero.values(), labels=allocations_nonzero.keys(), autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
            st.pyplot(fig)
        else:
            st.info("No allocations to display (all per-paycheck values are zero).")

    # ----------------------------
    # Persist any final changes before leaving run
    # ----------------------------
    # Write back the user's edited saved_so_far (user may have typed a value) and created/deadline/target edits
    # We use the df values to make sure the JSON is consistent
    # Update st.session_state.expenses from df (preserve keys that might exist in original dicts)
    new_expenses = []
    for i, orig in enumerate(st.session_state.expenses):
        # Build a new dict merging original keys with updated fields from df
        updated = orig.copy()
        row = df.iloc[i]
        updated["name"] = row["name"]
        updated["target"] = float(row["target"])
        updated["deadline"] = row["deadline"]
        updated["created"] = row["created"]
        # save the user's explicit saved_so_far if they typed one; otherwise keep user's stored value if >0 or auto-saved
        # We'll store what we showed as effective_saved so that the JSON reflects user's override or auto-assumption
        updated["saved_so_far"] = float(row["effective_saved"])
        new_expenses.append(updated)

    st.session_state.expenses = new_expenses
    users[current_user]["expenses"] = st.session_state.expenses
    save_users(users)

    st.info("Changes saved automatically. Edit any 'Saved so far' value to override the auto-assumption and the allocations will update immediately.")