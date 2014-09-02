from enum import Enum


class AuthContactType(Enum):
    corporation = 'Corporation'
    alliance = 'Alliance'


class APIKeyType(Enum):
    Account = 'Account'
    Character = 'Character'
    Corporation = 'Corporation'


class APIKeyStatus(Enum):
    valid = 'Valid'
    invalid_mask = 'Invalid Mask'
    invalid_expiration = 'Invalid Expiration'


class CharacterStatus(Enum):
    internal = 'Internal'
    ally = 'Ally'
    ineligible = 'Ineligible'
    purged = 'Purged'


class MessageType(Enum):
    Warning = 'warning'
    Danger = 'danger'
    Info = 'info'
    Success = 'success'


class MessageDisplay(Enum):
    All = '*'
    Register = 'register'


class GroupType(Enum):
    public = 'Public'
    private = 'Private'
    hidden = 'Hidden'


class GroupInviteStatus(Enum):
    pending = 'Pending'
    accepted = 'Accepted'
    rejected = 'Rejected'
