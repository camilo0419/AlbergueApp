
import sqlite3
from pathlib import Path

DB_PATH = Path("albergue.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Tipos de animal
    cur.execute("""
    CREATE TABLE IF NOT EXISTS animal_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL
    )
    """)

    # Animales
    cur.execute("""
    CREATE TABLE IF NOT EXISTS animals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        especie_id INTEGER NOT NULL,
        sexo TEXT,
        edad_meses INTEGER,
        ingreso_fecha TEXT,
        notas TEXT,
        FOREIGN KEY(especie_id) REFERENCES animal_types(id)
    )
    """)

    # Padrinos (Sponsors)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sponsors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT,
        correo TEXT
    )
    """)

    # Donaciones
    cur.execute("""
    CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        sponsor_id INTEGER NOT NULL,
        animal_id INTEGER,
        monto REAL NOT NULL,
        metodo TEXT,
        nota TEXT,
        FOREIGN KEY(sponsor_id) REFERENCES sponsors(id),
        FOREIGN KEY(animal_id) REFERENCES animals(id)
    )
    """)

    # Vacunas
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vaccines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_id INTEGER NOT NULL,
        vacuna TEXT NOT NULL,
        fecha_aplicacion TEXT NOT NULL,
        proxima_fecha TEXT,
        notas TEXT,
        FOREIGN KEY(animal_id) REFERENCES animals(id)
    )
    """)

    # Desparasitaciones
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dewormings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_id INTEGER NOT NULL,
        producto TEXT NOT NULL,
        fecha_aplicacion TEXT NOT NULL,
        proxima_fecha TEXT,
        notas TEXT,
        FOREIGN KEY(animal_id) REFERENCES animals(id)
    )
    """)

    # Adoptantes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS adopters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        documento TEXT,
        telefono TEXT,
        correo TEXT,
        direccion TEXT
    )
    """)

    # Adopciones
    cur.execute("""
    CREATE TABLE IF NOT EXISTS adoptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_id INTEGER NOT NULL,
        adopter_id INTEGER NOT NULL,
        estado TEXT NOT NULL,           -- EN_PROCESO / ADOPTADO / RECHAZADO
        fecha_egreso TEXT,              -- fecha de salida del albergue (si ADOPTADO)
        observaciones TEXT,
        FOREIGN KEY(animal_id) REFERENCES animals(id),
        FOREIGN KEY(adopter_id) REFERENCES adopters(id)
    )
    """)

    conn.commit()
    conn.close()
