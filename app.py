from flask import Flask, render_template, request
from datetime import date
import sqlite3

app = Flask(__name__)

def guardar_asistencia(nombre, rut, actividad, fecha):
    conn = sqlite3.connect("asistencia.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            rut TEXT,
            actividad TEXT,
            fecha TEXT
        )
    """)
    cursor.execute(
        "INSERT INTO asistencia (nombre, rut, actividad, fecha) VALUES (?, ?, ?, ?)",
        (nombre, rut, actividad, fecha)
    )
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    hoy = date.today().strftime("%d-%m-%Y")

    if request.method == "POST":
        nombre = request.form["nombre"]
        rut = request.form["rut"]
        actividad = request.form["actividad"]

        guardar_asistencia(nombre, rut, actividad, hoy)

    return render_template("index.html", fecha=hoy)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

