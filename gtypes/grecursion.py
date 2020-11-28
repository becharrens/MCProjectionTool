from typing import Set, Dict, Tuple

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
        self.mapping: Dict[str, Dict[Tuple[str], Dict[LAction, Set[GAction]]]]
        self.fst_gactions: Dict[str, Set[GAction]] = {}

    def project(self, roles: Set[str]) -> Dict[str, LType]:
        projections = self.gtype.project(roles)

        return {
            role: LRecursion(self.tvar, projection)
            for role, projection in projections.items()
        }

    def set_rec_gtype(self, tvar: str, gtype: GType) -> None:
        assert tvar != self.tvar, "Duplicate TVar"
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

    def build_mapping(
        self,
        mapping: Dict[str, Dict[LAction, Set[GAction]]],
        role_mapping: Dict[str, GAction],
        tvars: Set[str],
    ) -> None:
        self.gtype.build_mapping(mapping, role_mapping, tvars)

    def all_participants(
        self, curr_tvar: str, tvar_ppts: Dict[str, Tuple[Set[str], Set[str]]]
    ) -> None:
        _, curr_tvars = tvar_ppts[curr_tvar]
        curr_tvars.add(self.tvar)
        tvar_ppts[self.tvar] = (set(), set())
        self.gtype.all_participants(self.tvar, tvar_ppts)

    def set_rec_participants(self, tvar_ppts: Dict[str, Set[str]]) -> None:
        self.ppts = tvar_ppts[self.tvar]
        self.gtype.set_rec_participants(tvar_ppts)

    def ensure_unique_tvars(
        self, tvar_mapping: Dict[str, str], tvar_names: Set[str], uid: int
    ):
        if self.tvar in tvar_names:
            new_tvar, uid = GType.unique_tvar(self.tvar, tvar_names, uid)
            tvar_mapping[self.tvar] = new_tvar
            self.tvar = new_tvar
        else:
            tvar_names.add(self.tvar)
        self.gtype.ensure_unique_tvars(tvar_mapping, tvar_names, uid)

    def fst_global_actions_rec(
        self,
        curr_tvar: str,
        rec_gactions: Dict[str, Tuple[Set[str], Set[GAction]]],
        tvar_deps: Dict[str, Set[str]],
    ):
        tvar_deps[curr_tvar].add(self.tvar)
        tvar_deps[self.tvar] = set()
        rec_gactions[self.tvar] = (set(), set())
        self.gtype.fst_global_actions_rec(self.tvar, rec_gactions, tvar_deps)

    def set_rec_fst_global_actions(self, rec_gactions: Dict[str, Set[GAction]]):
        self.fst_gactions = rec_gactions[self.tvar]

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, GRecursion):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.gtype.hash(set())
