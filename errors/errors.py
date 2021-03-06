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


class UnnormalisedGlobalType(Exception):
    """Certain checks can only be made once a (global) type has been
    normalised, so if you try to use it without normalising it, an
    exception is thrown"""

    pass
