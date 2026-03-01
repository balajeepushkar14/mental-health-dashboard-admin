import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
import numpy as np

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(
    page_title="Mental Health Assessment System",
    page_icon="🧠",
    layout="wide"
)

# =============================
# DATABASE SETUP
# =============================
conn = sqlite3.connect("mental_health.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    date TEXT,
    phq9 INTEGER,
    gad7 INTEGER,
    risk TEXT
)
""")
conn.commit()

# Create default admin
try:
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
              ("admin", "admin123", "admin"))
    conn.commit()
except:
    pass

# =============================
# ML MODEL
# =============================
def train_model():
    X = np.array([[5,4],[10,8],[15,12],[20,18],[2,1]])
    y = np.array([0,1,1,1,0])
    model = LogisticRegression()
    model.fit(X,y)
    return model

model = train_model()

# =============================
# SESSION STATE
# =============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

# =============================
# LOGIN / REGISTER
# =============================
if not st.session_state.logged_in:

    st.title("🧠 Mental Health Assessment System")

    menu = st.radio("Select Option", ["Login", "Register"], key="auth_menu")

    if menu == "Register":
        st.subheader("Create Account")
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")

        if st.button("Register"):
            try:
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                          (new_user, new_pass, "user"))
                conn.commit()
                st.success("Registration Successful! Please login.")
            except:
                st.error("Username already exists.")

    if menu == "Login":
        st.subheader("Login")
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")

        if st.button("Login"):
            c.execute("SELECT role FROM users WHERE username=? AND password=?",
                      (user, pwd))
            result = c.fetchone()

            if result:
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.role = result[0]
                st.success("Login Successful!")
                st.rerun()
            else:
                st.error("Invalid Credentials")

    st.stop()

# =============================
# SIDEBAR
# =============================
st.sidebar.title(f"Welcome, {st.session_state.username}")

if st.session_state.role == "admin":
    page = st.sidebar.radio("Navigation",
                            ["Admin Dashboard", "All Assessments"],
                            key="admin_nav")
else:
    page = st.sidebar.radio("Navigation",
                            ["Take Assessment", "My History"],
                            key="user_nav")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# =============================
# USER SECTION
# =============================
if st.session_state.role == "user":

    if page == "Take Assessment":

        st.title("📝 Mental Health Assessment")
        st.markdown("Please answer all questions honestly.")

        PHQ9 = [
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
            "Trouble falling or staying asleep",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            "Feeling bad about yourself",
            "Trouble concentrating",
            "Moving or speaking slowly / Restless",
            "Thoughts of self-harm"
        ]

        GAD7 = [
            "Feeling nervous or anxious",
            "Unable to stop worrying",
            "Worrying too much",
            "Trouble relaxing",
            "Being so restless it’s hard to sit still",
            "Becoming easily annoyed",
            "Feeling afraid something awful might happen"
        ]

        OPTIONS = ["0", "1", "2", "3"]
        scores = []

        # -----------------------------
        # PHQ-9 Section
        # -----------------------------
        st.subheader("📘 PHQ-9 (Depression Scale)")
        for i, q in enumerate(PHQ9):
            answer = st.radio(
                q,
                OPTIONS,
                horizontal=True,
                key=f"phq9_{i}"
            )
            scores.append(int(answer))

        st.divider()

        # -----------------------------
        # GAD-7 Section
        # -----------------------------
        st.subheader("📙 GAD-7 (Anxiety Scale)")
        for i, q in enumerate(GAD7):
            answer = st.radio(
                q,
                OPTIONS,
                horizontal=True,
                key=f"gad7_{i}"
            )
            scores.append(int(answer))

        st.divider()

        # -----------------------------
        # SUBMIT
        # -----------------------------
        if st.button("Submit Assessment"):

            phq_score = sum(scores[:len(PHQ9)])
            gad_score = sum(scores[len(PHQ9):])

            prediction = model.predict([[phq_score, gad_score]])[0]
            risk = "High" if prediction == 1 else "Low"

            st.success(f"PHQ-9 Score: {phq_score}")
            st.success(f"GAD-7 Score: {gad_score}")

            if risk == "High":
                st.error(f"⚠ Risk Level: {risk}")
            else:
                st.success(f"✅ Risk Level: {risk}")

            c.execute("""
                INSERT INTO assessments
                (username, date, phq9, gad7, risk)
                VALUES (?, ?, ?, ?, ?)
            """, (st.session_state.username,
                  str(datetime.now()),
                  phq_score, gad_score, risk))
            conn.commit()

    # -----------------------------
    # HISTORY PAGE
    # -----------------------------
    if page == "My History":

        st.title("📊 My Assessment History")

        df = pd.read_sql_query(
            "SELECT date, phq9, gad7, risk FROM assessments WHERE username=?",
            conn, params=(st.session_state.username,)
        )

        if not df.empty:
            st.dataframe(df)

            fig, ax = plt.subplots()
            ax.plot(df["phq9"], label="PHQ-9")
            ax.plot(df["gad7"], label="GAD-7")
            ax.legend()
            st.pyplot(fig)
        else:
            st.info("No assessments yet.")

# =============================
# ADMIN SECTION
# =============================
if st.session_state.role == "admin":

    if page == "Admin Dashboard":

        st.title("👨‍💼 Admin Dashboard")
        users = pd.read_sql_query("SELECT username, role FROM users", conn)
        st.dataframe(users)

    if page == "All Assessments":

        st.title("📋 All User Assessments")

        df = pd.read_sql_query(
            "SELECT username, date, phq9, gad7, risk FROM assessments",
            conn)

        if not df.empty:
            st.dataframe(df)

            fig, ax = plt.subplots()
            ax.hist(df["phq9"], alpha=0.5, label="PHQ-9")
            ax.hist(df["gad7"], alpha=0.5, label="GAD-7")
            ax.legend()
            st.pyplot(fig)
        else:
            st.info("No data available.")