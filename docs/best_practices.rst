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

Be careful with locks
-----------------------

Keep in mind that locks are not guaranteed to be persistent.

.. code-block:: python

   import asyncio

   lock = await subnode.get_lock()

   asyncio.sleep(60)

   later_lock = await subnode.get_lock() # lock and later_lock are not guaranteed to be the same lock

You must call subnode.get_lock() every time you need to aquire a lock. The only guarantee is that one task can hold the lock at a time.

.. code-block:: python

   import asyncio

   async def dangerous_function(value):
      async with (await subnode.get_lock()):
         await subnode.set_value(value)

   await asyncio.gather(dangerous_function("a"), dangerous_function("b"))

Back up your data!
----------------------

If it can fail, assume it will. Always keep backups of important data.

A simple and widely used guideline is the **3-2-1 rule**:

* **3 copies of your data** - keep the original plus two backups
* **2 different storage types** - for example SSD + external drive or disk + cloud
* **1 off-site copy** - store one backup in a different physical location

This reduces the risk of losing data from hardware failure, accidents, or disasters.

And don't just **have** them, **integrate** them. Ensure your team knows how your backup system works, how to restore from it, and how long recovery will take. Make sure it works, because a broken backup system is no backup system.

Don't risk data you can't afford to lose! `You aren't GitLab! <https://about.gitlab.com/blog/gitlab-dot-com-database-incident/>`_