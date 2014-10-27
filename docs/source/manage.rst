.. _manage:

Manage commands
===============

NewAuth ships with some CLI commands to help make your life easier.


.. _manage_update_contacts:

Update Contacts
---------------

Usage::

    $ python manage.py update_contacts

This method will fetch all contact lists of all the api keys given in :ref:`eve_settings` in order to build a list of corporations and alliances to allow or deny access and registration to NewAuth.

Make Admin
----------

Description
    Make a user join the group :py:attr:`newauth.settings_dist.BaseConfig.ADMIN_GROUP` and create the group if necessary.

Usage
    $ python manage.py make_admin $USER_ID

Make Ping
---------

Description
    Make a user join the group :py:attr:`newauth.settings_dist.BaseConfig.PING_GROUP` and create the group if necessary.

Usage
    $ python manage.py make_ping $USER_ID

Update Users
------------

Description
    Update one user or all users with Celery

Usage
    $ python manage.py update_users [user_id]
