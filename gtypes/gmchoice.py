from typing import Dict, Set, List

import gtypes
from gtypes.gaction import GAction
from gtypes.gtype import GType
from ltypes.laction import LAction

# from ltypes.lchoice import LUnmergedChoice, LIDChoice
from ltypes.lmchoice import LUnmergedChoice
from ltypes.ltype import LType

# from unionfind.unionfind import UnionFind


def _hash_list(elem_list, tvars):
    hashes = tuple(elem.hash(tvars) for elem in elem_list)
    return sum(hashes) % gtypes.HASH_SIZE


class GChoice(GType):
    def __init__(self, choices: List[GType]) -> None:
        super().__init__()
        self.branches = choices
        self.gaction_mappings: List[Dict[str, Dict[LAction, Set[GAction]]]] = []

    def project(self, roles: Set[str]) -> Dict[str, LType]:
        self.ensure_consistent_choice()
        branch_projections = [gtype.project(roles) for gtype in self.branches]
        return {
            role: LUnmergedChoice(role, branch_projections, self.gaction_mappings)
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

    def to_string(self, indent) -> str:
        new_indent = indent + "\t"
        ltypes = [gtype.to_string(new_indent) for gtype in self.branches]
        new_line = "\n"
        return f"{indent}choice {{\n{f'{new_line}{indent}}} or {{{new_line}'.join(ltypes)}\n{indent}}}\n"

    def normalise(self) -> GType:
        self.branches = [gtype.normalise() for gtype in self.branches]
        self.build_fst_action_mapping()
        return self

    def has_rec_var(self, tvar: str) -> bool:
        for id_choice in self.branches:
            if id_choice.has_rec_var(tvar):
                return True
        return False

    def build_mapping(
        self,
        mapping: Dict[str, Dict[LAction, Set[GAction]]],
        role_mapping: Dict[str, GAction],
        tvars: Set[str],
    ):
        for gtype in self.branches:
            gtype.build_mapping(mapping, role_mapping, tvars)

    def build_fst_action_mapping(self):
        self.gaction_mappings = []
        for gtype in self.branches:
            mapping = {}
            gtype.build_mapping(mapping, {}, set())
            self.gaction_mappings.append(mapping)

    def ensure_consistent_choice(self):
        if len(self.gaction_mappings) > 0:
            roles = self.gaction_mappings[0].keys()
            for mapping in self.gaction_mappings:
                assert (
                    roles == mapping.keys()
                ), "Inconsistent Choice: All roles participating in a choice should participate in all branches"

    def __eq__(self, other):
        if not isinstance(other, GChoice):
            return False
        return self.hash(set()) == other.hash(set())

    def __hash__(self):
        return self.hash(set())

    def __str__(self) -> str:
        return self.to_string("")
