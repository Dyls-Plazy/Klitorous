import asyncio
import keldb
import time

database = keldb.KelDB(keldb.FileStoreHook("./testdb/"))

async def main():
    await database.set_value(f"Test {time.time()}")

    print(await database.get_value())

    async for subnode in database.list_subnodes():
        print(subnode.path)

asyncio.run(main())