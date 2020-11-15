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


def hash_ltype_list_rec(ltype_list, tvars) -> int:
    hashes = list(set(elem.hash_rec(tvars) for elem in ltype_list))
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
    def __init__(
        self,
        role: str,
        projections: List[Dict[str, LType]],
        gaction_mappings: List[Dict[str, Dict[LAction, Set[GAction]]]],
    ):
        assert len(projections) >= 1, "A choice should have at least 1 branch"
        self.role = role
        self.projections = projections
        self.branches = [projection[role] for projection in projections]
        # TODO: create map with the set of all first gactions in each branch
        self.gaction_mappings = gaction_mappings
        self.fst_actions: Optional[Set[LAction]] = None
        self.hash_value: Optional[int] = None
        self.nxt_states: Optional[Dict[LAction, Set[LType]]] = None

    def check_valid_projection(self):
        for ltype in self.branches:
            ltype.check_valid_projection()

        for i, ltype1 in enumerate(self.branches):
            for j, ltype2 in enumerate(self.branches):
                if i == j:
                    continue
                lactions1 = ltype1.first_actions_rec(set())
                lactions2 = ltype2.first_actions_rec(set())
                actions_not_in_i = lactions2.difference(lactions1)

                for action in actions_not_in_i:
                    # Check actions not dependent on common fst global action
                    self.check_action_does_not_depend_on_common_gactions(action, i, j)

                    # For any fist global action in b1 which doesn't appear in b2
                    # and where self.role doesn't participate, check 'action' cannot
                    # be carried out before gaction
                    self.check_action_in_j_cannot_be_carried_out_before_actions_in_i(
                        action, i, j
                    )

    def check_action_does_not_depend_on_common_gactions(
        self, action: LAction, b1_idx: int, b2_idx: int
    ):
        """
        action - action which we want to check
        b1 - index of branch being checked
        b2 - index of branch where 'action' is a first action for self.role
             which does not appear in b1
        """
        fst_gactions_b2 = self.gaction_mappings[b2_idx][self.role][action]
        b1_gactions = set().union(
            *tuple(self.gaction_mappings[b1_idx][self.role].values())
        )
        assert b1_gactions.isdisjoint(fst_gactions_b2), (
            f"First action from branch {b2_idx} which doesn't appear "
            f"in branch {b1_idx} should not depend on actions which aren't "
            f"common to both branches"
        )

    def check_action_in_j_cannot_be_carried_out_before_actions_in_i(
        self, action: LAction, i: int, j: int
    ):
        b1_gactions: Set[GAction] = set().union(
            *tuple(self.gaction_mappings[i][self.role].values())
        )
        b2_gactions: Set[GAction] = set().union(
            *tuple(self.gaction_mappings[j][self.role].values())
        )
        gactions = b1_gactions.difference(b2_gactions)
        gactions: Set[GAction] = {
            gaction
            for gaction in gactions
            if self.role not in gaction.get_participants()
        }

        other_role = action.get_participant()
        dual_action = action.dual()
        # Ensure trace which appears in b2 cannot happen before rp
        # choooses trace from b1
        for b1_gaction in gactions:
            if other_role in b1_gaction.get_participants():
                # Ensure action.dual() is not the first interaction
                # between other_role and self.role in the trace
                # starting with b1_gaction in b1 for other_role
                trace_action = b1_gaction.project(other_role)
                # Only need to check one trace, because trace equiv property will
                # ensure the same holds for all traces starting with the same
                # first action
                next_state: Optional[LType] = self.projections[i][
                    other_role
                ].get_next_state(trace_action, set())
                assert next_state is not None, (
                    "next state should not be none, as the trace action should "
                    "be a first global action in b1"
                )
                assert next_state.interacts_with_role_before_action(
                    self.role, dual_action, set()
                ), f"{action} should not be the first interaction between {self.role} and {other_role} in trace of {b1_gaction}"
            else:
                for b2_gaction in self.gaction_mappings[j][self.role][action]:
                    common_roles = set(b2_gaction.get_participants()).intersection(
                        set(b1_gaction.get_participants())
                    )
                    assert (
                        len(common_roles) > 0
                    ), "There should be at least one common role between gaction1 and gaction2"
                    interacts_with_self_role_before_gaction2 = False
                    for b1_role in common_roles:
                        next_state: Optional[LType] = self.projections[i][
                            b1_role
                        ].get_next_state(b1_gaction.project(b1_role), set())
                        assert next_state is not None, (
                            "next state should not be none, as the trace action should "
                            "be a first global action in b1"
                        )
                        if next_state.interacts_with_role_before_action(
                            self.role, b2_gaction.project(b1_role), set()
                        ):
                            interacts_with_self_role_before_gaction2 = True
                    assert interacts_with_self_role_before_gaction2, (
                        "At least one of the common roles in gaction1 and gaction2 needs to ensure that "
                        "gaction2 does not happen before an interaction with self.role"
                    )

        # Ensure 'action' cannot happen in b1 before rp chooses a trace from b1
        b1_gactions_wo_rp: Set[GAction] = {
            gaction
            for gaction in b1_gactions
            if self.role not in gaction.get_participants()
        }
        r2_b1_proj = self.projections[i][other_role]
        for laction in r2_b1_proj.first_actions_rec(set()):
            for gaction in self.gaction_mappings[i][other_role][laction]:
                if gaction in b1_gactions_wo_rp:
                    next_state: Optional[LType] = r2_b1_proj.get_next_state(
                        laction, set()
                    )
                    assert (
                        next_state is not None
                    ), "next state for a first action should never be none"
                    assert next_state.interacts_with_role_before_action(
                        self.role, dual_action, set()
                    ), (
                        "r2 should not be able to carry out action in b2 not present in b1 for "
                        "rp before rp chooses a trace from b1"
                    )
                    break

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

    def hash_rec(self, tvars: Set[str]) -> int:
        return hash_ltype_list_rec(self.branches, tvars)

    def normalise(self) -> LType:
        self.branches = [branch.normalise() for branch in self.branches]
        for i in range(len(self.projections)):
            self.projections[i][self.role] = self.branches[i]
        # self.check_valid_projection()
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

    def first_participants(self, tvars: Set[str]) -> Set[str]:
        return set(
            role for ltype in self.branches for role in ltype.first_participants(tvars)
        )

    def get_next_state(self, laction: LAction, tvars: Set[str]) -> Optional[LType]:
        for ltype in self.branches:
            next_state = ltype.get_next_state(laction, tvars)
            if next_state is not None:
                return next_state
        return None

    def is_first_interaction_with_role(self, laction: LAction, tvars: Set[str]) -> bool:
        for ltype in self.branches:
            if ltype.is_first_interaction_with_role(laction, tvars):
                return True
        return False

    def interacts_with_role_before_action(
        self, role: str, laction: LAction, tvars: Set[str]
    ) -> bool:
        for ltype in self.branches:
            if not ltype.interacts_with_role_before_action(role, laction, tvars):
                return False
        return True

    def set_tvar_hash(self, tvar: str, hash_value):
        for branch in self.branches:
            branch.set_tvar_hash(tvar, hash_value)

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, other):
        if not isinstance(other, LUnmergedChoice):
            return False
        return self.hash_rec(set()) == other.hash_rec(set())

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

    def first_participants(self, tvars: Set[str]) -> Set[str]:
        return set(
            role for ltype in self.branches for role in ltype.first_participants(tvars)
        )

    def first_actions_rec(self, tvars: Set[str]) -> Set[LAction]:
        return set(
            action
            for ltype in self.branches
            for action in ltype.first_actions_rec(tvars)
        )

    def set_rec_ltype(self, tvar: str, ltype):
        for branch in self.branches:
            branch.set_rec_ltype(tvar, ltype)
        self.calculate_hash = True
        self.hash_rec(set())

    def first_actions(self) -> Set[LAction]:
        pass

    def hash(self) -> int:
        if self.hash_value is None:
            self.hash_value = hash_ltype_list(self.branches)
        return self.hash_value

    def hash_rec(self, tvars: Set[str]) -> int:
        return hash_ltype_list_rec(self.branches, tvars)

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

    def is_first_interaction_with_role(self, laction: LAction, tvars: Set[str]) -> bool:
        for ltype in self.branches:
            if ltype.is_first_interaction_with_role(laction, tvars):
                return True
        return False

    def interacts_with_role_before_action(
        self, role: str, laction: LAction, tvars: Set[str]
    ) -> bool:
        for ltype in self.branches:
            if not ltype.interacts_with_role_before_action(role, laction, tvars):
                return False
        return True

    def check_valid_projection(self) -> None:
        for ltype in self.branches:
            ltype.check_valid_projection()

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, other):
        if not isinstance(other, LUnmergedChoice):
            return False
        return self.hash_rec(set()) == other.hash_rec(set())

    def __hash__(self):
        return self.hash()
