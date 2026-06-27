Creating a Custom Hook
======================

A ``Hook`` is the storage backend interface used by Klitorous. It defines how data is stored, retrieved, listed, and deleted.

To extend Klitorous, you implement a subclass of ``Hook`` and provide your own storage logic (database, cloud storage, in-memory store, etc.).

Why Hooks exist
---------------

Hooks separate:

* **Klitorous logic** (tree structure, nodes, paths)
* **Storage logic** (filesystem, memory, remote APIs, databases)

This makes Klitorous fully hot-pluggable, allowing you to connect the simplicity of Klitorous to whatever your use case requires.

However, you bear the responsibility of storage, thread-safety, caching, and integration.

Basic structure
---------------

All hooks must implement the following methods:

.. code-block:: python

    class MyHook(Hook):
        async def __init__(self):
            self.locksystem = None # Always define the locksystem property and ensure it can be changed dynamically

        async def get_path_value(self, path, cached=False):
            pass # Return a JSON-serializable object, or None if it doesn't exist

        async def set_path_value(self, path, value, cached=False):
            pass # Return anything

        async def list_path_subpaths(self, path, cached=False):
            pass # Ideally, return an lazy iterator to save on memory

        async def check_path_exists(self, path, cached=False):
            pass # Return a boolean

        async def delete_path(self, path, cached=False):
            pass # Return anything

Your hook should never throw an exception unless an internal failure occurs, such as a disk I/O failure.

Using your hook
---------------

Once implemented, pass it into Klitorous:

.. code-block:: python

    from klitorous import KelDB

    db = KelDB(MyHook())
