from pathlib import Path
import sqlite3

from flask import Flask, jsonify, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "hims.db"

app = Flask(__name__, static_folder=None)


def get_connection():
    """Create a read-only SQLite connection."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"HIMS database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_dashboard_data():
    """Build the exact datasets required by dashboard.html."""
    conn = get_connection()

    try:
        # Source used by the notebook:
        # SELECT * FROM patients;
        df_rows = conn.execute("SELECT * FROM patients").fetchall()

        if not df_rows:
            raise ValueError("The patients table is empty.")

        columns = df_rows[0].keys()
        required = {
            "patient_id",
            "age",
            "gender",
            "marital_status",
            "has_insurance",
            "department",
            "preferred_doctor",
        }
        missing = required.difference(columns)

        if missing:
            raise ValueError(
                "Missing required columns in patients table: "
                + ", ".join(sorted(missing))
            )

        rows = [dict(row) for row in df_rows]

        def unique_count(key):
            return len({
                row[key] for row in rows
                if row[key] is not None and str(row[key]).strip() != ""
            })

        ages = [
            float(row["age"])
            for row in rows
            if row["age"] is not None
        ]

        total_patients = unique_count("patient_id")
        average_age = sum(ages) / len(ages) if ages else 0
        minimum_age = min(ages) if ages else 0
        maximum_age = max(ages) if ages else 0

        insured_values = [
            row["has_insurance"]
            for row in rows
            if row["has_insurance"] is not None
        ]
        insured_count = sum(
            1 for value in insured_values
            if str(value).strip().lower() in {
                "yes", "y", "true", "1", "insured"
            }
        )
        insurance_rate = (
            insured_count / len(insured_values) * 100
            if insured_values else 0
        )

        # Patients by gender
        gender_counts = {}
        for row in rows:
            value = row["gender"]
            if value is not None:
                gender_counts[str(value)] = gender_counts.get(str(value), 0) + 1

        gender = [
            {"gender": key, "patients": value}
            for key, value in gender_counts.items()
        ]

        # Gender vs marital status
        gm_counts = {}
        for row in rows:
            gender_value = row["gender"]
            marital_value = row["marital_status"]
            if gender_value is not None and marital_value is not None:
                key = (str(gender_value), str(marital_value))
                gm_counts[key] = gm_counts.get(key, 0) + 1

        gender_marital = [
            {
                "gender": gender_value,
                "marital_status": marital_value,
                "patients": patients,
            }
            for (gender_value, marital_value), patients in gm_counts.items()
        ]

        # Insurance coverage
        insurance_counts = {}
        for row in rows:
            value = row["has_insurance"]
            if value is not None:
                key = str(value)
                insurance_counts[key] = insurance_counts.get(key, 0) + 1

        insurance = [
            {"has_insurance": key, "patients": value}
            for key, value in insurance_counts.items()
        ]

        # Department vs preferred doctor
        doctor_counts = {}
        for row in rows:
            department = row["department"]
            doctor = row["preferred_doctor"]
            if department is not None and doctor is not None:
                key = (str(department), str(doctor))
                doctor_counts[key] = doctor_counts.get(key, 0) + 1

        doctor_department = [
            {
                "department": department,
                "preferred_doctor": doctor,
                "patients": patients,
            }
            for (department, doctor), patients in doctor_counts.items()
        ]

        return {
            "kpis": {
                "total_patients": total_patients,
                "average_age": average_age,
                "minimum_age": minimum_age,
                "maximum_age": maximum_age,
                "insurance_rate": insurance_rate,
                "preferred_doctors": unique_count("preferred_doctor"),
            },
            "gender": gender,
            "gender_marital": gender_marital,
            "insurance": insurance,
            "doctor_department": doctor_department,
        }

    finally:
        conn.close()


@app.get("/")  #homepage
def dashboard():
    # Serve the user's existing HTML file.
    return send_from_directory(BASE_DIR, "dashboard_flask.html")


@app.get("/api/dashboard-data")
def dashboard_data():
    # JSON consumed by the Plotly code already present in dashboard.html.
    try:
        return jsonify(build_dashboard_data())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
