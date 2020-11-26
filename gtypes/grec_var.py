from typing import Set, Dict, Tuple

import gtypes
from gtypes import HASH_SIZE
from gtypes.gend import GEnd
from gtypes.gaction import GAction
from gtypes.gtype import GType
from ltypes.laction import LAction
from ltypes.ltype import LType
from ltypes.lrec_var import LRecVar


class GRecVar(GType):
    def __init__(self, var_name: str) -> None:
        super().__init__()
        self.tvar = var_name
        self.gtype: GType = GEnd()
        self.ppts: Set[str] = set()

    def project(self, roles: Set[str]) -> Dict[str, LType]:
        return {role: LRecVar(self.tvar) for role in roles}

    def set_rec_gtype(self, tvar: str, gtype: GType) -> None:
        if tvar == self.tvar:
            self.gtype = gtype

    def first_actions(self, tvars: Set[str]) -> Set[GAction]:
        if self.tvar in tvars:
            return set()
        return self.gtype.first_actions(tvars.union({self.tvar}))

    def hash(self, tvars: Set[str]) -> int:
        if self.tvar in tvars:
            return self.tvar.__hash__() % HASH_SIZE
        return (
            self.tvar.__hash__() * gtypes.PRIME
            + self.gtype.hash(tvars.union({self.tvar}))
        ) % HASH_SIZE

    def to_string(self, indent: str) -> str:
        return f"{indent}continue {self.tvar}"

    def normalise(self) -> GType:
        return self

    def has_rec_var(self, tvar: str) -> bool:
        return self.tvar == tvar

    def build_mapping(
        self,
        mapping: Dict[str, Dict[LAction, Set[GAction]]],
        role_mapping: Dict[str, GAction],
        tvars: Set[str],
    ) -> None:
        # If all the roles which appear in the recursion have already been mapped,
        # then unfolding the recursion any further will not update the mapping
        if self.tvar in tvars or self.gtype.get_participants().issubset(
            role_mapping.keys()
        ):
            return
        self.gtype.build_mapping(mapping, role_mapping, tvars.union({self.tvar}))

    def all_participants(
        self, curr_tvar: str, tvar_ppts: Dict[str, Tuple[Set[str], Set[str]]]
    ) -> None:
        if self.tvar != curr_tvar:
            _, curr_tvars = tvar_ppts[curr_tvar]
            curr_tvars.add(self.tvar)

    def set_rec_participants(self, tvar_ppts: Dict[str, Set[str]]) -> None:
        pass

    def ensure_unique_tvars(
        self, tvar_mapping: Dict[str, str], tvar_names: Set[str], uid: int
    ):
        if self.tvar in tvar_mapping:
            self.tvar = tvar_mapping[self.tvar]

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, GRecVar):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.hash(set())
