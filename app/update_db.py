from app.database import obtener_conexion


def actualizar_tabla():

    with obtener_conexion() as conexion:

        with conexion.cursor() as cursor:

            cursor.execute("""
                ALTER TABLE jobs_seen
                ADD COLUMN IF NOT EXISTS status VARCHAR(30)
                DEFAULT 'pending';
            """)

            cursor.execute("""
                ALTER TABLE jobs_seen ADD COLUMN IF NOT EXISTS company TEXT;
                ALTER TABLE jobs_seen ADD COLUMN IF NOT EXISTS location TEXT;
                ALTER TABLE jobs_seen ADD COLUMN IF NOT EXISTS description TEXT;
                ALTER TABLE jobs_seen ADD COLUMN IF NOT EXISTS salary_min INTEGER;
                ALTER TABLE jobs_seen ADD COLUMN IF NOT EXISTS salary_max INTEGER;
                ALTER TABLE jobs_seen ADD COLUMN IF NOT EXISTS remote BOOLEAN DEFAULT FALSE;
                ALTER TABLE jobs_seen ADD COLUMN IF NOT EXISTS filter_score INTEGER;
                ALTER TABLE jobs_seen ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(64);
                ALTER TABLE jobs_seen ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                ALTER TABLE jobs_seen ADD COLUMN IF NOT EXISTS analyzing_at TIMESTAMP;
            """)

            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS jobs_seen_dedupe_key_unique
                ON jobs_seen (dedupe_key)
                WHERE dedupe_key IS NOT NULL;
            """)

            cursor.execute("""
                ALTER TABLE jobs_seen
                ADD COLUMN IF NOT EXISTS match_score INTEGER;
            """)

            cursor.execute("""
                ALTER TABLE jobs_seen
                ADD COLUMN IF NOT EXISTS ai_summary TEXT;
            """)

            cursor.execute("""
                ALTER TABLE jobs_seen
                ADD COLUMN IF NOT EXISTS ai_strengths TEXT;
            """)

            cursor.execute("""
                ALTER TABLE jobs_seen
                ADD COLUMN IF NOT EXISTS ai_missing TEXT;
            """)

            cursor.execute("""
                ALTER TABLE jobs_seen
                ADD COLUMN IF NOT EXISTS ai_reason TEXT;
            """)

            cursor.execute("""
                ALTER TABLE jobs_seen
                ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMP;
            """)

            cursor.execute("""
                ALTER TABLE jobs_seen
                ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP;
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id BIGSERIAL PRIMARY KEY,
                    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    status VARCHAR(20) NOT NULL DEFAULT 'running',
                    found_count INTEGER NOT NULL DEFAULT 0,
                    filtered_count INTEGER NOT NULL DEFAULT 0,
                    analyzed_count INTEGER NOT NULL DEFAULT 0,
                    notified_count INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    current_step VARCHAR(30) NOT NULL DEFAULT 'starting',
                    phase_message TEXT,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                ALTER TABLE pipeline_runs
                ADD COLUMN IF NOT EXISTS current_step VARCHAR(30) NOT NULL DEFAULT 'starting';
                ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS phase_message TEXT;
                ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)

        conexion.commit()

    print("✅ Tabla jobs_seen actualizada correctamente.")


if __name__ == "__main__":
    actualizar_tabla()
