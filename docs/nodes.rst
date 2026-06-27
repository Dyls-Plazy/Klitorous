Working with Nodes
===================

Nodes are the core abstraction in Klitorous.

What is a Node?
---------------

The Node object represents a singular node in the tree.

Example:

.. code-block:: text

   /
   ├── users/
   │   ├── alice/
   │   └── bob/
   └── config/

Creating Nodes
--------------

Nodes are created dynamically:

.. code-block:: python

   users = await db.get_subnode("users") # Nothing is created yet
   alice = await users.get_subnode("alice") # Still nothing
   await alice.set_value(None) # Now the nodes are created recursively

Setting Values
--------------

Nodes can store any JSON-serializable value:

.. code-block:: python

   await alice.set_value({
       "age": 25,
       "active": True
   })

All values are saved automatically, there is no save mechanism.

Reading Values
--------------

.. code-block:: python

   data = await alice.get_value()
   print(data)

Listing Subnodes
----------------

.. code-block:: python

   async for child in users.list_subnodes():
       print(child.name)

Deleting Nodes
--------------

.. code-block:: python

   await alice.delete()

Lock Tutorial
-------------

Consider a bank balance stored in a node:

.. code-block:: python

   balance = await db.get_subnode("balance")

A naive withdrawal implementation may have race conditions:

.. code-block:: python

   async def withdraw(amount):
       current = await balance.get_value()

       if current >= amount:
           await balance.set_value(current - amount)

If two withdrawals run concurrently, both may read the same balance before either update is written.

Using the node lock prevents this:

.. code-block:: python

   async def withdraw(amount):
       async with (await balance.get_lock(area="transactions")):
           current = await balance.get_value()

           if current >= amount:
               await balance.set_value(current - amount)

Now only one task can execute the critical section at a time.

Thread Safety and Hooks
~~~~~~~~~~~~~~~~~~~~~~~~

Node locks are **not** a replacement for Klitorous's internal thread-safety guarantees.

Klitorous operations are already designed to be safe to use concurrently. You do **not** need to manually acquire node locks simply to make database access thread-safe.

Instead, node locks exist to help users coordinate their own higher-level application logic when multiple operations must be treated as a single atomic sequence.

Likewise, node locks should not be relied upon to make hooks thread-safe. Hook implementations must still be written to handle concurrent execution correctly according to the hook system's requirements.

Node locks are entirely advisory. Klitorous does not automatically enforce them, nor does it regulate database operations based on whether a node's lock is currently held. Any task may still read from or write to a node regardless of the lock state.

Disabling Hook Locks
~~~~~~~~~~~~~~~~~~~~~~~~

If you are **confident you can handle locks yourself**, you can disable hook locking to manage it manually.

.. code-block:: python

   from klitorous.locking import DummyLockSystem

   somehook.locksystem = DummyLockSystem()

Note that this is **non-standard** usage and may introduce undocumented behaviors.

Node locks will continue to work as normal.
