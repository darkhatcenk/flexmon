"""
FlexMON Online Migrations
Idempotent database migrations that can be run at any time
"""
import psycopg2


def run_online_migrations(conn):
    """
    Run all online migrations in order
    Returns: (success: bool, message: str)
    """
    migrations = [
        _add_user_timestamps,
    ]

    for migration in migrations:
        success, message = migration(conn)
        if not success:
            return False, message

    return True, "All migrations completed successfully"


def _add_user_timestamps(conn):
    """
    Migration 002: Add created_at/updated_at columns to users table
    and create trigger to auto-update updated_at
    """
    cur = conn.cursor()

    try:
        # Add updated_at column if not exists (created_at already exists in schema)
        cur.execute("""
            DO $$
            BEGIN
              -- Add updated_at column if missing
              IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='updated_at'
              ) THEN
                ALTER TABLE users
                  ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();

                -- Backfill existing rows
                UPDATE users SET updated_at = created_at WHERE updated_at IS NULL;

                -- Make it NOT NULL after backfill
                ALTER TABLE users ALTER COLUMN updated_at SET NOT NULL;
              END IF;
            END$$;
        """)

        # Create trigger function for auto-updating updated_at
        cur.execute("""
            DO $$
            BEGIN
              -- Create trigger function if not exists
              IF NOT EXISTS (
                SELECT 1 FROM pg_proc WHERE proname='set_updated_at'
              ) THEN
                CREATE OR REPLACE FUNCTION set_updated_at()
                RETURNS TRIGGER AS $func$
                BEGIN
                  NEW.updated_at = NOW();
                  RETURN NEW;
                END;
                $func$ LANGUAGE plpgsql;
              END IF;
            END$$;
        """)

        # Create trigger if not exists
        cur.execute("""
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM information_schema.triggers
                WHERE event_object_table='users' AND trigger_name='trg_set_updated_at'
              ) THEN
                CREATE TRIGGER trg_set_updated_at
                  BEFORE UPDATE ON users
                  FOR EACH ROW
                  EXECUTE FUNCTION set_updated_at();
              END IF;
            END$$;
        """)

        conn.commit()
        return True, "User timestamps migration completed"

    except psycopg2.Error as e:
        conn.rollback()
        return False, f"User timestamps migration failed: {e}"
    finally:
        cur.close()
