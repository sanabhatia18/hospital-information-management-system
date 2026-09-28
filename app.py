from flask import Flask, render_template, request, jsonify
import sqlite3
import re
import uuid
from datetime import datetime

app = Flask(__name__)

# ==================================================
# QUESTIONS
# ==================================================

QUESTIONS = [
    {"field": "fullname", "question": "Enter Full Name"},
    {"field": "dob", "question": "Enter Date of Birth (YYYY-MM-DD)"},
    {"field": "age", "question": "Enter Age"},
    {"field": "gender", "question": "Enter Gender (Male/Female/Other)"},
    {"field": "marital_status", "question": "Enter Marital Status"},
    {"field": "mobile", "question": "Enter Mobile Number"},
    {"field": "email", "question": "Enter Email Address"},
    {"field": "aadhaar", "question": "Enter Aadhaar Number"},
    {"field": "address", "question": "Enter House No / Street"},
    {"field": "area", "question": "Enter Area / Locality"},
    {"field": "city", "question": "Enter City"},
    {"field": "state", "question": "Enter State"},
    {"field": "pincode", "question": "Enter Pincode"},
    {"field": "blood_group", "question": "Enter Blood Group"},
    {"field": "emergency_name", "question": "Emergency Contact Name"},
    {"field": "emergency_number", "question": "Emergency Contact Number"},
    {"field": "symptoms", "question": "Describe Symptoms"},
    {"field": "symptom_duration", "question": "How long have symptoms existed?"},
    {"field": "current_condition", "question": "Current Medical Condition"},
    {"field": "allergies", "question": "Any Allergies?"},
    {"field": "previous_surgery", "question": "Any Previous Surgery?"},
    {"field": "family_history", "question": "Family Medical History (Optional)"},
    {"field": "has_insurance", "question": "Do you have Health Insurance? (Yes/No)"},
    {"field": "insurance_provider", "question": "Insurance Provider Name"},
    {"field": "policy_number", "question": "Policy Number"},
    {"field": "insurance_validity", "question": "Policy Expiry Date (YYYY-MM-DD)"},
    {"field": "department", "question": "Preferred Department"},
    {"field": "preferred_doctor", "question": "Preferred Doctor"},
    {"field": "appointment_date", "question": "Appointment Date (YYYY-MM-DD)"},
    {"field": "appointment_time", "question": "Appointment Time (HH:MM)"}
]

patient_sessions = {}

# ==================================================
# DATABASE
# ==================================================

def init_db():

    conn = sqlite3.connect("hims.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients(
        patient_id TEXT PRIMARY KEY,
        fullname TEXT,
        dob TEXT,
        age INTEGER,
        gender TEXT,
        marital_status TEXT,
        mobile TEXT,
        email TEXT,
        aadhaar TEXT,
        address TEXT,
        area TEXT,
        city TEXT,
        state TEXT,
        pincode TEXT,
        blood_group TEXT,
        emergency_name TEXT,
        emergency_number TEXT,
        symptoms TEXT,
        symptom_duration TEXT,
        current_condition TEXT,
        allergies TEXT,
        previous_surgery TEXT,
        family_history TEXT,
        has_insurance TEXT,
        insurance_provider TEXT,
        policy_number TEXT,
        insurance_validity TEXT,
        department TEXT,
        preferred_doctor TEXT,
        appointment_date TEXT,
        appointment_time TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()

# ==================================================
# VALIDATION
# ==================================================

def validate(field, value):

    if field == "fullname":
        return bool(re.match(r'^[A-Za-z ]+$', value))

    elif field == "age":
        return value.isdigit() and 1 <= int(value) <= 120

    elif field == "mobile":
        return bool(re.match(r'^[6-9]\d{9}$', value))

    elif field == "email":
        return bool(re.match(
            r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$',
            value
        ))

    elif field == "aadhaar":
        return bool(re.match(r'^\d{12}$', value))

    elif field == "pincode":
        return bool(re.match(r'^\d{6}$', value))

    elif field == "blood_group":
        return value.upper() in [
            "A+","A-","B+","B-",
            "AB+","AB-","O+","O-"
        ]

    elif field == "emergency_number":
        return bool(re.match(r'^[6-9]\d{9}$', value))

    return True

# ==================================================
# DEPARTMENT ASSIGNMENT
# ==================================================

def assign_department(symptoms):

    symptoms = symptoms.lower()

    if "chest" in symptoms or "heart" in symptoms:
        return "Cardiology"

    elif "bone" in symptoms or "fracture" in symptoms:
        return "Orthopedics"

    elif "skin" in symptoms:
        return "Dermatology"

    elif "eye" in symptoms:
        return "Ophthalmology"

    elif "brain" in symptoms or "headache" in symptoms:
        return "Neurology"

    return "General Medicine"

# ==================================================
# ROUTES
# ==================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/start")
def start_chat():

    session_id = str(uuid.uuid4())

    patient_sessions[session_id] = {
        "step": 0,
        "data": {}
    }

    return jsonify({
        "session_id": session_id,
        "question": QUESTIONS[0]["question"]
    })


@app.route("/chat", methods=["POST"])
def chat():

    req = request.get_json()

    session_id = req.get("session_id")
    answer = req.get("answer", "").strip()

    if session_id not in patient_sessions:
        return jsonify({
            "success": False,
            "message": "Session expired. Please restart registration."
        })

    session = patient_sessions[session_id]

    step = session["step"]

    field = QUESTIONS[step]["field"]

    if not validate(field, answer):
        return jsonify({
            "success": False,
            "message": f"Invalid {field}. Please enter valid data."
        })

    session["data"][field] = answer

    # ===================================
    # INSURANCE SKIP
    # ===================================

    if field == "has_insurance" and answer.lower() == "no":

        session["data"]["insurance_provider"] = ""
        session["data"]["policy_number"] = ""
        session["data"]["insurance_validity"] = ""

        step += 4
        session["step"] = step

        return jsonify({
            "success": True,
            "completed": False,
            "question": QUESTIONS[step]["question"],
            "summary": session["data"]
        })

    step += 1
    session["step"] = step

    # ===================================
    # NEXT QUESTION
    # ===================================

    if step < len(QUESTIONS):

        return jsonify({
            "success": True,
            "completed": False,
            "question": QUESTIONS[step]["question"],
            "summary": session["data"]
        })

    # ===================================
    # FINAL SAVE
    # ===================================

    patient_id = "PAT" + datetime.now().strftime("%Y%m%d%H%M%S")

    auto_department = assign_department(
        session["data"].get("symptoms", "")
    )

    department = session["data"].get(
        "department",
        auto_department
    )

    try:

        conn = sqlite3.connect("hims.db")
        cur = conn.cursor()

        values = (
            patient_id,
            session["data"].get("fullname"),
            session["data"].get("dob"),
            session["data"].get("age"),
            session["data"].get("gender"),
            session["data"].get("marital_status"),
            session["data"].get("mobile"),
            session["data"].get("email"),
            session["data"].get("aadhaar"),
            session["data"].get("address"),
            session["data"].get("area"),
            session["data"].get("city"),
            session["data"].get("state"),
            session["data"].get("pincode"),
            session["data"].get("blood_group"),
            session["data"].get("emergency_name"),
            session["data"].get("emergency_number"),
            session["data"].get("symptoms"),
            session["data"].get("symptom_duration"),
            session["data"].get("current_condition"),
            session["data"].get("allergies"),
            session["data"].get("previous_surgery"),
            session["data"].get("family_history"),
            session["data"].get("has_insurance"),
            session["data"].get("insurance_provider"),
            session["data"].get("policy_number"),
            session["data"].get("insurance_validity"),
            department,
            session["data"].get("preferred_doctor"),
            session["data"].get("appointment_date"),
            session["data"].get("appointment_time"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        cur.execute("""
        INSERT INTO patients VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, values)

        conn.commit()

        print("PATIENT SAVED SUCCESSFULLY")

    except Exception as e:

        print("DATABASE ERROR:", str(e))

        return jsonify({
            "success": False,
            "message": str(e)
        })

    finally:

        conn.close()

    summary = session["data"].copy()

    summary["patient_id"] = patient_id
    summary["assign_department"] = auto_department

    del patient_sessions[session_id]

    return jsonify({
        "success": True,
        "completed": True,
        "summary": summary })


@app.route("/patients")
def patients():

    conn = sqlite3.connect("hims.db")
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    cur.execute("""
    SELECT *
    FROM patients
    ORDER BY created_at DESC
    """)

    rows = [dict(row) for row in cur.fetchall()]

    conn.close()

    return jsonify(rows)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)