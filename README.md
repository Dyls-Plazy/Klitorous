
# KelDB
[![Latest PyPI package version](https://img.shields.io/pypi/v/keldb.svg)](https://pypi.org/project/keldb) [![Latest Read The Docs](https://readthedocs.org/projects/keldb/badge/?version=latest)](https://keldb.readthedocs.io/en/latest/)

KelDB is a simple node-based database for asyncio applications.
## Dynamics
KelDB is organised into **nodes**. A node is a container that can hold a value and/or other **subnodes**. The database itself is the root node, and every piece of data is a subnode of it.
## Usage
KelDB is quite flexible. There's only a few commands to learn.

    import asyncio
    import keldb
    
    # Create a default KelDB database (or load an existing database)
    database = keldb.KelDB(keldb.FileStoreHook("./testdb/"))
    
    async def main():
        # Create subnodes (lazy creation - no actual subnodes are created yet)
        foo = await database.get_subnode("foo")
        bar = await database.get_subnode("bar")
        baz = await database.get_subnode("baz")
    
        await bar.set_value("This can be any json-serializable object.") # Set a value (now "bar" is actually created)
        
        await baz.set_value({"type": "user", "name": "Gabe Newell"}) # Now "baz" is actually created
    
        text_subnode = await foo.get_subnode("text")
    
        await text_subnode.set_value("If you are reading this, this data saved correctly!") # Write text in a subnode's subnode. (now both "foo" and "foo/text" are created)
    
        print(await text_subnode.get_value()) # Read a value from the database
    
        await foo.delete() # Delete a subnode (do note that this also recursively deletes any subnodes under it)
    
        async for subnode in database.list_subnodes(): # Iterate over subnodes
            print(subnode.path)
    
        await database.set_value("Even the database itself is technically a node!")
    
    asyncio.run(main())

