"""Tests for the Storage module."""

import os
import tempfile

from wechat_bot.storage import Storage


class TestStorage:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self.storage = Storage(state_dir=self._tmpdir)

    def test_credentials_roundtrip(self):
        self.storage.save_credentials("acct1", "token123", base_url="https://host", user_id="u1")
        creds = self.storage.load_credentials("acct1")
        assert creds["token"] == "token123"
        assert creds["base_url"] == "https://host"
        assert creds["user_id"] == "u1"

    def test_credentials_missing(self):
        creds = self.storage.load_credentials("nonexistent")
        assert creds == {}

    def test_current_user_roundtrip(self):
        self.storage.save_current_user(
            "acct_latest",
            "token_latest",
            base_url="https://host.latest",
            user_id="u_latest",
        )
        current = self.storage.load_current_user()
        assert current["account_id"] == "acct_latest"
        assert current["base_url"] == "https://host.latest"
        assert current["user_id"] == "u_latest"
        assert "token" not in current

    def test_current_user_roundtrip_include_token(self):
        self.storage.save_current_user(
            "acct_latest",
            "token_latest",
            include_token=True,
        )
        current = self.storage.load_current_user()
        assert current["token"] == "token_latest"

    def test_current_user_missing(self):
        assert self.storage.load_current_user() == {}

    def test_sync_buf_roundtrip(self):
        self.storage.save_sync_buf("acct1", "buf_data_abc")
        buf = self.storage.load_sync_buf("acct1")
        assert buf == "buf_data_abc"

    def test_sync_buf_missing(self):
        buf = self.storage.load_sync_buf("nonexistent")
        assert buf == ""

    def test_context_tokens(self):
        self.storage.set_context_token("acct1", "user_a", "ctx_token_1")
        self.storage.set_context_token("acct1", "user_b", "ctx_token_2")

        assert self.storage.get_context_token("acct1", "user_a") == "ctx_token_1"
        assert self.storage.get_context_token("acct1", "user_b") == "ctx_token_2"
        assert self.storage.get_context_token("acct1", "user_c") is None

    def test_context_tokens_persist_and_restore(self):
        self.storage.set_context_token("acct1", "user_x", "tok_x")

        new_storage = Storage(state_dir=self._tmpdir)
        assert new_storage.get_context_token("acct1", "user_x") is None

        count = new_storage.restore_context_tokens("acct1")
        assert count == 1
        assert new_storage.get_context_token("acct1", "user_x") == "tok_x"

    def test_clear_context_tokens(self):
        self.storage.set_context_token("acct1", "user_a", "tok_a")
        self.storage.set_context_token("acct2", "user_b", "tok_b")

        self.storage.clear_context_tokens("acct1")
        assert self.storage.get_context_token("acct1", "user_a") is None
        assert self.storage.get_context_token("acct2", "user_b") == "tok_b"

    def test_list_account_ids(self):
        self.storage.save_credentials("alpha", "t1")
        self.storage.save_credentials("beta", "t2")
        ids = self.storage.list_account_ids()
        assert ids == ["alpha", "beta"]

    def test_list_account_ids_empty(self):
        assert self.storage.list_account_ids() == []

    def test_list_account_ids_by_user_id(self):
        self.storage.save_credentials("alpha", "t1", user_id="u1")
        self.storage.save_credentials("beta", "t2", user_id="u2")
        self.storage.save_credentials("gamma", "t3", user_id="u1")

        assert self.storage.list_account_ids_by_user_id("u1") == ["alpha", "gamma"]
        assert self.storage.list_account_ids_by_user_id("u2") == ["beta"]
        assert self.storage.list_account_ids_by_user_id("missing") == []
        assert self.storage.list_account_ids_by_user_id("") == []

    def test_credentials_saved_with_private_permissions(self):
        if os.name == "nt":
            return

        self.storage.save_credentials("acct1", "token123")
        cred_path = os.path.join(self._tmpdir, "acct1", "credentials.json")
        state_mode = os.stat(self._tmpdir).st_mode & 0o777
        account_mode = os.stat(os.path.dirname(cred_path)).st_mode & 0o777
        file_mode = os.stat(cred_path).st_mode & 0o777

        assert state_mode == 0o700
        assert account_mode == 0o700
        assert file_mode == 0o600
