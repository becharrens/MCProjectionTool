from typing import Set, Dict, Tuple, List, Optional

import gtypes
from gtypes.gaction import GAction
from gtypes.gtype import GType
from ltypes.laction import LAction
from ltypes.lrecursion import LRecursion
from ltypes.ltype import LType


class GRecursion(GType):
    def __init__(self, tvar: str, gtype: GType) -> None:
        super().__init__()
        self.tvar = tvar
        self.gtype = gtype
        self.gtype.set_rec_gtype(self.tvar, self)

    def project(self, roles: Set[str]) -> Dict[str, LType]:
        projections = self.gtype.project(roles)

        return {
            role: LRecursion(self.tvar, projection)
            for role, projection in projections.items()
        }

    def set_rec_gtype(self, tvar: str, gtype: GType) -> None:
        # TODO: Fix tvars
        # assert tvar != self.tvar, "Duplicate TVar"
        self.gtype.set_rec_gtype(tvar, gtype)

    def first_actions(self, tvars: Set[str]) -> Set[GAction]:
        return self.gtype.first_actions(tvars)

    def hash(self, tvars: Set[str]) -> int:
        return (
            self.tvar.__hash__() * gtypes.PRIME + self.gtype.hash(tvars)
        ) % gtypes.HASH_SIZE

    def to_string(self, indent: str) -> str:
        next_indent = indent + "\t"
        return f"{indent}rec {self.tvar} {{\n{self.gtype.to_string(next_indent)}\n{indent}}}"

    def normalise(self) -> GType:
        self.gtype = self.gtype.normalise()
        if self.gtype.has_rec_var(self.tvar):
            return self
        return self.gtype

    def has_rec_var(self, tvar: str) -> bool:
        return self.gtype.has_rec_var(tvar)

    def ensure_unique_tvars(
        self, tvar_mapping: Dict[str, str], tvar_names: Set[str], uid: int
    ):
        old_name = None
        old_tvar = self.tvar
        if self.tvar in tvar_names:
            new_tvar, uid = GType.unique_tvar(self.tvar, tvar_names, uid)
            old_name = tvar_mapping[self.tvar]
            tvar_mapping[self.tvar] = new_tvar
            self.tvar = new_tvar
        else:
            tvar_names.add(self.tvar)
            tvar_mapping[self.tvar] = self.tvar
        self.gtype.ensure_unique_tvars(tvar_mapping, tvar_names, uid)
        if old_name is not None:
            tvar_mapping[old_tvar] = old_name

    def ensure_consistent_payloads(
        self, payload_mapping: Dict[str, List[Tuple[Optional[str], str]]]
    ) -> None:
        self.gtype.ensure_consistent_payloads(payload_mapping)

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, GRecursion):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.gtype.hash(set())
