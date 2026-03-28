"""Persistent storage for context tokens, sync cursors, and credentials."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from threading import Lock

from ._logging import logger

__all__ = ["Storage"]

_DEFAULT_STATE_DIR = os.path.join(os.path.expanduser("~"), ".wechat_bot")
_PRIVATE_DIR_MODE = 0o700
_PRIVATE_FILE_MODE = 0o600


class Storage:
    """Thread-safe, file-backed storage for bot state.

    Data is kept in an in-memory dict and flushed to a JSON file on every
    write so it survives restarts.

    Directory layout::

        {state_dir}/
        ├── current_user.json            # {"account_id": ..., "base_url": ...}
        ├── {account_id}/
        │   ├── credentials.json      # {"token": ..., "base_url": ...}
        │   ├── sync.json             # {"get_updates_buf": "..."}
        │   └── context_tokens.json   # {"user_id": "token", ...}
    """

    def __init__(self, state_dir: str | None = None) -> None:
        self._state_dir = state_dir or _DEFAULT_STATE_DIR
        self._lock = Lock()
        self._context_tokens: dict[str, str] = {}
        self._ensure_private_dir(self._state_dir)

    @property
    def state_dir(self) -> str:
        return self._state_dir

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _account_dir(self, account_id: str) -> str:
        d = os.path.join(self._state_dir, account_id)
        os.makedirs(d, exist_ok=True)
        return d

    def _credentials_path(self, account_id: str) -> str:
        return os.path.join(self._account_dir(account_id), "credentials.json")

    def _sync_path(self, account_id: str) -> str:
        return os.path.join(self._account_dir(account_id), "sync.json")

    def _context_tokens_path(self, account_id: str) -> str:
        return os.path.join(self._account_dir(account_id), "context_tokens.json")

    def _current_user_path(self) -> str:
        return os.path.join(self._state_dir, "current_user.json")

    # ------------------------------------------------------------------
    # Generic JSON helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _set_private_mode(path: str, mode: int) -> None:
        if os.name == "nt":
            return
        with contextlib.suppress(OSError):
            os.chmod(path, mode)

    @classmethod
    def _ensure_private_dir(cls, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        cls._set_private_mode(path, _PRIVATE_DIR_MODE)

    @staticmethod
    def _read_json(path: str) -> dict[str, object]:
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
                if not isinstance(raw, dict):
                    return {}
                data: dict[str, object] = raw
                return data
        except FileNotFoundError:
            return {}
        except (json.JSONDecodeError, PermissionError, OSError):
            logger.warning("Failed to read state file %s, using empty state", path)
            return {}

    @classmethod
    def _write_json(cls, path: str, data: dict[str, object]) -> None:
        directory = os.path.dirname(path)
        cls._ensure_private_dir(directory)

        fd, tmp_path = tempfile.mkstemp(
            dir=directory,
            prefix=".tmp_state_",
            suffix=".json",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            cls._set_private_mode(tmp_path, _PRIVATE_FILE_MODE)
            os.replace(tmp_path, path)
            cls._set_private_mode(path, _PRIVATE_FILE_MODE)
        except Exception:
            with contextlib.suppress(FileNotFoundError):
                os.remove(tmp_path)
            raise

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    def save_credentials(
        self,
        account_id: str,
        token: str,
        base_url: str | None = None,
        user_id: str | None = None,
    ) -> None:
        data: dict[str, object] = {"token": token}
        if base_url:
            data["base_url"] = base_url
        if user_id:
            data["user_id"] = user_id
        self._write_json(self._credentials_path(account_id), data)
        logger.info("Saved credentials for account %s", account_id)

    def load_credentials(self, account_id: str) -> dict[str, str]:
        raw = self._read_json(self._credentials_path(account_id))
        return {k: str(v) for k, v in raw.items() if isinstance(v, str)}

    def save_current_user(
        self,
        account_id: str,
        token: str | None = None,
        base_url: str | None = None,
        user_id: str | None = None,
        include_token: bool = False,
    ) -> None:
        """Save the latest successfully logged-in account globally.

        By default only account metadata is saved.
        Pass ``include_token=True`` to persist token in ``current_user.json``.
        """
        data: dict[str, object] = {"account_id": account_id}
        if include_token and token:
            data["token"] = token
        if base_url:
            data["base_url"] = base_url
        if user_id:
            data["user_id"] = user_id
        self._write_json(self._current_user_path(), data)
        logger.info("Updated current user to account %s", account_id)

    def load_current_user(self) -> dict[str, str]:
        """Load latest account metadata from ``current_user.json``.

        Notes:
            Legacy files may still include a ``token`` field.
        """
        raw = self._read_json(self._current_user_path())
        return {k: str(v) for k, v in raw.items() if isinstance(v, str)}

    # ------------------------------------------------------------------
    # Sync cursor (get_updates_buf)
    # ------------------------------------------------------------------

    def save_sync_buf(self, account_id: str, buf: str) -> None:
        self._write_json(self._sync_path(account_id), {"get_updates_buf": buf})

    def load_sync_buf(self, account_id: str) -> str:
        data = self._read_json(self._sync_path(account_id))
        return str(data.get("get_updates_buf", ""))

    # ------------------------------------------------------------------
    # Context tokens  (account_id:user_id → token)
    # ------------------------------------------------------------------

    @staticmethod
    def _ctx_key(account_id: str, user_id: str) -> str:
        return f"{account_id}:{user_id}"

    def set_context_token(self, account_id: str, user_id: str, token: str) -> None:
        with self._lock:
            self._context_tokens[self._ctx_key(account_id, user_id)] = token
            self._persist_context_tokens(account_id)

    def get_context_token(self, account_id: str, user_id: str) -> str | None:
        with self._lock:
            return self._context_tokens.get(self._ctx_key(account_id, user_id))

    def restore_context_tokens(self, account_id: str) -> int:
        """Load context tokens from disk into memory. Returns count restored."""
        path = self._context_tokens_path(account_id)
        data = self._read_json(path)
        count = 0
        with self._lock:
            for uid, tok in data.items():
                if isinstance(tok, str) and tok:
                    self._context_tokens[self._ctx_key(account_id, uid)] = tok
                    count += 1
        logger.info("Restored %d context tokens for account %s", count, account_id)
        return count

    def clear_context_tokens(self, account_id: str) -> None:
        prefix = f"{account_id}:"
        with self._lock:
            keys = [k for k in self._context_tokens if k.startswith(prefix)]
            for k in keys:
                del self._context_tokens[k]
        path = self._context_tokens_path(account_id)
        with contextlib.suppress(FileNotFoundError):
            os.remove(path)

    def _persist_context_tokens(self, account_id: str) -> None:
        prefix = f"{account_id}:"
        tokens: dict[str, object] = {}
        for k, v in self._context_tokens.items():
            if k.startswith(prefix):
                tokens[k[len(prefix) :]] = v
        path = self._context_tokens_path(account_id)
        self._write_json(path, tokens)

    # ------------------------------------------------------------------
    # Account listing
    # ------------------------------------------------------------------

    def list_account_ids(self) -> list[str]:
        """Return account IDs that have stored credentials."""
        if not os.path.isdir(self._state_dir):
            return []
        result: list[str] = []
        for name in os.listdir(self._state_dir):
            cred = os.path.join(self._state_dir, name, "credentials.json")
            if os.path.isfile(cred):
                result.append(name)
        return sorted(result)

    def list_account_ids_by_user_id(self, user_id: str) -> list[str]:
        """Return account IDs whose credentials belong to ``user_id``."""
        wanted = user_id.strip()
        if not wanted:
            return []
        matched: list[str] = []
        for account_id in self.list_account_ids():
            creds = self.load_credentials(account_id)
            if creds.get("user_id", "").strip() == wanted:
                matched.append(account_id)
        return sorted(matched)
