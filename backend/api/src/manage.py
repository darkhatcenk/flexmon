"""
FlexMON Management CLI
Administrative commands for FlexMON backend
"""
import os
import sys
import secrets
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
import psycopg2
from passlib.hash import bcrypt_sha256

from .migrations import run_online_migrations

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


def write_password_to_host(password: str, username: str = "platform_admin"):
    """
    Write admin password to host-mounted file for persistence

    This allows the password to be accessed from the host machine at:
    infra/secrets/platform_admin_pwd.txt
    """
    host_password_file = Path("/app/infra/secrets/platform_admin_pwd.txt")

    try:
        # Create parent directories if they don't exist
        host_password_file.parent.mkdir(parents=True, exist_ok=True)

        # Write just the plain password (no JSON, no extra newlines)
        with open(host_password_file, 'w') as f:
            f.write(password)

        typer.echo(f"✅ Platform admin password also written to {host_password_file}")
        return True

    except (IOError, OSError, PermissionError) as e:
        typer.echo(f"⚠️  Warning: Could not write password to {host_password_file}: {e}", err=True)
        typer.echo(f"   This is non-fatal, but you'll need to retrieve password from container logs or /app/runtime/admin_credentials.json")
        return False


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

            # Write password to host-mounted file for persistence
            write_password_to_host(password, username)
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
def reset_admin(
    username: str = typer.Option("platform_admin", "--username", "-u", help="Admin username"),
    email: Optional[str] = typer.Option("admin@flexmon.local", "--email", "-e", help="Admin email")
):
    """
    Reset/create platform admin with auto-generated secure password

    This command is designed for offline admin recovery and initial setup.
    It generates a strong random password and prints it to stdout.

    IMPORTANT: Only call this via docker exec, NOT via HTTP.
    """
    typer.echo(f"🔐 Resetting platform admin: {username}")

    # Connect to database
    conn = get_db_connection()

    # Run online migrations first to ensure updated_at column exists
    typer.echo("🔧 Running online migrations...")
    success, message = run_online_migrations(conn)
    if not success:
        typer.echo(f"❌ Migration failed: {message}", err=True)
        conn.close()
        raise typer.Exit(code=1)
    typer.echo(f"✅ {message}")

    # Generate strong password (48 chars, URL-safe, no padding)
    # Using 36 random bytes gives us 48 chars of base64url
    password = base64.urlsafe_b64encode(secrets.token_bytes(36)).decode('ascii').rstrip('=')

    # Ensure password is within bcrypt limits (< 72 bytes)
    if len(password) > 64:
        password = password[:64]

    typer.echo(f"   Generated password length: {len(password)} chars")

    # Hash the password with bcrypt_sha256 (no 72-byte limit)
    password_hash = bcrypt_sha256.hash(password)

    cur = conn.cursor()

    try:
        # Upsert the user (updated_at now exists after migration)
        cur.execute("""
            INSERT INTO users (username, email, password_hash, role, tenant_id, enabled, created_at)
            VALUES (%s, %s, %s, 'platform_admin', NULL, TRUE, NOW())
            ON CONFLICT (username) DO UPDATE SET
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                role = 'platform_admin',
                enabled = TRUE,
                updated_at = NOW()
        """, (username, email, password_hash))

        conn.commit()

        # Get user info
        cur.execute("SELECT id, created_at FROM users WHERE username = %s", (username,))
        user = cur.fetchone()

        if user:
            user_id, created_at = user
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

            typer.echo(f"\n✅ Platform admin reset successfully!")
            typer.echo(f"   User ID: {user_id}")
            typer.echo(f"   Username: {username}")
            typer.echo(f"   Email: {email}")
            typer.echo(f"   Role: platform_admin")
            typer.echo(f"   Created: {created_at}")
            typer.echo(f"\n🔑 CREDENTIALS (save these securely):")
            typer.echo(f"   Username: {username}")
            typer.echo(f"   Password: {password}")
            typer.echo(f"\n⚠️  This password will NOT be shown again!")

            # Write credentials to runtime directory (create if not exists)
            runtime_dir = Path("/app/runtime")
            runtime_dir.mkdir(parents=True, exist_ok=True)

            # Write JSON for programmatic access
            creds_file = runtime_dir / "admin_credentials.json"
            creds_data = {
                "username": username,
                "password": password,
                "timestamp": timestamp,
                "user_id": user_id
            }
            with open(creds_file, 'w') as f:
                json.dump(creds_data, f, indent=2)
            typer.echo(f"\n📝 Credentials written to: {creds_file}")

            # Append to info.md for human-readable tracking
            info_file = runtime_dir / "info.md"
            with open(info_file, 'a') as f:
                f.write(f"\n## Admin Reset - {timestamp}\n")
                f.write(f"- Username: `{username}`\n")
                f.write(f"- Password: `{password[:8]}...{password[-8:]}` (masked, see JSON)\n")
                f.write(f"- User ID: {user_id}\n\n")
            typer.echo(f"📝 Info appended to: {info_file}")

            # Write password to host-mounted file for persistence
            write_password_to_host(password, username)
        else:
            typer.echo("⚠️  User created but could not verify", err=True)

    except psycopg2.Error as e:
        conn.rollback()
        typer.echo(f"❌ Failed to reset admin: {e}", err=True)
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

    # Connect to database
    conn = get_db_connection()

    # Run online migrations first to ensure updated_at column exists
    success, message = run_online_migrations(conn)
    if not success:
        typer.echo(f"⚠️  Migration failed: {message}", err=True)
        # Continue anyway for password reset

    # Hash the password with bcrypt_sha256 (no 72-byte limit)
    password_hash = bcrypt_sha256.hash(password)

    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE users
            SET password_hash = %s,
                updated_at = NOW()
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
