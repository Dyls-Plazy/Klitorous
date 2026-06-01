from typing import Any, Union
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
    
    async def delete_path(self, path:str) -> None:
        raise NotImplementedError

class FileStoreHook(Hook):
    def __init__(self, dir:str):
        self.dir = pathlib.Path(dir).absolute()

        self.locks = []

        for _ in range(100):
            self.locks.append(asyncio.Lock())

    async def get_directory_lock(self, directory:str) -> asyncio.Lock:
        return self.locks[hash(directory)%len(self.locks)]
    
    async def get_path_directory(self, path:str, file:str="") -> str:
        parts = (self.dir,) + tuple(base64.urlsafe_b64encode(x.encode()).decode() for x in path.split("/") if x != "") + (file,)

        return os.path.join(*parts)

    async def get_path_value(self, path:str, cached=False) -> Any:
        directory = await self.get_path_directory(path, "value.json")

        async with (await self.get_directory_lock(await self.get_path_directory(path))):
            if not os.path.isfile(directory):
                return None

            async with aiofiles.open(directory, 'r') as f:
                return json.loads(await f.read())
            
    async def set_path_value(self, path:str, value:Any, cached=False) -> None:
        directory = await self.get_path_directory(path)

        async with (await self.get_directory_lock(directory)):
            os.makedirs(directory, exist_ok=True)

            async with aiofiles.open(await self.get_path_directory(path, "value.json"), 'w') as f:
                await f.write(json.dumps(value))
        
        return value
        
    async def list_path_subpaths(self, path:str, cached=False) -> iter:
        directory = await self.get_path_directory(path)

        async with (await self.get_directory_lock(directory)):
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_dir():
                        try:
                            entry_name = base64.urlsafe_b64decode(entry.name.encode()).decode()
                        except:continue

                        yield entry_name

    async def check_path_exists(self, path:str, cached=False) -> bool:
        directory = await self.get_path_directory(path)

        async with (await self.get_directory_lock(directory)):
            return os.path.isdir(directory)
    
    async def delete_path(self, path:str, cached=False) -> None:
        directory = await self.get_path_directory(path)

        async with (await self.get_directory_lock(directory)):
            shutil.rmtree(directory)

class KelDB(Node):
    def __init__(self, hook:Hook):
        self.root = self
        self.parent = None
        self.name = ""
        self.path = "/"

        self.hook = hook