from typing import Dict, Set, List, Tuple, Optional

import gtypes
from gtypes.gaction import GAction
from gtypes.gtype import GType
from ltypes.laction import LAction

# from ltypes.lchoice import LUnmergedChoice, LIDChoice
from ltypes.lmchoice import LUnmergedChoice
from ltypes.ltype import LType

# from unionfind.unionfind import UnionFind


def _hash_list(elem_list: List[GType], tvars):
    hashes = set(elem.hash(tvars) for elem in elem_list)
    return sum(hashes) % gtypes.HASH_SIZE


class GChoice(GType):
    def __init__(self, choices: List[GType]) -> None:
        super().__init__()
        assert len(choices) >= 1, "Choice must have at least one branch"
        self.branches = choices

    def project(self, roles: Set[str]) -> Dict[str, LType]:
        branch_projections = [gtype.project(roles) for gtype in self.branches]
        return {role: LUnmergedChoice(role, branch_projections) for role in roles}

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
        norm_branches = [gtype.normalise() for gtype in self.branches]
        flattened_branches: List[GType] = []
        for gtype in norm_branches:
            # Flatten nested mixed choices
            if isinstance(gtype, GChoice):
                flattened_branches.extend(gtype.branches)
            else:
                flattened_branches.append(gtype)
        self.branches = [gtype.normalise() for gtype in self.branches]
        return self

    def has_rec_var(self, tvar: str) -> bool:
        for id_choice in self.branches:
            if id_choice.has_rec_var(tvar):
                return True
        return False

    def ensure_unique_tvars(
        self, tvar_mapping: Dict[str, str], tvar_names: Set[str], uid: int
    ):
        for branch in self.branches:
            branch.ensure_unique_tvars(tvar_mapping, tvar_names, uid)

    def ensure_consistent_payloads(
        self, payload_mapping: Dict[str, List[Tuple[Optional[str], str]]]
    ) -> None:
        for branch in self.branches:
            branch.ensure_consistent_payloads(payload_mapping)

    def __eq__(self, other):
        if not isinstance(other, GChoice):
            return False
        return self.hash(set()) == other.hash(set())

    def __hash__(self):
        return self.hash(set())

    def __str__(self) -> str:
        return self.to_string("")
