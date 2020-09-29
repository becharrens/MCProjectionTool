from typing import Dict, Set, List

import gtypes
from gtypes.gaction import GAction
from gtypes.gtype import GType

from ltypes.lchoice import LUnmergedChoice, LIDChoice
from ltypes.ltype import LType
from unionfind.unionfind import UnionFind


def _hash_list(elem_list, tvars):
    hashes = tuple(elem.hash(tvars) for elem in elem_list)
    return sum(hashes) % gtypes.HASH_SIZE


class GChoice(GType):
    def __init__(self, choices: List[GType]) -> None:
        super().__init__()
        self.branches = choices

    def project(self, roles: Set[str]) -> Dict[str, LType]:
        id_choices = GChoice._identify_independent_choices(self.branches)
        id_choice_projections = [id_choice.project(roles) for id_choice in id_choices]
        return {
            role: LUnmergedChoice([proj[role] for proj in id_choice_projections])
            for role in roles
        }

    def first_actions(self, tvars: Set[str]) -> Set[GAction]:
        return set(
            action for gtype in self.branches for action in gtype.first_actions(tvars)
        )

    def set_rec_gtype(self, tvar: str, gtype: GType) -> None:
        for id_choice in self.branches:
            id_choice.set_rec_gtype(tvar, gtype)

    def hash(self, tvars: set) -> int:
        return _hash_list(self.branches, tvars)

    @staticmethod
    def _identify_independent_choices(choices: List[GType]):
        ufind = UnionFind()
        for gtype in choices:
            actions = tuple(gtype.first_actions(set()))
            assert len(actions) == 1
            ufind.add(actions[0].get_participants(), gtype)
        return [GIDChoice(branches) for branches in ufind.get_subsets()]

    def to_string(self, indent) -> str:
        new_indent = indent + "\t"
        ltypes = [gtype.to_string(new_indent) for gtype in self.branches]
        new_line = "\n"
        return f"{indent}choice {{\n{f'{new_line}{indent}}} or {{{new_line}'.join(ltypes)}\n{indent}}}\n"

    def normalise(self) -> GType:
        self.branches = [gtype.normalise() for gtype in self.branches]
        return self

    def has_rec_var(self, tvar: str) -> bool:
        for id_choice in self.branches:
            if id_choice.has_rec_var(tvar):
                return True
        return False

    def __eq__(self, other):
        if not isinstance(other, GChoice):
            return False
        return self.hash(set()) == other.hash(set())

    def __hash__(self):
        return self.hash(set())

    def __str__(self) -> str:
        return self.to_string("")


class GIDChoice(GType):
    def __init__(self, branches: List[GType]):
        self.branches = branches

    def hash(self, tvars: Set[str]) -> int:
        return _hash_list(self.branches, tvars)

    def project(self, roles: Set[str]) -> Dict[str, LIDChoice]:
        branch_projections = [gtype.project(roles) for gtype in self.branches]
        return {
            role: LIDChoice(
                role,
                [proj[role] for i, proj in enumerate(branch_projections)],
                [
                    # Extract participants of first action and convert them to a set
                    set(tuple(gtype.first_actions(set()))[0].get_participants())
                    for gtype in self.branches
                ],
            )
            for role in roles
        }

    def set_rec_gtype(self, tvar: str, gtype: GType) -> None:
        for branch in self.branches:
            branch.set_rec_gtype(tvar, gtype)

    def first_actions(self, tvars: Set[str]) -> Set[GAction]:
        return set(
            action for gtype in self.branches for action in gtype.first_actions(tvars)
        )

    def to_string(self, indent: str) -> str:
        new_indent = indent + "\t"
        ltypes = [ltype.to_string(new_indent) for ltype in self.branches]
        new_line = "\n"
        return f"{indent}choice {{\n{f'{new_line}{indent}}} or {{{new_line}'.join(ltypes)}\n{indent}}}\n"

    def normalise(self) -> GType:
        self.branches = [gtype.normalise() for gtype in self.branches]
        return self

    def has_rec_var(self, tvar: str) -> bool:
        for gtype in self.branches:
            if gtype.has_rec_var(tvar):
                return True
        return False

    def __eq__(self, other: object):
        if not isinstance(other, GIDChoice):
            return False
        return self.hash(set()) == other.hash(set())

    def __hash__(self):
        return self.hash(set())

    def __str__(self) -> str:
        return super().__str__()
