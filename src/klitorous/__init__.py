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
import asyncio

from .locking import *
from .hooks import *


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

    async def get_lock(self, area="generic") -> asyncio.Lock:
        return await self.root._get_path_lock(self.path, area=area)

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
# KelDB Root
# =========================


class KelDB(Node):
    """
    Root database object.
    """

    def __init__(self, hook: Hook, locks_count:int=10000) -> None:
        self.root = self
        self.parent = None
        self.name = ""
        self.path = "/"
        self.hook = hook
        self.cache_enabled = True

        self.locksystem = BasicLockSystem(locks_count=locks_count)

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
    
    async def _get_path_lock(self, directory: str, area: str="generic") -> asyncio.Lock:
        return await self.locksystem._get_path_lock(directory, area)
