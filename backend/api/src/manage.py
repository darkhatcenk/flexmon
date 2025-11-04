"""
FlexMON Management CLI
Administrative commands for FlexMON backend
"""
import os
import sys
from typing import Optional

import typer
import psycopg2
from passlib.hash import bcrypt_sha256

app = typer.Typer(help="FlexMON Management CLI")


def get_db_connection():
    """Get database connection using environment variables or defaults"""
    # Try to read password from secret file first (Docker secrets)
    db_password = None
    password_file = os.getenv("POSTGRES_PASSWORD_FILE")
    if password_file and os.path.exists(password_file):
        with open(password_file) as f:
            db_password = f.read().strip()

    # Fall back to environment variables
    if not db_password:
        db_password = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD", "postgres")

    host = os.getenv("PGHOST", "timescaledb")
    database = os.getenv("PGDATABASE", "flexmon")
    user = os.getenv("PGUSER", "flexmon")
    port = os.getenv("PGPORT", "5432")

    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=db_password,
            port=port
        )
        return conn
    except psycopg2.Error as e:
        typer.echo(f"❌ Database connection failed: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def create_admin(
    username: str = typer.Option(..., "--username", "-u", help="Admin username"),
    password: str = typer.Option(..., "--password", "-p", help="Admin password"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Admin email (optional)")
):
    """
    Create or update platform admin user

    This command creates a new platform_admin user or updates an existing one.
    Platform admins have full system access and can manage all tenants.
    """
    typer.echo(f"🔧 Creating/updating platform admin user: {username}")

    # Hash the password with bcrypt_sha256 (no 72-byte limit)
    password_hash = bcrypt_sha256.hash(password)

    # Connect to database
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Upsert the user
        cur.execute("""
            INSERT INTO users (username, email, password_hash, role, tenant_id, enabled, created_at)
            VALUES (%s, %s, %s, 'platform_admin', NULL, TRUE, NOW())
            ON CONFLICT (username) DO UPDATE SET
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                role = 'platform_admin',
                enabled = TRUE
        """, (username, email, password_hash))

        conn.commit()

        # Check if it was insert or update
        cur.execute("SELECT id, created_at FROM users WHERE username = %s", (username,))
        user = cur.fetchone()

        if user:
            typer.echo(f"✅ Platform admin '{username}' created/updated successfully (ID: {user[0]})")
            typer.echo(f"   Role: platform_admin")
            typer.echo(f"   Email: {email or 'not set'}")
            typer.echo(f"   Created: {user[1]}")
        else:
            typer.echo("⚠️  User created but could not verify", err=True)

    except psycopg2.Error as e:
        conn.rollback()
        typer.echo(f"❌ Failed to create/update user: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        cur.close()
        conn.close()


@app.command()
def list_users(
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Filter by role"),
    enabled_only: bool = typer.Option(False, "--enabled-only", help="Show only enabled users")
):
    """
    List all users in the system
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = "SELECT id, username, email, role, tenant_id, enabled, created_at FROM users WHERE 1=1"
        params = []

        if role:
            query += " AND role = %s"
            params.append(role)

        if enabled_only:
            query += " AND enabled = TRUE"

        query += " ORDER BY created_at DESC"

        cur.execute(query, params)
        users = cur.fetchall()

        if not users:
            typer.echo("No users found")
            return

        typer.echo(f"\n{'ID':<6} {'Username':<20} {'Email':<30} {'Role':<20} {'Tenant':<20} {'Enabled':<8} {'Created'}")
        typer.echo("=" * 140)

        for user in users:
            user_id, username, email, urole, tenant_id, enabled, created_at = user
            typer.echo(f"{user_id:<6} {username:<20} {email or 'N/A':<30} {urole:<20} {tenant_id or 'N/A':<20} {'✓' if enabled else '✗':<8} {created_at}")

        typer.echo(f"\nTotal users: {len(users)}")

    except psycopg2.Error as e:
        typer.echo(f"❌ Failed to list users: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        cur.close()
        conn.close()


@app.command()
def reset_password(
    username: str = typer.Option(..., "--username", "-u", help="Username"),
    password: str = typer.Option(..., "--password", "-p", help="New password")
):
    """
    Reset user password
    """
    typer.echo(f"🔧 Resetting password for user: {username}")

    # Hash the password with bcrypt_sha256 (no 72-byte limit)
    password_hash = bcrypt_sha256.hash(password)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE users
            SET password_hash = %s
            WHERE username = %s
        """, (password_hash, username))

        if cur.rowcount == 0:
            typer.echo(f"❌ User '{username}' not found", err=True)
            raise typer.Exit(code=1)

        conn.commit()
        typer.echo(f"✅ Password reset successfully for '{username}'")

    except psycopg2.Error as e:
        conn.rollback()
        typer.echo(f"❌ Failed to reset password: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        cur.close()
        conn.close()


@app.command()
def db_info():
    """
    Show database connection information
    """
    password_file = os.getenv("POSTGRES_PASSWORD_FILE")

    typer.echo("📊 Database Connection Info:")
    typer.echo(f"   Host: {os.getenv('PGHOST', 'timescaledb')}")
    typer.echo(f"   Port: {os.getenv('PGPORT', '5432')}")
    typer.echo(f"   Database: {os.getenv('PGDATABASE', 'flexmon')}")
    typer.echo(f"   User: {os.getenv('PGUSER', 'flexmon')}")
    typer.echo(f"   Password from: {'secret file' if password_file else 'environment variable'}")

    # Try to connect
    typer.echo("\n🔌 Testing connection...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        typer.echo(f"✅ Connected successfully!")
        typer.echo(f"   PostgreSQL version: {version[:50]}...")
        cur.close()
        conn.close()
    except Exception as e:
        typer.echo(f"❌ Connection failed: {e}", err=True)


if __name__ == "__main__":
    app()
