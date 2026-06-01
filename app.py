import secrets
import asyncio
import keldb
import time

database = keldb.KelDB(keldb.FileStoreHook("./testdb/"))

async def main():
    await database.set_value(f"Test {time.time()}")

    print(await database.get_value())

    subnode = database

    for i in range(25):
        await subnode.set_value(i)

        subnode = await subnode.get_subnode(secrets.token_hex(1))

    print(subnode.path)

    async for subsubnode in database.list_subnodes():
        print(subsubnode.path)

asyncio.run(main())