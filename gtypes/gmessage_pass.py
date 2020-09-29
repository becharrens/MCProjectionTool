from typing import Set, Dict

import gtypes
from gtypes.gaction import GAction
from gtypes.gtype import GType
from ltypes.ltype import LType
from ltypes.lmessage_pass import LMessagePass


class GMessagePass(GType):
    def __init__(self, action: GAction, cont: GType) -> None:
        super().__init__()
        self.action = action
        self.cont = cont

    def project(self, roles: Set[str]) -> Dict[str, LType]:
        projections = self.cont.project(roles)
        for role in roles:
            local_action = self.action.project(role)
            if local_action is not None:
                projections[role] = LMessagePass(local_action, projections[role])
        return projections

    def first_actions(self, tvars: Set[str]) -> Set[GAction]:
        return {self.action}

    def set_rec_gtype(self, tvar: str, gtype: GType) -> None:
        self.cont.set_rec_gtype(tvar, gtype)

    def hash(self, tvars: Set[str]) -> int:
        return (
            self.action.__hash__() * gtypes.PRIME + self.cont.hash(tvars)
        ) % gtypes.HASH_SIZE

    def to_string(self, indent: str) -> str:
        return f"{indent}{self.action};\n{self.cont.to_string(indent)}"

    def normalise(self):
        self.cont: GType = self.cont.normalise()
        return self

    def has_rec_var(self, tvar: str) -> bool:
        return self.cont.has_rec_var(tvar)

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, GMessagePass):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.hash(set())
