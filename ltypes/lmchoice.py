from typing import Set, List, Dict, Any, Optional, Tuple

import ltypes


from ltypes.laction import LAction
from ltypes.ltype import LType
from unionfind.unionfind import UnionFind


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
        self.ensure_consistent_choice(role_fst_actions)
        assert (
            self.can_apply_two_roles_rule(role_fst_actions)
            or self.can_apply_merge_rule(role_fst_actions)
            or self.can_apply_directed_choice_projection(role_fst_actions)
            or self.can_apply_partial_rules(role_fst_actions)
        ), (
            "Cannot apply projection rules. Global type must satisfy one of the following:\n"
            " - At most one role can have a different behaviour across all branches\n "
            " - All roles have the same behaviour across branches, except possibly two, "
            "which always interact with each other first\n"
            " - The choice must be directed: A single role must decide which branch to follow"
            " - and all the other roles must either iteract"
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

    def can_apply_partial_rules(self, role_fst_actions: List[Dict[str, Set[LAction]]]):
        all_role_fst_actions = {
            role: {
                action
                for branch_fst_actions in role_fst_actions
                for action in branch_fst_actions[role]
            }
            for role in role_fst_actions[0]
        }
        all_branches = set(range(len(role_fst_actions)))

        branches = set(all_branches)
        # Compute partition
        while branches:
            for branch in branches:
                branch_fst_actions = role_fst_actions[branch]
                roles_with_partial_behaviour = set(
                    role
                    for role in role_fst_actions[0]
                    if branch_fst_actions[role] != all_role_fst_actions[role]
                )
                if len(roles_with_partial_behaviour) == 0:
                    all_branches.remove(branch)
                    break
                if len(roles_with_partial_behaviour) > 2:
                    return False
                if len(roles_with_partial_behaviour) == 1:
                    merge_partition = self.gen_merge_partition(
                        branches,
                        role_fst_actions,
                        all_role_fst_actions,
                        next(iter(roles_with_partial_behaviour)),
                    )
                    if merge_partition is not None:
                        all_branches -= merge_partition
                        break
                if len(roles_with_partial_behaviour) >= 1:
                    # two_role_partition = self.gen_two_role_partition(
                    #     branch,
                    #     role_fst_actions,
                    #     all_role_fst_actions,
                    #     roles_with_partial_behaviour,
                    # )
                    two_role_partition = None
                    if two_role_partition is None:
                        return False
                    else:
                        all_branches -= two_role_partition
                        break
            branches = set(all_branches)
        return True

    def is_directed_choice(
        self, role_fst_actions: List[Dict[str, Set[LAction]]], role_subset: List[str]
    ):
        for role in role_subset:
            if self.is_directed_by_role(role, role_fst_actions, role_subset):
                return True
        return False

    def is_directed_by_role(
        self,
        role: str,
        role_fst_actions: List[Dict[str, Set[LAction]]],
        role_subset: List[str],
    ):
        role_actions = {r: set() for r in role_subset}
        for branch_fst_actions in role_fst_actions:
            # for role, fst_actions in branch_fst_actions.items():
            for other_role in role_subset:
                if role != other_role:
                    fst_actions = branch_fst_actions[other_role]
                    if fst_actions != role_actions[other_role]:
                        ppts = set(action.get_participant() for action in fst_actions)
                        if len(ppts) > 1 or (len(ppts) == 1 and role not in ppts):
                            return False
        return True

    def find_role_subsets_for_candidate_directed_choices(
        self, role_fst_actions: List[Dict[str, Set[LAction]]]
    ):
        roles_ufind = UnionFind()
        for branch_fst_actions in role_fst_actions:
            for role, fst_actions in branch_fst_actions.items():
                for action in fst_actions:
                    roles_ufind.add([role, action.get_participant()])
        return roles_ufind.get_subsets()

    def all_subsets_are_directed_choices(
        self,
        role_subsets: Tuple[List[str]],
        role_fst_actions: List[Dict[str, Set[LAction]]],
    ):
        for role_subset in role_subsets:
            if not self.is_directed_choice(role_fst_actions, role_subset):
                return False
        return True

    def is_valid_composition_of_directed_choices(
        self,
        role_subsets: Tuple[List[str]],
        role_fst_actions: List[Dict[str, Set[LAction]]],
    ):
        roles = tuple(role_fst_actions[0].keys())
        all_role_fst_actions = {
            role: {
                action
                for branch_fst_actions in role_fst_actions
                for action in branch_fst_actions[role]
            }
            for role in roles
        }
        for branch_fst_actions in role_fst_actions:
            for i, role_subset in enumerate(role_subsets):
                partial_traces = False
                for role in role_subset:
                    if branch_fst_actions[role] != all_role_fst_actions[role]:
                        partial_traces = True
                        break
                if partial_traces:
                    for j in range(len(role_subsets)):
                        if i != j:
                            other_role_subset = role_subsets[j]
                            for role in other_role_subset:
                                if (
                                    branch_fst_actions[role]
                                    != all_role_fst_actions[role]
                                ):
                                    return False
        return True

    def can_apply_directed_choice_projection(
        self, role_fst_actions: List[Dict[str, Set[LAction]]]
    ):
        role_subsets = self.find_role_subsets_for_candidate_directed_choices(
            role_fst_actions
        )
        if not self.all_subsets_are_directed_choices(role_subsets, role_fst_actions):
            return False
        return self.is_valid_composition_of_directed_choices(
            role_subsets, role_fst_actions
        )

    def ensure_consistent_choice(self, role_fst_actions: List[Dict[str, Set[LAction]]]):
        active_roles = set()
        inactive_roles = set()
        for branch_fst_actions in role_fst_actions:
            for role, fst_actions in branch_fst_actions.items():
                if len(fst_actions) == 0:
                    assert (
                        role not in active_roles
                    ), f"Inconsistent Choice: role {role} does not participate in all branches of the choice"
                    inactive_roles.add(role)
                else:
                    assert (
                        role not in inactive_roles
                    ), f"Inconsistent Choice: role {role} does not participate in all branches of the choice"
                    active_roles.add(role)

    def first_actions(self) -> Set[LAction]:
        if self.fst_actions is None:
            self.fst_actions = set()
            for branch in self.branches:
                self.fst_actions |= branch.first_actions()
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

    def calc_fst_actions_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        fst_actions: Dict[str, Set[LAction]],
        update_tvars: Dict[str, bool],
    ):
        for ltype in self.branches:
            ltype.calc_fst_actions_rec(tvar_deps, fst_actions, update_tvars)

    def set_fst_actions_rec(self, fst_actions: Dict[str, Set[LAction]]):
        for branch in self.branches:
            branch.set_fst_actions_rec(fst_actions)

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, other):
        if not isinstance(other, LUnmergedChoice):
            return False
        return self.hash_rec(False) == other.hash_rec(False)

    def __hash__(self):
        return self.hash()

    def gen_merge_partition(
        self,
        branches: Set[int],
        role_fst_actions: List[Dict[str, Set[LAction]]],
        all_role_fst_actions: Dict[str, Set[LAction]],
        role_with_partial_behaviour: str,
    ):
        partition = set()
        all_actions = set()
        role = role_with_partial_behaviour
        for branch in branches:
            role_actions = role_fst_actions[branch][role]
            if role_actions != all_role_fst_actions[role]:
                for r in all_role_fst_actions:
                    if (
                        r != role
                        and role_fst_actions[branch][r] != all_role_fst_actions[r]
                    ):
                        return None
                partition.add(branch)
                all_actions |= role_actions
        if all_actions != all_role_fst_actions[role]:
            return None
        return partition


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

    def calc_fst_actions_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        fst_actions: Dict[str, Set[LAction]],
        update_tvars: Dict[str, bool],
    ):
        for ltype in self.branches:
            ltype.calc_fst_actions_rec(tvar_deps, fst_actions, update_tvars)

    def set_fst_actions_rec(self, fst_actions: Dict[str, Set[LAction]]):
        for branch in self.branches:
            branch.set_fst_actions_rec(fst_actions)

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, other):
        if not isinstance(other, LUnmergedChoice):
            return False
        return self.hash() == other.hash()

    def __hash__(self):
        return self.hash()
