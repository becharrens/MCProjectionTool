from typing import Set, List, Dict, Any, Optional

import ltypes


from errors.errors import InconsistentChoice, InvalidChoice, NotTraceEquivalent
from gtypes.gaction import GAction
from ltypes.laction import LAction
from ltypes.ltype import LType


def hash_list(hashes: List[int]) -> int:
    res = 0
    for hv in hashes:
        res ^= hv
    return res


def hash_ltype_list_rec(ltype_list, const_tvar_hash: bool) -> int:
    hashes = list(set(elem.hash_rec(const_tvar_hash) for elem in ltype_list))
    return hash_list(hashes) % ltypes.HASH_SIZE


def hash_ltype_list(ltype_list: List[LType]) -> int:
    hashes = list(set(elem.hash() for elem in ltype_list))
    return hash_list(hashes) % ltypes.HASH_SIZE


# def merge_next_states(
#     next_states: List[Dict[LAction, Set[LType]]]
# ) -> Dict[LAction, Set[LType]]:
#     new_next_states = None
#     for transitions in next_states:
#         if new_next_states is None:
#             new_next_states = transitions
#         else:
#             if len(transitions.keys()) != len(new_next_states.keys()):
#                 raise NotTraceEquivalent(
#                     "All independent choices should have the same set of first actions"
#                 )
#             for action in new_next_states:
#                 if action not in transitions:
#                     raise NotTraceEquivalent(
#                         "All independent choices should have the same set of first actions"
#                     )
#                 new_next_states[action] |= transitions[action]
#     return new_next_states


class LUnmergedChoice(LType):
    def __init__(self, role: str, projections: List[Dict[str, LType]]):
        assert len(projections) >= 1, "A choice should have at least 1 branch"
        self.role = role
        self.projections = projections
        self.branches = [projection[role] for projection in projections]
        self.fst_actions: Optional[Set[LAction]] = None
        self.hash_value: Optional[int] = None
        self.nxt_states: Optional[Dict[LAction, Set[LType]]] = None

    def check_valid_projection(self):
        for branch in self.branches:
            branch.check_valid_projection()
        role_fst_actions = [
            {role: ltype.first_actions() for role, ltype in branch_projection.items()}
            for branch_projection in self.projections
        ]
        assert self.can_apply_two_roles_rule(
            role_fst_actions
        ) or self.can_apply_merge_rule(role_fst_actions), (
            "Cannot apply projection rules. Global type must satisfy one of the following:\n"
            " - At most one role can have a different behaviour across all branches\n "
            "- All roles have the same behaviour across branches, except possibly two, "
            "which always interact with each other first"
        )

    def can_apply_two_roles_rule(
        self, role_fst_actions: List[Dict[str, Set[LAction]]]
    ) -> bool:
        role_actions = role_fst_actions[0]
        candidates = set()
        for branch_fst_actions in role_fst_actions:
            for role, fst_actions in branch_fst_actions.items():
                if role_actions[role] != fst_actions:
                    ppts = set(action.get_participant() for action in fst_actions)
                    if len(ppts) > 1:
                        return False
                    if len(candidates) == 0:
                        other_ppt = ppts.pop()
                        candidates = {role, other_ppt}
                    elif role not in candidates:
                        return False
        return True

    def can_apply_merge_rule(
        self, role_fst_actions: List[Dict[str, Set[LAction]]]
    ) -> bool:
        role_actions = role_fst_actions[0]
        candidate = None
        for branch_fst_actions in role_fst_actions:
            for role, fst_actions in branch_fst_actions.items():
                if role_actions[role] != fst_actions:
                    if candidate is not None and candidate != role:
                        return False
                    if candidate is None:
                        candidate = role
        return True

    def first_actions(self) -> Set[LAction]:
        if self.fst_actions is None:
            self.fst_actions = self.first_actions_rec(set())
        return self.fst_actions

    def first_actions_rec(self, tvars: Set[str]) -> Set[LAction]:
        return set(
            action
            for ltype in self.branches
            for action in ltype.first_actions_rec(tvars)
        )

    def set_rec_ltype(self, tvar: str, ltype: LType) -> None:
        for branch in self.branches:
            branch.set_rec_ltype(tvar, ltype)

    def hash(self) -> int:
        if self.hash_value is None:
            self.hash_value = hash_ltype_list(self.branches)
        return self.hash_value

    def hash_rec(self, const_tvar_hash) -> int:
        return hash_ltype_list_rec(self.branches, const_tvar_hash)

    def normalise(self) -> LType:
        self.branches = [branch.normalise() for branch in self.branches]
        for i in range(len(self.projections)):
            self.projections[i][self.role] = self.branches[i]
        return self

    def next_states_rec(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
        branch_next_states = [branch.next_states_rec(tvars) for branch in self.branches]
        return LUnmergedChoice.merge_next_states(branch_next_states)

    def next_states(self) -> Dict[LAction, Set[LType]]:
        if self.nxt_states is None:
            # Calling next_states because this will cache results
            branch_next_states = [branch.next_states() for branch in self.branches]
            self.nxt_states = LUnmergedChoice.merge_next_states(branch_next_states)
        return self.nxt_states

    @staticmethod
    def same_first_actions(
        common_states: List[Dict[LAction, Set[LType]]],
        disjoint_states: List[Dict[LAction, Set[LType]]],
    ) -> bool:
        first_actions = None
        for states in (common_states, disjoint_states):
            for branch_states in states:
                if first_actions is None:
                    first_actions = branch_states.keys()
                else:
                    if first_actions != branch_states.keys():
                        return False
        return True

    @staticmethod
    def merge_next_states(
        branch_next_states: List[Dict[LAction, Set[LType]]],
    ) -> Dict[LAction, Set[LType]]:
        next_states = {}
        common_actions = {
            action
            for branch_state in branch_next_states
            for action in branch_state.keys()
        }

        for action in common_actions:
            new_state = set()
            for state in branch_next_states:
                if action in state:
                    new_state |= state[action]
            next_states[action] = new_state
        return next_states

    def to_string(self, indent: str) -> str:
        new_indent = indent + "\t"
        str_ltypes = [ltype.to_string(new_indent) for ltype in self.branches]
        new_line = "\n"
        return f"{indent}choice {{\n{f'{new_line}{indent}}} or {{{new_line}'.join(str_ltypes)}\n{indent}}}\n"

    def has_rec_var(self, tvar: str) -> bool:
        for ltype in self.branches:
            if ltype.has_rec_var(tvar):
                return True
        return False

    def rename_tvars(self, tvars: Set[str], new_tvar: str, new_ltype: LType):
        for ltype in self.branches:
            ltype.rename_tvars(tvars, new_tvar, new_ltype)

    def flatten_recursion(self):
        for ltype in self.branches:
            ltype.flatten_recursion()

    def get_next_state(self, laction: LAction, tvars: Set[str]) -> Optional[LType]:
        for ltype in self.branches:
            next_state = ltype.get_next_state(laction, tvars)
            if next_state is not None:
                return next_state
        return None

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, other):
        if not isinstance(other, LUnmergedChoice):
            return False
        return self.hash_rec(False) == other.hash_rec(False)

    def __hash__(self):
        return self.hash()


class LChoice(LType):
    def __init__(self, branches: List[LType]) -> None:
        self.branches = branches
        self.hash_value = 0

    def next_states(self) -> Dict[LAction, Set[Any]]:
        next_states = [id_choice.next_states() for id_choice in self.branches]
        return LChoice.aggregate_states(next_states)

    def next_states_rec(self, tvars: Set[str]) -> Dict[LAction, Set[Any]]:
        next_states = [branch.next_states_rec(tvars) for branch in self.branches]
        return LChoice.aggregate_states(next_states)

    @staticmethod
    def aggregate_states(all_states: List[Dict[LAction, Set[LType]]]):
        # Every branch should be carrying out a single, unique first action
        return {
            action: state for states in all_states for action, state in states.items()
        }

    def first_actions_rec(self, tvars: Set[str]) -> Set[LAction]:
        return set(
            action
            for ltype in self.branches
            for action in ltype.first_actions_rec(tvars)
        )

    def set_rec_ltype(self, tvar: str, ltype):
        for branch in self.branches:
            branch.set_rec_ltype(tvar, ltype)

    def first_actions(self) -> Set[LAction]:
        pass

    def hash(self) -> int:
        if self.hash_value is None:
            self.hash_value = hash_ltype_list(self.branches)
        return self.hash_value

    def hash_rec(self, const_tvar_hash: bool) -> int:
        return hash_ltype_list_rec(self.branches, const_tvar_hash)

    def to_string(self, indent: str) -> str:
        new_indent = indent + "\t"
        str_ltypes = [ltype.to_string(new_indent) for ltype in self.branches]
        new_line = "\n"
        return f"{indent}choice {{\n{f'{new_line}{indent}}} or {{{new_line}'.join(str_ltypes)}\n{indent}}}"

    def normalise(self) -> LType:
        self.branches = [branch.normalise() for branch in self.branches]
        return self

    def has_rec_var(self, tvar: str) -> bool:
        for ltype in self.branches:
            if ltype.has_rec_var(tvar):
                return True
        return False

    def rename_tvars(self, tvars: Set[str], new_tvar: str, new_ltype: LType):
        for ltype in self.branches:
            ltype.rename_tvars(tvars, new_tvar, new_ltype)

    def flatten_recursion(self):
        for ltype in self.branches:
            ltype.flatten_recursion()

    def get_next_state(self, laction: LAction, tvars: Set[str]) -> Optional[LType]:
        for ltype in self.branches:
            next_state = ltype.get_next_state(laction, tvars)
            if next_state is not None:
                return next_state
        return None

    def check_valid_projection(self) -> None:
        for ltype in self.branches:
            ltype.check_valid_projection()

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, other):
        if not isinstance(other, LUnmergedChoice):
            return False
        return self.hash() == other.hash()

    def __hash__(self):
        return self.hash()
