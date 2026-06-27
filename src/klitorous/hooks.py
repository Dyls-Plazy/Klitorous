from typing import Any, AsyncIterator
import orjson as json
import aiofiles
import pathlib
import base64
import shutil
import os

from .locking import *

# =========================
# Hook Interface
# =========================


class Hook:
    """
    Abstract storage backend interface.
    """

    def __repr__(self):
        return "Hook()"

    async def get_path_value(self, path: str, cached: bool = False) -> Any:
        raise NotImplementedError

    async def set_path_value(self, path: str, value: Any, cached: bool = False) -> Any:
        raise NotImplementedError

    async def list_path_subpaths(
        self, path: str, cached: bool = False
    ) -> AsyncIterator[str]:
        raise NotImplementedError

    async def check_path_exists(self, path: str, cached: bool = False) -> bool:
        raise NotImplementedError

    async def delete_path(self, path: str, cached: bool = False) -> None:
        raise NotImplementedError


# =========================
# Memory Store Hook
# =========================


class MemoryStoreHook:
    """
    Simple memory-backed storage implementation. (for testing)
    """

    def __init__(self):
        self.locksystem = SingleLockSystem()
        self.data = {"subnodes": {}, "exists": True}

    def __repr__(self):
        return "MemoryStoreHook()"

    async def get_path_dict(self, path: str, create: bool = False) -> dict:
        subnode = self.data

        for subnode_name in (x for x in path.split("/") if x):
            subnodes = subnode["subnodes"]
            if not subnodes.get(subnode_name):
                subnodes[subnode_name] = {"subnodes": {}, "exists": False}

            subnode = subnodes.get(subnode_name)

            if create:
                subnode["exists"] = True

        return subnode

    async def get_path_value(self, path: str, cached: bool = False) -> Any:
        async with (await self.locksystem._get_path_lock(path)):
            subnode = await (self.get_path_dict(path))

            return subnode.get("value")

    async def set_path_value(self, path: str, value: Any, cached: bool = False) -> Any:
        async with (await self.locksystem._get_path_lock(path)):
            subnode = await (self.get_path_dict(path, create=True))

            subnode["value"] = value

    async def list_path_subpaths(self, path: str, cached: bool = False) -> AsyncIterator[str]:
        async with (await self.locksystem._get_path_lock(path, "list")):
            full_list = (
                subnode_name
                for subnode_name, subnode in (await self.get_path_dict(path))[
                    "subnodes"
                ].items()
                if subnode["exists"]
            )

        for subnode_name in full_list:
            yield subnode_name

    async def check_path_exists(self, path: str, cached: bool = False) -> bool:
        return (await self.get_path_dict(path))["exists"]

    async def delete_path(self, path: str, cached: bool = False) -> None:
        path_tuple = tuple(x for x in path.split("/") if x)

        async with (await self.locksystem._get_path_lock(path)):
            (await self.get_path_dict("/".join(path_tuple[:-1])))["subnodes"].pop(
                path_tuple[-1]
            )


# =========================
# File Store Hook
# =========================


class FileStoreHook(Hook):
    """
    Filesystem-backed storage implementation.

    Each node is stored as a directory. The value is stored in value.json inside the directory.
    """

    def __init__(self, dir: str, locks_count: int = 10000) -> None:
        self.dir = pathlib.Path(dir).absolute()
        self.locksystem = BasicLockSystem(locks_count=locks_count)

    def __repr__(self):
        return f"FileStoreHook(dir='{self.dir}')"

    async def get_path_directory(self, path: str, file: str = "") -> str:
        parts = (
            self.dir,
            *[
                base64.urlsafe_b64encode(x.encode()).decode()
                for x in path.split("/")
                if x
            ],
            file,
        )
        return os.path.join(*parts)

    async def get_path_value(self, path: str, cached: bool = False) -> Any:
        file_path = await self.get_path_directory(path, "value.json")

        async with (await self.locksystem._get_path_lock(path)):
            if not os.path.isfile(file_path):
                return None

            async with aiofiles.open(file_path, "rb") as f:
                return json.loads(await f.read())

    async def set_path_value(self, path: str, value: Any, cached: bool = False) -> None:
        directory = await self.get_path_directory(path)

        async with (await self.locksystem._get_path_lock(path)):
            os.makedirs(directory, exist_ok=True)

            file_path = await self.get_path_directory(path, "value.json")
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(json.dumps(value))

    async def list_path_subpaths(
        self, path: str, cached: bool = False
    ) -> AsyncIterator[str]:
        directory = await self.get_path_directory(path)

        async with (await self.locksystem._get_path_lock(path, area="list")):
            if not os.path.isdir(directory):
                return

            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_dir():
                        try:
                            yield base64.urlsafe_b64decode(entry.name.encode()).decode()
                        except Exception:
                            continue

    async def check_path_exists(self, path: str, cached: bool = False) -> bool:
        directory = await self.get_path_directory(path)

        async with (await self.locksystem._get_path_lock(path)):
            return os.path.isdir(directory)

    async def delete_path(self, path: str, cached: bool = False) -> None:
        directory = await self.get_path_directory(path)

        async with (await self.locksystem._get_path_lock(path)):
            shutil.rmtree(directory, ignore_errors=True)