import asyncio

class LockSystem():
    pass

class DummyLock(asyncio.Lock):
    def __init__(self):
        pass

    async def __aenter__(self) -> None:
        pass

    async def __aexit__(self) -> None:
        pass

    async def acquire(self) -> bool:
        return True
    
    def release(self) -> None:
        return None
    
    def locked(self) -> bool:
        return False

class DummyLockSystem(LockSystem):
    def __init__(self):
        pass

    async def _get_path_lock(self, directory: str, area: str="generic") -> DummyLock:
        return DummyLock()
    
class BasicLockSystem(LockSystem):
    def __init__(self, locks_count:int=10000):
        self.locks = {}
        self.locklock = asyncio.Lock()
        self.locks_count = locks_count

    async def _get_path_lock(self, directory: str, area: str="generic") -> asyncio.Lock:
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
    def __init__(self):
        self.lock = asyncio.Lock()

    async def _get_path_lock(self, directory: str, area: str="generic") -> asyncio.Lock:
        return self.lock
    
