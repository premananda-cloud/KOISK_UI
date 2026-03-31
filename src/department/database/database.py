"""
src/department/database/database.py
====================================
SQLAlchemy engine, session factory, and DB initialisation for KOISK.

Supported backends (set DATABASE_URL in your .env):
──────────────────────────────────────────────────────────────────────────────
  SQLite (default / dev):
      DATABASE_URL=sqlite:///./koisk.db

  PostgreSQL (recommended for production):
      DATABASE_URL=postgresql://user:pass@host:5432/koisk_db

  MySQL / MariaDB:
      DATABASE_URL=mysql+pymysql://user:pass@host:3306/koisk_db
      pip install PyMySQL

  MS SQL Server:
      DATABASE_URL=mssql+pyodbc://user:pass@host/koisk_db?driver=ODBC+Driver+17+for+SQL+Server
      pip install pyodbc

──────────────────────────────────────────────────────────────────────────────
HOW TO SWITCH DATABASE
──────────────────────────────────────────────────────────────────────────────
1. Install the driver for your target database (pip commands above).
2. Set DATABASE_URL in your environment or .env file.
3. That's it — SQLAlchemy handles the rest. All models work unchanged.

Optional tuning env vars:
  DB_POOL_SIZE      — connection pool size          (default: 10, ignored for SQLite)
  DB_MAX_OVERFLOW   — extra connections beyond pool (default: 20, ignored for SQLite)
  SQL_ECHO          — set "true" to log all queries (default: false)

──────────────────────────────────────────────────────────────────────────────
Imported by main.py:
    from src.department.database.database import get_db, init_db
"""

import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# ─── Connection URL ────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./koisk.db")

# ─── Detect backend ───────────────────────────────────────────────────────────

_is_sqlite   = DATABASE_URL.startswith("sqlite")
_is_postgres = "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL
_is_mysql    = "mysql" in DATABASE_URL
_is_mssql    = "mssql" in DATABASE_URL

_echo = os.getenv("SQL_ECHO", "false").lower() == "true"

# ─── Engine configuration ──────────────────────────────────────────────────────

if _is_sqlite:
    # SQLite needs special settings for FastAPI's threaded context.
    # StaticPool is only applied for in-memory databases (:memory:).
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool if ":memory:" in DATABASE_URL else None,
        echo=_echo,
    )

    # Enable WAL mode (better concurrent reads) and foreign key enforcement.
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

elif _is_postgres:
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,   # transparently reconnect on stale connections
        echo=_echo,
    )

elif _is_mysql:
    # PyMySQL driver: pip install PyMySQL
    # For better performance use mysqlclient: pip install mysqlclient
    #   and change URL scheme to mysql+mysqldb://...
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,
        pool_recycle=3600,    # MySQL drops idle connections after ~8h; recycle hourly
        echo=_echo,
    )

elif _is_mssql:
    # Requires pyodbc + the Microsoft ODBC driver installed on the OS.
    # pip install pyodbc
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,
        echo=_echo,
        fast_executemany=True,  # bulk insert performance improvement for pyodbc
    )

else:
    # Generic fallback — works for any SQLAlchemy-supported dialect.
    logger.warning(
        "[DB] Unrecognised DATABASE_URL scheme — using generic engine config. "
        "Pool tuning and dialect-specific options are not applied."
    )
    engine = create_engine(DATABASE_URL, echo=_echo)


# ─── Session factory ──────────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,   # avoids lazy-load errors after commit in FastAPI
)


# ─── FastAPI dependency ───────────────────────────────────────────────────────

def get_db():
    """
    Yields a SQLAlchemy Session for use in FastAPI route handlers.

    Usage:
        @app.get("/...")
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ─── DB initialisation ────────────────────────────────────────────────────────

def init_db() -> None:
    """
    Create all tables and seed a default super-admin if none exists.
    Called once at FastAPI startup via @app.on_event("startup").
    """
    from .models import Base, Admin

    logger.info(f"[DB] Backend : {_backend_label()}")
    logger.info(f"[DB] URL     : {_safe_url(DATABASE_URL)}")
    Base.metadata.create_all(bind=engine)
    logger.info("[DB] Tables created / verified.")

    _seed_default_admin()


def _backend_label() -> str:
    if _is_sqlite:   return "SQLite"
    if _is_postgres: return "PostgreSQL"
    if _is_mysql:    return "MySQL / MariaDB"
    if _is_mssql:    return "MS SQL Server"
    return "Unknown"


def _seed_default_admin() -> None:
    """Insert a default super-admin row on first run (idempotent)."""
    from .models import Admin

    db = SessionLocal()
    try:
        if db.query(Admin).filter(Admin.username == "admin").first():
            return

        default_password = os.getenv("ADMIN_DEFAULT_PASSWORD", "Admin@1234")
        hashed = _hash_password(default_password)

        admin = Admin(
            username        = "admin",
            email           = "admin@koisk.local",
            full_name       = "Super Admin",
            hashed_password = hashed,
            role            = "super_admin",
            department      = None,
            is_active       = True,
        )
        db.add(admin)
        db.commit()
        logger.info(
            "[DB] Default super-admin created  username=admin  "
            "password=(from ADMIN_DEFAULT_PASSWORD env or 'Admin@1234')"
        )
    except Exception as exc:
        db.rollback()
        logger.error(f"[DB] Failed to seed default admin: {exc}")
    finally:
        db.close()


def _hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt (passlib) or SHA-256 fallback."""
    try:
        from passlib.context import CryptContext
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return ctx.hash(plain)
    except ImportError:
        import hashlib
        logger.warning("[DB] passlib not installed — using SHA-256 password hash (dev only)")
        return hashlib.sha256(plain.encode()).hexdigest()


def _safe_url(url: str) -> str:
    """Mask the password in a DB URL for safe logging."""
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":****@")
            return urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        pass
    return url
