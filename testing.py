from io import BytesIO
import asyncio
import keldb

# Create a default KelDB database
database = keldb.KelDB(keldb.FileStoreHook("testdb"))

async def main():
    global database

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

    direct_reference = await database.get_node_from_path("/this/can/be/any/path/")

    print(direct_reference)
    print(await bar.get_subnode("/this/can/be/any/path/"))
    print(database)

    await direct_reference.set_value(True)
    await database.set_value("Even the database itself is technically a node!")

    async for subnode in database.list_subnodes(recursive=True, include_self=True): # Iterate over subnodes
        print(subnode.path)

    buffer = BytesIO()

    await database.dump_database(buffer)

    buffer.seek(0)

    database_dump = buffer.read()

    print(database_dump)

    buffer.seek(0)

    database = keldb.KelDB(keldb.MemoryStoreHook())

    await database.load_database_dump(buffer)

    buffer = BytesIO()

    await database.dump_database(buffer)

    buffer.seek(0)

    print(buffer.read() == database_dump)

    async with (await direct_reference.get_lock()):
        print("I have gotten a lock!")
        print(direct_reference.root.locksystem.locks)

asyncio.run(main())