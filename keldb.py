from typing import Any
from enum import Enum
import aiofiles
import asyncio
import pathlib
import base64
import shutil
import json
import os

class Node():
    def __init__(self):
        # Basic information
        self.root = None
        self.parent = None
        self.name = None
        self.path = None

    async def get_value(self) -> Any:
        return await self.root.hook.get_path_value(self.path)
    
    async def set_value(self, value:Any) -> None:
        await self.root.hook.set_path_value(self.path, value)

    async def list_subnodes(self) -> iter:
        if not await self.exists():
            return

        async for subnode_name in self.root.hook.list_path_subpaths(self.path):
            subnode = Node()

            subnode.root = self.root
            subnode.parent = self
            subnode.name = subnode_name
            subnode.path = self.path + f"{subnode_name}/"

            yield subnode
    
    async def get_subnode(self, subnode_name:str):
        subnode = Node()

        subnode.root = self.root
        subnode.parent = self
        subnode.name = subnode_name
        subnode.path = self.path + f"{subnode_name}/"

        return subnode
    
    async def exists(self) -> bool:
        return await self.root.hook.check_path_exists(self.path)
    
    async def delete(self) -> None:
        if await self.exists():
            await self.root.hook.delete_path(self.path)

class Hook():
    async def get_path_value(self, path:str, cached=False) -> Any:
        raise NotImplementedError
    
    async def set_path_value(self, path:str, value:Any, cached=False) -> Any:
        raise NotImplementedError
    
    async def list_path_subpaths(self, path:str, cached=False) -> iter:
        raise NotImplementedError

    async def check_path_exists(self, path:str, cached=False) -> bool:
        raise NotImplementedError

class FileStoreHook(Hook):
    def __init__(self, dir:str):
        self.dir = pathlib.Path(dir).absolute()

        self.store = {}
    
    async def get_path_directory(self, path:str, file:str="") -> str:
        parts = (self.dir,) + tuple(base64.urlsafe_b64encode(x.encode()).decode() for x in path.split("/") if x != "") + (file,)

        return os.path.join(*parts)

    async def get_path_value(self, path:str, cached=False) -> Any:
        directory = await self.get_path_directory(path, "value.json")

        if not cached:
            if not os.path.isfile(directory):
                return None

            async with aiofiles.open(directory, 'r') as f:
                return json.loads(await f.read())
            
    async def set_path_value(self, path:str, value:Any, cached=False) -> None:
        os.makedirs(await self.get_path_directory(path), exist_ok=True)

        async with aiofiles.open(await self.get_path_directory(path, "value.json"), 'w') as f:
            return await f.write(json.dumps(value))
        
    async def list_path_subpaths(self, path:str, cached=False) -> iter:
        with os.scandir(await self.get_path_directory(path)) as entries:
            for entry in entries:
                if entry.is_dir():
                    try:
                        entry_name = base64.urlsafe_b64decode(entry.name.encode()).decode()
                    except:continue

                    yield entry_name

    async def check_path_exists(self, path:str, cached=False) -> bool:
        return os.path.isdir(await self.get_path_directory(path))
    
    async def delete_path(self, path:str, cached=False) -> bool:
        return shutil.rmtree(await self.get_path_directory(path))

class KelDB(Node):
    def __init__(self, hook:Hook):
        self.root = self
        self.parent = None
        self.name = ""
        self.path = "/"

        self.hook = hook