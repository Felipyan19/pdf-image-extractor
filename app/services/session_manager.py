"""Session management for temporary image storage with public URLs."""

import threading
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
from dataclasses import dataclass


@dataclass
class SessionData:
    """Data structure for session information."""
    session_id: str
    created_at: datetime
    expires_at: datetime
    output_dir: Path
    pdf_filename: str
    file_count: int = 0


class SessionManager:
    """
    Manages temporary sessions for extracted images.

    Features:
    - Thread-safe session creation and retrieval
    - Automatic expiry tracking
    - Cleanup of expired sessions
    """

    def __init__(self, ttl_hours: int, base_output_dir: Path):
        """
        Initialize session manager.

        Args:
            ttl_hours: Time-to-live for sessions in hours
            base_output_dir: Base directory for all outputs
        """
        self.ttl_hours = ttl_hours
        self.base_output_dir = base_output_dir
        self.sessions_dir = base_output_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Thread-safe session registry
        self._sessions: Dict[str, SessionData] = {}
        self._lock = threading.Lock()

    def create_session(self, pdf_filename: str) -> str:
        """
        Create a new session with unique ID.

        Args:
            pdf_filename: Name of the PDF file being processed

        Returns:
            Session ID (UUID4 hex string without hyphens)
        """
        session_id = uuid4().hex  # 32-character hex string
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=self.ttl_hours)

        # Create session directory
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Create session data
        session_data = SessionData(
            session_id=session_id,
            created_at=created_at,
            expires_at=expires_at,
            output_dir=session_dir,
            pdf_filename=pdf_filename
        )

        # Store in registry (thread-safe)
        with self._lock:
            self._sessions[session_id] = session_data

        return session_id

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Retrieve session data by ID.

        Args:
            session_id: Session ID to look up

        Returns:
            SessionData if found, None otherwise
        """
        with self._lock:
            return self._sessions.get(session_id)

    def get_session_output_dir(self, session_id: str) -> Optional[Path]:
        """
        Get the output directory for a session.

        Args:
            session_id: Session ID

        Returns:
            Path to session output directory, or None if not found
        """
        session = self.get_session(session_id)
        return session.output_dir if session else None

    def is_session_valid(self, session_id: str) -> bool:
        """
        Check if a session exists and has not expired.

        Args:
            session_id: Session ID to check

        Returns:
            True if session exists and is not expired, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False

        return datetime.now() < session.expires_at

    def is_session_expired(self, session_id: str) -> bool:
        """
        Check if a session has expired.

        Args:
            session_id: Session ID to check

        Returns:
            True if session exists and has expired, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False

        return datetime.now() >= session.expires_at

    def get_expired_sessions(self) -> List[str]:
        """
        Get list of expired session IDs.

        Returns:
            List of session IDs that have expired
        """
        now = datetime.now()
        with self._lock:
            return [
                session_id
                for session_id, session_data in self._sessions.items()
                if now >= session_data.expires_at
            ]

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its files.

        Args:
            session_id: Session ID to delete

        Returns:
            True if session was deleted, False if not found
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # Delete session directory and all files
        try:
            if session.output_dir.exists():
                shutil.rmtree(session.output_dir, ignore_errors=True)
        except Exception as e:
            print(f"Warning: Error deleting session directory {session.output_dir}: {e}")

        # Remove from registry
        with self._lock:
            self._sessions.pop(session_id, None)

        return True

    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions and their files.

        Returns:
            Number of sessions cleaned up
        """
        expired_ids = self.get_expired_sessions()
        deleted_count = 0

        for session_id in expired_ids:
            if self.delete_session(session_id):
                deleted_count += 1

        return deleted_count

    def get_active_session_count(self) -> int:
        """
        Get count of active (non-expired) sessions.

        Returns:
            Number of active sessions
        """
        now = datetime.now()
        with self._lock:
            return sum(
                1 for session_data in self._sessions.values()
                if now < session_data.expires_at
            )

    def get_total_session_count(self) -> int:
        """
        Get total count of sessions (including expired).

        Returns:
            Total number of sessions in registry
        """
        with self._lock:
            return len(self._sessions)
