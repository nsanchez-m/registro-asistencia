from flask import Flask, render_template, request, redirect, session, send_file, flash
import sqlite3
import pandas as pd
from io import BytesIO
from datetime import date

app = Flask(__name__)
app.secret_key = "clave_secreta_super_segura"

DB_NAME = "asistencia.db"
ADMIN_PASSWORD = "gbufro2026"

# ======================
# BASE DE DATOS
# ======================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actividades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        fecha TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asistencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        apellido TEXT,
        matricula TEXT,
        carrera TEXT,
        correo TEXT,
        actividad_id INTEGER,
        fecha TEXT,
        primera_vez INTEGER,
        UNIQUE(matricula, actividad_id, fecha)
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ======================
# FORMULARIO PRINCIPAL (CORREGIDO: Se añadió la variable 'fecha')
# ======================
@app.route("/", methods=["GET", "POST"])
def index():
    hoy = date.today().isoformat()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, nombre FROM actividades WHERE fecha = ?",
        (hoy,)
    )
    actividades = cursor.fetchall()

    if request.method == "POST":
        datos = (
            request.form["nombre"],
            request.form["apellido"],
            request.form["matricula"],
            request.form["carrera"],
            request.form["correo"],
            request.form["actividad"],
            hoy,
            1 if request.form.get("primera_vez") else 0
        )

        try:
            cursor.execute("""
                INSERT INTO asistencias
                (nombre, apellido, matricula, carrera, correo, actividad_id, fecha, primera_vez)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, datos)
            conn.commit()
            flash("¡Registro exitoso! Gracias por asistir.", "success")

        except sqlite3.IntegrityError:
            conn.close()
            return render_template(
                "index.html",
                actividades=actividades,
                fecha=hoy, # Corrección: pasar fecha aquí también
                error="⚠️ Ya estás registrado(a) en esta actividad hoy."
            )

        conn.close()
        return redirect("/")

    conn.close()
    return render_template("index.html", actividades=actividades, fecha=hoy) # Corrección: pasar fecha

# ======================
# LOGIN ADMIN (CÓDIGO COMPLETO)
# ======================
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        # Verifica si la contraseña escrita en el formulario coincide con "gbufro2026"
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin/panel")
        else:
            error = "Contraseña incorrecta"
    
    # Esto es lo que se muestra cuando entras por primera vez (GET)
    # o cuando la contraseña es incorrecta
    return render_template("admin_login.html", error=error)

# ======================
# PANEL ADMIN (CORREGIDO: Consulta SQL con todos los campos)
# ======================
@app.route("/admin/panel", methods=["GET", "POST"])
def admin_panel():
    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        cursor.execute(
            "INSERT INTO actividades (nombre, fecha) VALUES (?, ?)",
            (request.form["nombre"], request.form["fecha"])
        )
        conn.commit()

    cursor.execute("SELECT * FROM actividades ORDER BY fecha DESC")
    actividades = cursor.fetchall()

    # CORRECCIÓN: La consulta ahora trae los 8 campos necesarios en el orden correcto
    cursor.execute("""
        SELECT a.id, a.fecha, act.nombre AS actividad, a.nombre, a.apellido, 
               a.carrera, a.correo, a.primera_vez
        FROM asistencias a
        JOIN actividades act ON a.actividad_id = act.id
        ORDER BY a.fecha DESC
    """)
    registros = cursor.fetchall()

    conn.close()
    return render_template("admin.html", actividades=actividades, registros=registros)

# ======================
# ELIMINAR REGISTRO (NUEVA RUTA)
# ======================
@app.route("/admin/eliminar_asistencia/<int:id>")
def eliminar_asistencia(id):
    if not session.get("admin"):
        return redirect("/admin")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM asistencias WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/admin/panel")

# ======================
# EXPORTAR EXCEL
# ======================
@app.route("/admin/exportar")
def exportar_excel():
    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("""
        SELECT
            a.matricula AS Matricula,
            a.nombre || ' ' || a.apellido AS Nombre,
            a.correo AS Correo,
            a.carrera AS Carrera,
            a.primera_vez AS PrimeraVez,
            act.nombre || ' (' || act.fecha || ')' AS Actividad,
            'X' AS Asistencia
        FROM asistencias a
        JOIN actividades act ON a.actividad_id = act.id
    """, conn)
    conn.close()

    df["PrimeraVez"] = df["PrimeraVez"].map({1: "Sí", 0: "No"})

    pivot = df.pivot_table(
        index=["Nombre", "Matricula", "Correo", "Carrera", "PrimeraVez"],
        columns="Actividad",
        values="Asistencia",
        aggfunc="first",
        fill_value=""
    )

    pivot["Total asistencias"] = (pivot == "X").sum(axis=1)
    pivot.reset_index(inplace=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pivot.to_excel(writer, index=False)

    output.seek(0)
    return send_file(output, download_name="asistencias_gbu.xlsx", as_attachment=True)

if __name__ == "__main__":
    # Render usa la variable de entorno PORT, si no existe usa el 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)