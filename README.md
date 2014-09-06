NewAuth
=========

NewAuth is a full featured authentication system for your Eve Online alliance or corporation. It brings out of the box support for multiple api keys per user, user groups with applications and invitations, and pings.

It is easily extensible and we're very much welcoming of new features!

## Instructions

    # Clone the repository and create a new virtual environment
    git clone https://github.com/J4LP/newauth
    virtualenv .
    pip install -r requirements.txt
    # Edit the settings
    cp auth/settings_dist.py auth/settings.py
    # Get the assets
    bower install
    # Build the assets
    python manage.py assets build
    # Migrate the database
    python manage.py db migrate
    python manage.py db upgrade
    # Launch
    python run.py

## Preview

![Imgur](http://i.imgur.com/1nBFYxp.png)

## Features

* Multi API Keys support
* Groups
* Support for plugins
* LDAP support with the [Pizza LDAP Schema](https://bitbucket.org/Sylnai/pizza-auth)
* Pings (support for XMPP and more coming soon)
* Administration (more and more being developed)

## Tests

Tests are coming as I manage to figure out how to deal with API keys and fixture data

## Contributing

The goal is to allow other people to easily use NewAuth for their alliance or corporation. If you wish to add a feature or if you find an issue, please open an issue or a pull request and we'll discuss things ! We also hangs in asylum@conference.talkinlocal.org (Jabber)!

## LICENSE

The MIT License (MIT)

Copyright (c) [2014] [@adrien-f] and collaborators

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
