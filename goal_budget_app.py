import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from dateutil.relativedelta import relativedelta

st.title("Biweekly Paycheck Allocator with Editable Goals")

# --- Input paycheck info ---
paycheck = st.number_input("Enter this paycheck amount:", min_value=0.0, step=50.0)
pay_date = st.date_input("Paycheck Date", value=datetime.date.today())

# --- Editable goals ---
st.subheader("Your Goals")
if "goals" not in st.session_state:
    st.session_state.goals = [
        {"name": "Rent", "target": 1200.0, "deadline": datetime.date.today().replace(day=30)},
        {"name": "Utilities", "target": 125.0, "deadline": datetime.date.today().replace(day=30)},
        {"name": "Electric", "target": 50.0, "deadline": datetime.date.today().replace(day=30)},
        {"name": "Internet", "target": 30.0, "deadline": datetime.date.today().replace(day=30)},
        {"name": "Auto Insurance", "target": 500.0, "deadline": datetime.date.today() + relativedelta(months=+6)},
        {"name": "Renters Insurance", "target": 150.0, "deadline": datetime.date.today() + relativedelta(months=+12)},
    ]

# --- Show editable goals ---
for i, goal in enumerate(st.session_state.goals):
    st.write(f"### Goal {i+1}")
    st.session_state.goals[i]["name"] = st.text_input("Category Name", value=goal["name"], key=f"name_{i}")
    st.session_state.goals[i]["target"] = st.number_input(
        "Target Amount",
        min_value=0.0,
        value=float(goal["target"]),
        step=10.0, key=f"target_{i}"
    )
    st.session_state.goals[i]["deadline"] = st.date_input("Deadline", value=goal["deadline"], key=f"deadline_{i}")

# Button to add a new goal
if st.button("Add New Goal"):
    st.session_state.goals.append({"name": "New Goal", "target": 0, "deadline": datetime.date.today()})

# --- Compute allocations ---
df = pd.DataFrame(st.session_state.goals)
df["deadline"] = pd.to_datetime(df["deadline"])
df["days_until_deadline"] = (df["deadline"] - pd.to_datetime(pay_date)).dt.days
days_between_paychecks = 14
df["paychecks_left"] = (df["days_until_deadline"] / days_between_paychecks).apply(lambda x: max(int(x)+1,1))
df["per_paycheck"] = df["target"] / df["paychecks_left"]

total_allocations = df["per_paycheck"].sum()
leftover = max(paycheck - total_allocations, 0)

# --- Display allocations ---
st.subheader("Allocations This Paycheck")
st.dataframe(df[["name","target","deadline","paychecks_left","per_paycheck"]])

st.write(f"**Total Allocations This Paycheck:** ${total_allocations:,.2f}")
st.write(f"**Leftover/Spending Money:** ${leftover:,.2f}")

# --- Pie chart ---
allocations_dict = {row["name"]: row["per_paycheck"] for _, row in df.iterrows()}
allocations_dict["Leftover"] = leftover

fig, ax = plt.subplots()
ax.pie(allocations_dict.values(), labels=allocations_dict.keys(), autopct="%1.1f%%", startangle=90)
ax.axis("equal")
st.pyplot(fig)
