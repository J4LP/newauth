.. _settings:

.. py:currentmodule:: newauth.settings

Settings
========

Settings in NewAuth works by subclassing :py:class:`BaseConfig` with "DevConfig" or "ProdConfig" or any other prefix.
The prefix will be read from `NEWAUTH_ENV` and default to "Dev".

.. autoclass:: BaseConfig

   .. autoattribute:: SECRET_KEY
       :annotation:
   .. autoattribute:: APP_DIR
       :annotation:
   .. autoattribute:: PROJECT_ROOT
       :annotation:
   .. autoattribute:: DEBUG
       :annotation:
   .. autoattribute:: SQLALCHEMY_DATABASE_URI
       :annotation:
   .. autoattribute:: SQLALCHEMY_ECHO
       :annotation: