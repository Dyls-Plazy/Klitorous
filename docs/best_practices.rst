Best Practices
==============

This page details the recommended usage patterns for KelDB.

Use small, focused nodes
------------------------

When your use case allows it, try to split nodes into smaller subnodes whenever possible, within reason.

KelDB is more than capable of storing large objects, but less is more in this case.

Good:

.. code-block:: text

   /users/alice/profile/
   /users/alice/settings/
   /users/alice/token/
   /users/alice/password_hash/

Bad:

.. code-block:: text

   /users/alice/ -> giant JSON blob

Prefer structured paths
-----------------------

Use hierarchical paths in order to reduce the number of nodes in one path.

Most implementations do not handle excessive amounts of nodes in one path well. Think of it like cramming all of your files into one folder.

Good:

.. code-block:: python

   users_subnode = await db.get_subnode("users")
   alice = await users_subnode.get_subnode("alice")

Bad:

.. code-block:: python

   await db.get_subnode("users_alice_v2_final")

Beware of deadlocks
-----------------------

Do not attempt operations on a node while iterating over its subnodes. It may result in a deadlock depending on implementation. Think about it like writing to a file you're actively reading.

Do not do this:

.. code-block:: python

   async for subnode in my_node.list_subnodes():
      await my_node.set_value("Evil and intimidating deadlock!!")

If you *must* set a node's value, do something like this instead:

.. code-block:: python
   import asyncio

   async for subnode in my_node.list_subnodes():
      set_task = my_node.set_value("This will not deadlock as it will wait for the lock to release without blocking the main thread.")

      asyncio.create_task(set_task) # This will fix the deadlock but the set operation may be arbitrarily delayed

   await set_task # Optionally wait for the task to finish after the script

Back up your data!
----------------------

If it can fail, assume it will. Always keep backups of important data.

A simple and widely used guideline is the **3-2-1 rule**:

* **3 copies of your data** - keep the original plus two backups
* **2 different storage types** - for example SSD + external drive or disk + cloud
* **1 off-site copy** - store one backup in a different physical location

This reduces the risk of losing all your data from hardware failure, accidents, or disasters.

Don't risk data you can't afford to lose! `You aren't GitLab! <https://about.gitlab.com/blog/gitlab-dot-com-database-incident/>`_