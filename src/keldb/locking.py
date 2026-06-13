import asyncio


class DummyLock(asyncio.Lock):
    """
    No-op lock implementation.

    This lock never blocks and is intended for situations where
    locking is disabled but a lock-like API is still required.
    """

    def __init__(self):
        pass

    async def __aenter__(self) -> None:
        """Enter the async context manager without acquiring a real lock."""
        pass

    async def __aexit__(self) -> None:
        """Exit the async context manager without releasing a real lock."""
        pass

    async def acquire(self) -> bool:
        """
        Simulate successful lock acquisition.

        Returns:
            True, always.
        """
        return True

    def release(self) -> None:
        """No-op release method."""
        return None

    def locked(self) -> bool:
        """
        Report lock state.

        Returns:
            False, since the lock is never actually held.
        """
        return False

class LockSystem:
    """Base interface for lock management systems."""
    pass

class DummyLockSystem(LockSystem):
    """
    Lock system that provides no-op locks.

    Useful when synchronization is unnecessary but code expects
    a lock provider.
    """

    def __init__(self):
        pass

    async def _get_path_lock(
        self,
        directory: str,
        area: str = "generic",
    ) -> DummyLock:
        """
        Return a dummy lock for the requested path.

        Args:
            directory: Path identifier.
            area: Optional lock namespace.

        Returns:
            A new DummyLock instance.
        """
        return DummyLock()


class BasicLockSystem(LockSystem):
    """
    Path-based lock manager.

    Maintains a pool of asyncio locks keyed by directory/path,
    allowing independent synchronization of different resources.
    """

    def __init__(self, locks_count: int = 10000):
        """
        Initialize the lock system.

        Args:
            locks_count: Maximum number of cached locks to retain.
        """
        self.locks = {}
        self.locklock = asyncio.Lock()
        self.locks_count = locks_count

    async def _get_path_lock(
        self,
        directory: str,
        area: str = "generic",
    ) -> asyncio.Lock:
        """
        Retrieve or create a lock for a specific path.

        The lock registry is protected by an internal lock to ensure
        safe concurrent access. Unused locks may be evicted when the
        cache exceeds the configured size.

        Args:
            directory: Path identifier.
            area: Optional lock namespace.

        Returns:
            An asyncio.Lock associated with the path.
        """
        async with self.locklock:
            lock = self.locks.pop(f"_{area}{directory}", None)

            if not lock:
                lock = asyncio.Lock()

            while len(self.locks) > self.locks_count:
                lock_name = next(iter(self.locks.keys()))

                if self.locks[lock_name].locked():
                    break

                self.locks.pop(lock_name)

            self.locks[directory] = lock

            return lock


class SingleLockSystem(LockSystem):
    """
    Lock system that uses a single shared lock for all paths.

    This provides the strongest synchronization but allows only one
    operation to proceed at a time regardless of directory.
    """

    def __init__(self):
        """Initialize the shared lock."""
        self.lock = asyncio.Lock()

    async def _get_path_lock(
        self,
        directory: str,
        area: str = "generic",
    ) -> asyncio.Lock:
        """
        Return the shared lock.

        Args:
            directory: Ignored.
            area: Ignored.

        Returns:
            The single shared asyncio.Lock instance.
        """
        return self.lock