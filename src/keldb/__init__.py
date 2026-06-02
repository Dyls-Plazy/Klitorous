"""
KelDB

An asynchronous hierarchical key-value database abstraction.

KelDB organizes data as a tree of nodes. Each node can store a value and have subnodes. Storage is delegated to a backend Hook.

Core Components:
    - Node: Represents a node in the database tree.
    - Hook: Backend abstraction interface for custom setups.
    - FileStoreHook: Filesystem-backed implementation.
    - KelDB: Root database node.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Optional, IO
import orjson as json
import aiofiles
import asyncio
import pathlib
import secrets
import base64
import shutil
import os


# =========================
# Utility functions
# =========================


async def _readlines(target: IO[bytes]) -> AsyncIterator[bytes]:
    while True:
        buffer = target.read(65535)

        if not buffer:
            break

        item = b""

        for char in [buffer[i : i + 1] for i in range(len(buffer))]:
            if char == b"\n":
                yield item
                item = b""
            else:
                item += char


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

    def __repr__(self):
        return f"Node(name='{self.name}', path='{self.path}')"

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

    async def list_subnodes(
        self, recursive: bool = False, include_self: bool = False
    ) -> AsyncIterator["Node"]:
        """
        Iterate over subnodes.

        Arguments:
            recursive (bool): Whether to recursively iterate over the entire tree.
            include_self (bool): Whether to include itself as a node in the list (if the node itself actually exists)

        Yields:
            Node: Subnode objects.
        """
        if not await self.exists():
            return

        if include_self:
            yield self

        next_list = []

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

            if recursive:
                next_list.append(subnode)

        for subnode in next_list:
            async for subsubnode in subnode.list_subnodes(recursive=True):
                yield subsubnode

    async def get_subnode(self, subnode_name: str) -> "Node":
        """
        Get a reference to a subnode.

        Args:
            subnode_name (str): Name of subnode.

        Returns:
            Node: Subnode reference.
        """
        if "/" in subnode_name:
            node = self

            for node_name in (x for x in subnode_name.split("/") if x):
                node = await node.get_subnode(node_name)

            return node

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
        Recursively delete this node and all subnodes.
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
        self.lock = asyncio.Lock()
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
        async with self.lock:
            subnode = await (self.get_path_dict(path))

            return subnode.get("value")

    async def set_path_value(self, path: str, value: Any, cached: bool = False) -> Any:
        async with self.lock:
            subnode = await (self.get_path_dict(path, create=True))

            subnode["value"] = value

    async def list_path_subpaths(self, path: str, cached: bool = False) -> tuple[str]:

        async with self.lock:
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

        async with self.lock:
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
        self.locks = {}
        self.locklock = asyncio.Lock()
        self.locks_count = locks_count

    def __repr__(self):
        return f"FileStoreHook(dir='{self.dir}')"

    async def get_directory_lock(self, directory: str, area: str="generic") -> asyncio.Lock:
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

            async with aiofiles.open(file_path, "rb") as f:
                return json.loads(await f.read())

    async def set_path_value(self, path: str, value: Any, cached: bool = False) -> None:
        directory = await self.get_path_directory(path)

        async with await self.get_directory_lock(path):
            os.makedirs(directory, exist_ok=True)

            file_path = await self.get_path_directory(path, "value.json")
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(json.dumps(value))

    async def list_path_subpaths(
        self, path: str, cached: bool = False
    ) -> AsyncIterator[str]:
        directory = await self.get_path_directory(path)

        async with await self.get_directory_lock(path, area="list"):
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

    def __repr__(self):
        return f"KelDB(hook={self.hook})"

    async def get_node_from_path(self, path: str) -> Node:
        """
        Get a reference to a node from a path.

        Args:
            path (str): Path of node.

        Returns:
            Node: Node reference.
        """
        node = self

        for node_name in (x for x in path.split("/") if x):
            node = await node.get_subnode(node_name)

        return node

    async def dump_database(self, target: IO[bytes]) -> None:
        """
        Dump the database as a .keldb file.

        Args:
            target (IO[bytes]): Binary IO stream to write the database to.
        """

        target.write(json.dumps(1.0))
        target.write(b"\n")

        target.write(json.dumps({}))
        target.write(b"\n")

        async for subnode in self.list_subnodes(recursive=True, include_self=True):
            target.write(json.dumps(subnode.path))
            target.write(b"\n")
            target.write(json.dumps(await subnode.get_value()))
            target.write(b"\n")

    async def load_database_dump(self, target: IO[bytes]) -> None:
        """
        Load a .keldb file into the current database.

        Args:
            target (IO[bytes]): Binary IO stream to load the database from
        """

        placeholder_value = None

        version = placeholder_value
        header = placeholder_value
        path = placeholder_value
        value = placeholder_value

        async for line in _readlines(target):
            data = json.loads(line)

            if version is placeholder_value:
                version = data

                if version > 1:
                    raise RuntimeError(
                        f"This file is version {version}, while this version can only handle files up to 1.0."
                    )

                continue
            if header is placeholder_value:
                header = data
                continue
            if path is placeholder_value:
                path = data
                continue
            if value is placeholder_value:
                value = data

                await (await self.get_node_from_path(path)).set_value(value)

                path = placeholder_value
                value = placeholder_value

                continue
