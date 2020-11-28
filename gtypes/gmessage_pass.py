from typing import Set, Dict, Tuple

import gtypes
from gtypes.gaction import GAction
from gtypes.gtype import GType
from ltypes.laction import LAction
from ltypes.ltype import LType
from ltypes.lmessage_pass import LMessagePass


def update_mapping(
    new_role: str,
    role_action: GAction,
    fst_gaction: GAction,
    mapping: Dict[str, Dict[LAction, Set[GAction]]],
    role_mapping: Dict[str, GAction],
):
    # a->b --> b->c
    role_mapping[new_role] = fst_gaction
    r_mapping = mapping.setdefault(new_role, {})
    gaction_mapping = r_mapping.setdefault(role_action.project(new_role), set())
    gaction_mapping.add(fst_gaction)
    # a->b; b->c + b->a; b->c


class GMessagePass(GType):
    def __init__(self, action: GAction, cont: GType) -> None:
        super().__init__()
        self.action = action
        self.cont = cont
        self.ppts: Set[str] = set()

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
            self.action.__hash__() + self.cont.hash(tvars) * gtypes.PRIME
        ) % gtypes.HASH_SIZE

    def to_string(self, indent: str) -> str:
        return f"{indent}{self.action};\n{self.cont.to_string(indent)}"

    def normalise(self):
        self.cont: GType = self.cont.normalise()
        return self

    def has_rec_var(self, tvar: str) -> bool:
        return self.cont.has_rec_var(tvar)

    def ensure_unique_tvars(
        self, tvar_mapping: Dict[str, str], tvar_names: Set[str], uid: int
    ):
        self.cont.ensure_unique_tvars(tvar_mapping, tvar_names, uid)

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, GMessagePass):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.hash(set())
