from app.database import obtener_conexion


def crear_tabla():

    with obtener_conexion() as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs_seen (
                    job_id VARCHAR(255) PRIMARY KEY,
                    title TEXT NOT NULL,
                    source VARCHAR(100) NOT NULL,
                    url TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

        conexion.commit()

    print("✅ Tabla jobs_seen creada correctamente.")


if __name__ == "__main__":
    crear_tabla()