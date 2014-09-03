class Pinger(object):
    """
    Pinger base class to create a new pinger.

    :param Ping: Ping object
    """

    ping = ""
    """Ping object"""

    configuration = []
    """
    Extra fields names to add to the User model.

    The description supports Markdown. This will be serialized as JSON and saved per user.

    :var list: (field_name, name, description)
    """

    name = ""
    """Pinger name used for configuration storage and in other various places."""

    display_name = ""
    """Pinger name to be displayed."""

    description = ""
    """Description to be displayed, supports Markdown."""

    immutable = False
    """Can this pinger be disabled ?"""

    def __init__(self, ping=None):
        """The pinger is given the ping object that contains the user list and ping message."""
        self.ping = ping

    def send_ping(self):
        """
        Send the ping to the users.
        """
        raise NotImplementedError()

    def enabled(self, user):
        """
        Test if the user has the pinger enabled and configured.

        :rtype: boolean
        """
        raise NotImplementedError()

    def enable(self, user, user_configuration):
        """
        Called when enabling the pinger.

        Modify the user profile to save pinger settings and validate settings.

        Feel free to flash messages through Flask's flash.

        `user_configuration` will be saved and tied to the user.

        :return: Return if the operation was successful or not.
        :rtype: boolean
        """
        raise NotImplementedError()

    def disable(self, user, user_configuration):
        """
        Called when disabling the pinger.

        Modify the user profile to disable the pinger so that self.enabled returns False.

        Feel free to flash messages through Flask's flash.

        `user_configuration` will be saved and tied to the user.

        :return: Return if the operation was successful or not.
        :rtype: boolean
        """
        raise NotImplementedError()

