Quickstart
==========

Klitorous lets you store data in a tree-like structure using ""nodes."

Installation
------------

.. code-block:: bash

   pip install klitorous

Basic Usage
-----------

.. code-block:: python

   from klitorous import KelDB, FileStoreHook

   db = KelDB(FileStoreHook("./data"))

   root = db
   users = await root.get_subnode("users")

   await users.set_value({"count": 1})
   value = await users.get_value()

What this does
--------------

- Creates a file-backed database
- Stores a JSON value at /users
- Retrieves it asynchronously
