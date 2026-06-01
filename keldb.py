"""
KelDB

An asynchronous hierarchical key-value database abstraction.

KelDB organizes data as a tree of nodes. Each node can store a value and have child nodes. Storage is delegated to a backend Hook.

Core Components:
    - Node: Represents a node in the database tree.
    - Hook: Backend abstraction interface for custom setups.
    - FileStoreHook: Filesystem-backed implementation.
    - KelDB: Root database node.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Optional
import aiofiles
import asyncio
import pathlib
import base64
import shutil
import json
import os


# =========================
# Node
# =========================

class Node:
    """
    Represents a singular node.

    This object is a lightweight reference to a database path. It can store a value and contain subnodes.

    Attributes:
        root (KelDB): Root database instance.
        parent (Node | None): Parent node.
        name (str | None): Node name.
        path (str | None): Full database path.
    """

    def __init__(self) -> None:
        self.root: Optional["KelDB"] = None
        self.parent: Optional["Node"] = None
        self.name: Optional[str] = None
        self.path: Optional[str] = None

    async def get_value(self) -> Any:
        """
        Get the value of this node.

        Returns:
            Any: Stored value or None.
        """
        return await self.root.hook.get_path_value(
            self.path,
            cached=self.root.cache_enabled,
        )

    async def set_value(self, value: Any) -> None:
        """
        Set the value of this node.

        Args:
            value (Any): JSON-serializable value.
        """
        await self.root.hook.set_path_value(
            self.path,
            value,
            cached=self.root.cache_enabled,
        )

    async def list_subnodes(self) -> AsyncIterator["Node"]:
        """
        Iterate over subnodes.

        Yields:
            Node: Subnode objects.
        """
        if not await self.exists():
            return

        async for subnode_name in self.root.hook.list_path_subpaths(
            self.path,
            cached=self.root.cache_enabled,
        ):
            subnode = Node()
            subnode.root = self.root
            subnode.parent = self
            subnode.name = subnode_name
            subnode.path = self.path + f"{subnode_name}/"
            yield subnode

    async def get_subnode(self, subnode_name: str) -> "Node":
        """
        Get a reference to a child node.

        Args:
            subnode_name (str): Name of subnode.

        Returns:
            Node: Child node reference.
        """
        subnode = Node()
        subnode.root = self.root
        subnode.parent = self
        subnode.name = subnode_name
        subnode.path = self.path + f"{subnode_name}/"
        return subnode

    async def exists(self) -> bool:
        """
        Check if this node exists.

        Returns:
            bool: True if exists.
        """
        return await self.root.hook.check_path_exists(
            self.path,
            cached=self.root.cache_enabled,
        )

    async def delete(self) -> None:
        """
        Delete this node and all children.
        """
        if await self.exists():
            await self.root.hook.delete_path(
                self.path,
                cached=self.root.cache_enabled,
            )


# =========================
# Hook Interface
# =========================

class Hook:
    """
    Abstract storage backend interface.
    """

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
# File Store Hook
# =========================

class FileStoreHook(Hook):
    """
    Filesystem-backed storage implementation.

    Each node is stored as a directory. The value is stored in value.json inside the directory.
    """

    def __init__(self, dir: str) -> None:
        self.dir = pathlib.Path(dir).absolute()
        self.locks = [asyncio.Lock() for _ in range(100)]

    async def get_directory_lock(self, directory: str) -> asyncio.Lock:
        return self.locks[hash(directory) % len(self.locks)]

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

        async with await self.get_directory_lock(path):
            if not os.path.isfile(file_path):
                return None

            async with aiofiles.open(file_path, "r") as f:
                return json.loads(await f.read())

    async def set_path_value(self, path: str, value: Any, cached: bool = False) -> None:
        directory = await self.get_path_directory(path)

        async with await self.get_directory_lock(path):
            os.makedirs(directory, exist_ok=True)

            file_path = await self.get_path_directory(path, "value.json")
            async with aiofiles.open(file_path, "w") as f:
                await f.write(json.dumps(value))

    async def list_path_subpaths(
        self, path: str, cached: bool = False
    ) -> AsyncIterator[str]:
        directory = await self.get_path_directory(path)

        async with await self.get_directory_lock(path):
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

        async with await self.get_directory_lock(path):
            return os.path.isdir(directory)

    async def delete_path(self, path: str, cached: bool = False) -> None:
        directory = await self.get_path_directory(path)

        async with await self.get_directory_lock(path):
            shutil.rmtree(directory, ignore_errors=True)


# =========================
# KelDB Root
# =========================

class KelDB(Node):
    """
    Root database object.
    """

    def __init__(self, hook: Hook) -> None:
        self.root = self
        self.parent = None
        self.name = ""
        self.path = "/"
        self.hook = hook
        self.cache_enabled = True