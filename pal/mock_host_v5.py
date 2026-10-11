"""Lifetime POSIX guard for a canonical v5 mock SQLite database."""

import contextlib
import os
import sqlite3
import stat
import threading
import uuid

try:
    import fcntl
except ImportError:
    fcntl = None

_SIDECAR_SUFFIX = ".pal-v5.lock"
_REGISTRY = {}
_REGISTRY_LOCK = threading.Lock()
_LIVE_PHASES = frozenset(("owned", "startup", "ready"))


def _regular_single(info):
    return stat.S_ISREG(info.st_mode) and info.st_nlink == 1


def _open_flags():
    if fcntl is None or not hasattr(fcntl, "flock"):
        raise RuntimeError("POSIX flock is unavailable")
    try:
        return os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC
    except AttributeError as exc:
        raise RuntimeError("required POSIX open flags are unavailable") from exc


def _release_failed_lock(fd, locked):
    try:
        try:
            if locked:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
    except BaseException:
        pass


class MockHostSession:
    __slots__ = (
        "_canon",
        "_sidecar",
        "_fd",
        "_pid",
        "_sidecar_dev",
        "_sidecar_ino",
        "_db_dev",
        "_db_ino",
        "_session_id",
        "_runner_id",
        "_phase",
        "_db_uuid",
        "_orphan_lease_id",
        "_permits",
    )

    @classmethod
    def open(cls, database_path):
        if not isinstance(database_path, (str, os.PathLike)):
            raise ValueError("database path must be str or PathLike")
        try:
            supplied = os.fspath(database_path)
        except TypeError as exc:
            raise ValueError("database path must be str or PathLike") from exc
        if (
            not isinstance(supplied, str)
            or supplied == ""
            or supplied == ":memory:"
            or supplied.startswith("file:")
            or "\x00" in supplied
        ):
            raise ValueError("unsupported database path")

        canon = os.path.realpath(supplied)
        with _REGISTRY_LOCK:
            if canon in _REGISTRY:
                raise RuntimeError("database is already guarded")

            flags = _open_flags()
            sidecar = canon + _SIDECAR_SUFFIX
            lock_fd = os.open(sidecar, flags, 0o600)
            locked = False
            try:
                try:
                    sidecar_info = os.fstat(lock_fd)
                except OSError as exc:
                    raise RuntimeError("cannot inspect lock sidecar") from exc
                if not _regular_single(sidecar_info):
                    raise RuntimeError("invalid lock sidecar")

                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    raise RuntimeError("database lifetime is already owned") from exc
                locked = True

                db_fd = os.open(canon, flags, 0o600)
                try:
                    db_info = os.fstat(db_fd)
                finally:
                    os.close(db_fd)
                if not _regular_single(db_info):
                    raise RuntimeError("invalid database file")

                guard = cls.__new__(cls)
                guard._canon = canon
                guard._sidecar = sidecar
                guard._fd = lock_fd
                guard._pid = os.getpid()
                guard._sidecar_dev = sidecar_info.st_dev
                guard._sidecar_ino = sidecar_info.st_ino
                guard._db_dev = db_info.st_dev
                guard._db_ino = db_info.st_ino
                guard._session_id = str(uuid.uuid4())
                guard._runner_id = str(uuid.uuid4())
                guard._phase = "owned"
                guard._db_uuid = None
                guard._orphan_lease_id = None
                guard._permits = 0
                _REGISTRY[canon] = guard
            except BaseException:
                _release_failed_lock(lock_fd, locked)
                raise
            return guard

    @property
    def database_path(self):
        return self._canon

    @property
    def session_id(self):
        return self._session_id

    @property
    def runner_id(self):
        return self._runner_id

    @property
    def phase(self):
        return self._phase

    @property
    def db_uuid(self):
        return self._db_uuid

    @property
    def orphan_lease_id(self):
        return self._orphan_lease_id

    def _check_valid(self, ready):
        canon = getattr(self, "_canon", None)
        if not isinstance(canon, str) or _REGISTRY.get(canon) is not self:
            raise RuntimeError("guard is not registered")
        if getattr(self, "_pid", None) != os.getpid():
            raise RuntimeError("guard belongs to another process")

        phase = getattr(self, "_phase", None)
        if phase not in _LIVE_PHASES:
            raise RuntimeError("guard is closed")
        if ready and phase != "ready":
            raise RuntimeError("guard is not ready")

        fd = getattr(self, "_fd", None)
        sidecar = getattr(self, "_sidecar", None)
        if not isinstance(fd, int) or fd < 0 or not isinstance(sidecar, str):
            raise RuntimeError("guard descriptor is invalid")

        try:
            fd_info = os.fstat(fd)
            sidecar_info = os.lstat(sidecar)
            db_info = os.stat(canon)
        except OSError as exc:
            raise RuntimeError("guarded files are unavailable") from exc

        sidecar_identity = (
            getattr(self, "_sidecar_dev", None),
            getattr(self, "_sidecar_ino", None),
        )
        db_identity = (
            getattr(self, "_db_dev", None),
            getattr(self, "_db_ino", None),
        )
        if (
            not _regular_single(fd_info)
            or not _regular_single(sidecar_info)
            or not _regular_single(db_info)
            or (fd_info.st_dev, fd_info.st_ino) != sidecar_identity
            or (sidecar_info.st_dev, sidecar_info.st_ino) != sidecar_identity
            or (db_info.st_dev, db_info.st_ino) != db_identity
        ):
            raise RuntimeError("guarded file identity changed")

    def _valid(self, ready=False):
        with _REGISTRY_LOCK:
            self._check_valid(ready)

    def check_connection(self, connection, ready=False):
        self._valid(ready)
        if not isinstance(connection, sqlite3.Connection):
            raise RuntimeError("connection must be sqlite3.Connection")

        try:
            rows = connection.execute("PRAGMA database_list").fetchall()
        except sqlite3.Error as exc:
            raise RuntimeError("cannot inspect connection databases") from exc

        main = None
        for row in rows:
            if len(row) >= 3 and row[1] == "main":
                main = row[2]
                break
        if not isinstance(main, str) or main == "" or "\x00" in main:
            raise RuntimeError("connection has no file-backed main database")

        try:
            actual = os.path.realpath(main)
            if actual != self._canon:
                raise RuntimeError("connection main database does not match guard")
            info = os.stat(actual)
        except OSError as exc:
            raise RuntimeError("cannot inspect connection database") from exc
        if (info.st_dev, info.st_ino) != (self._db_dev, self._db_ino):
            raise RuntimeError("connection database identity does not match guard")

    def mark_registered(self, db_uuid, orphan_lease_id=None):
        if not isinstance(db_uuid, str) or db_uuid == "":
            raise RuntimeError("db_uuid must be a nonempty string")
        if orphan_lease_id is not None and (
            not isinstance(orphan_lease_id, str) or orphan_lease_id == ""
        ):
            raise RuntimeError("orphan_lease_id must be None or a nonempty string")

        with _REGISTRY_LOCK:
            self._check_valid(False)
            if self._phase == "owned":
                self._db_uuid = db_uuid
                self._orphan_lease_id = orphan_lease_id
                self._phase = "startup"
                return
            if (
                self._phase in ("startup", "ready")
                and self._db_uuid == db_uuid
                and self._orphan_lease_id == orphan_lease_id
            ):
                return
            raise RuntimeError("conflicting registration")

    def activate(self):
        with _REGISTRY_LOCK:
            self._check_valid(False)
            if self._phase != "startup":
                raise RuntimeError("guard is not in startup phase")
            self._phase = "ready"

    @contextlib.contextmanager
    def _permit(self, ready):
        with _REGISTRY_LOCK:
            self._check_valid(ready)
            self._permits += 1
        try:
            yield self
        finally:
            with _REGISTRY_LOCK:
                self._permits -= 1

    def operation(self, ready=False):
        return self._permit(ready)

    def activity(self):
        return self._permit(True)

    def close(self):
        canon = getattr(self, "_canon", None)
        if not isinstance(canon, str):
            raise RuntimeError("guard is not registered")

        with _REGISTRY_LOCK:
            if _REGISTRY.get(canon) is not self:
                raise RuntimeError("guard is not registered")
            if getattr(self, "_pid", None) != os.getpid():
                raise RuntimeError("guard belongs to another process")
            if getattr(self, "_phase", None) not in _LIVE_PHASES:
                raise RuntimeError("guard is closed")
            if getattr(self, "_permits", 0) != 0:
                raise RuntimeError("guard has outstanding permits")
            fd = getattr(self, "_fd", None)
            if not isinstance(fd, int) or fd < 0:
                raise RuntimeError("guard descriptor is invalid")

            self._phase = "closed"
            self._fd = -1
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                finally:
                    os.close(fd)
            finally:
                if _REGISTRY.get(canon) is self:
                    del _REGISTRY[canon]

    def __enter__(self):
        self._valid()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


__all__ = ("MockHostSession",)
