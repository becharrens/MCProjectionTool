class InconsistentChoice(Exception):
    """When a role participates in some branches of a choice but not in others"""

    pass


class InvalidChoice(Exception):
    """When the first actions of the choice do not follow one of the valid
    communication patterns"""

    pass


class NotTraceEquivalent(Exception):
    """When different types don't have the same set of first actions they
    cannot be trace equivalent"""

    pass


class InconsistentChoiceLabel(Exception):
    """When different branches of a mixed choice have the same label
    for first actions of the same kind (send/receive). This could be due to
    inconsistent use of message payloads"""

    pass


class Violation(Exception):
    """When an unreachable state has been reached"""

    pass
