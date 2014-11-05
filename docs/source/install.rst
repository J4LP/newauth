.. _install:

Installation
============

Dependencies
------------

You will need, of course, Python (tested on 2.7, might need some fixes for Python 3.x), a running SQL server (NewAuth has been tested with SQLite and PostgreSQL but it should work with MySQL) and a Redis server. Create a new SQL database and a user for NewAuth and keep its login details close.
You might also need some extra packages to compile python dependencies, most notably libxml2 and database driver specific libraries.

Downloading
-----------

Here's the basic commands to download and install NewAuth:

.. code-block:: bash

    $ git clone https://github.com/J4LP/newauth.git
    $ cd newauth
    $ virtualenv .
    $ source bin/activate
    $ pip install -r requirements.txt

Configuration
-------------

NewAuth configuration is read from the :file:`newauth/settings.py` file. Refer to :ref:`settings` for documentation and come back here!


Corporation API Key
-------------------

In order to pick up your corporation/alliance, you will need to generate a corporation or alliance key with the Contact and Standings permissions. Please click this `link`_ to open CCP's API page to create one.

.. _link: https://support.eveonline.com/api/key/CreatePredefined/

Initial launch
--------------

Once NewAuth is configured, you will need to migrate the database:

.. code-block:: bash

    $ python manage.py db migrate
    $ python manage.py db upgrade

You should then be able to start NewAuth with its development server:

.. code-block:: bash

    $ python run.py
     * Running on http://0.0.0.0:5002/

Once NewAuth is confirmed to be working, it's time to import your corporation's contacts:

.. code-block:: bash

    $ python manage.py update_contacts

And there you have it! NewAuth is now running on your computer. You are now able to create an account and login with it! Once your account created, make yourself admin with:

.. code-block:: bash

     $ python manage.py make_admin $YOUR_USER_ID

Thanks you for using NewAuth!

Background Tasks
----------------

NewAuth is using Celery to delegate heavy tasks to the background and cronjobs. Please refer to `Celery's documentation`_ for more configuration options. You will need to launch it alongside newauth with::

    celery -A manage.celery worker -Q newauth,celery -B

This command should be ran in the root directory of NewAuth.

.. _`Celery's documentation`: http://celery.readthedocs.org/en/latest/index.html
