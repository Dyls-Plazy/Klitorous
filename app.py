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
        print(await subnode.exists())

        await subnode.set_value(i)

        print(await subnode.exists())

        subnode = await subnode.get_subnode(secrets.token_hex(1))

    print(subnode.path)

    time.sleep(10)

    await database.delete()

    async for subsubnode in database.list_subnodes():
        print(subsubnode.path)

asyncio.run(main())