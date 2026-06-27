
# Klitorous
[![Latest PyPI package version](https://img.shields.io/pypi/v/klitorous.svg)](https://pypi.org/project/klitorous) [![Latest Read The Docs](https://readthedocs.org/projects/klitorous/badge/?version=stable)](https://klitorous.readthedocs.io/en/stable/)

Klitorous is a fork of KelDB for the Dyl's Plazy

## Installation
Install from PyPi:

    pip install -U klitorous

Or install from source

    git clone https://github.com/Dyls-Plazy/klitorous.git
    cd klitorous
    pip install -r requirements.txt
    python3 -m pip install -U . --force-reinstall

## Usage
Klitorous is quite flexible. There's only a few commands to learn.

    import asyncio
    import klitorous
    
    # Create a default Klitorous database (or load an existing database)
    database = klitorous.Klitorous(klitorous.FileStoreHook("./testdb/"))
    
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

