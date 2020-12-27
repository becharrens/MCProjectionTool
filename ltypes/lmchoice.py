import itertools
from abc import abstractmethod, ABC
from typing import Set, List, Dict, Optional, Tuple, Iterable, Any, cast, FrozenSet

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


def two_communicating_roles(
    actions: Dict[str, Set[LAction]], leaders: Set[str]
) -> bool:
    l1, l2 = tuple(leaders)
    l1_ppts = {action.get_participant() for action in actions[l1]}
    l2_ppts = {action.get_participant() for action in actions[l2]}
    return l1_ppts == {l2} and l2_ppts == {l1}


def all_actions_in_partition(
    p: FrozenSet[int], branches: Dict[str, List[LType]]
) -> Tuple[Set[str], Dict[str, Set[LAction]]]:
    all_actions = {}
    leaders: Set[str] = set()
    for role, ltypes in branches.items():
        actions = set()
        for idx in p:
            first_actions = ltypes[idx].first_actions()
            not_equal_actions = actions and first_actions != actions
            if not actions or not_equal_actions:
                actions = actions.union(first_actions)
            if not_equal_actions:
                leaders.add(role)
        all_actions[role] = actions
    return leaders, all_actions


def proj_condition(leaders: Set[str], actions: Dict[str, Set[LAction]]) -> bool:
    num_leaders = len(leaders)
    if num_leaders < 2:
        return True
    if num_leaders == 2:
        return two_communicating_roles(actions, leaders)


def can_be_merged(
    p1: FrozenSet[int], p2: FrozenSet[int], branches: Dict[str, List[LType]]
) -> Tuple[bool, Set[str], Dict[str, Set[LAction]], Set[str], Dict[str, Set[LAction]]]:
    p1_leaders, p1_actions = all_actions_in_partition(p1, branches)
    p2_leaders, p2_actions = all_actions_in_partition(p2, branches)

    diff_roles = set()
    for role, actions in p1_actions.items():
        if actions != p2_actions[role]:
            diff_roles.add(role)
            if len(diff_roles) == 2:
                r1, r2 = tuple(diff_roles)
                r1_actions = p1_actions[r1].union(p2_actions[r1])
                r2_actions = p1_actions[r2].union(p2_actions[r2])
                r1_ppts = {action.get_participant() for action in r1_actions}
                r2_ppts = {action.get_participant() for action in r2_actions}
                if not (r1_ppts == {r2} and r2_ppts == {r1}):
                    return False, p1_leaders, p1_actions, p2_leaders, p2_actions
            elif len(diff_roles) > 2:
                return False, p1_leaders, p1_actions, p2_leaders, p2_actions

    return True, p1_leaders, p1_actions, p2_leaders, p2_actions


class AbsPartition(ABC):
    @abstractmethod
    def is_valid(self, computed_partitions: Dict[Any, bool]):
        pass

    @abstractmethod
    def satisfies_proj_property(self) -> bool:
        pass

    @abstractmethod
    def partitions(self) -> Iterable:
        pass


class Partition(AbsPartition):
    def __init__(
        self,
        branches: Dict[str, List[LType]],
        indices: FrozenSet[int],
        role_actions: Dict[str, Set[LAction]],
        leaders: Set[str],
    ):
        self.branches = branches
        self.indices = indices
        self.can_be_projected = proj_condition(leaders, role_actions)

    def satisfies_proj_property(self):
        return self.can_be_projected

    def partitions(self) -> Iterable[Tuple[AbsPartition, AbsPartition]]:
        idx_list = list(self.indices)
        n = len(self.indices)
        first_iter = True
        for partition in itertools.product([False, True], repeat=n - 1):
            if first_iter:
                # Ignore partition 0,0, ... ,0
                first_iter = False
                continue
            p1 = frozenset.union(
                frozenset(
                    idx_list[i + 1] for i, in_p2 in enumerate(partition) if not in_p2
                ),
                frozenset((idx_list[0],)),
            )

            p2 = frozenset(
                idx_list[i + 1] for i, in_p2 in enumerate(partition) if in_p2
            )

            can_merge, p1_leaders, p1_actions, p2_leaders, p2_actions = can_be_merged(
                p1, p2, self.branches
            )
            if can_merge:
                partition1 = Partition(self.branches, p1, p1_actions, p1_leaders)
                partition2 = Partition(self.branches, p2, p2_actions, p2_leaders)
                yield partition1, partition2
        return

    def is_valid(self, computed_partitions: Dict[AbsPartition, bool]) -> bool:
        if self in computed_partitions:
            return computed_partitions[self]

        if self.satisfies_proj_property():
            computed_partitions[self] = True
            return True

        for p1, p2 in self.partitions():
            if p1.is_valid(computed_partitions) and p2.is_valid(computed_partitions):
                computed_partitions[self] = True
                return True
        computed_partitions[self] = False
        return False

    def __hash__(self) -> int:
        return self.indices.__hash__()

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Partition):
            return False

        return o.indices == self.indices


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
            # or self.can_apply_directed_choice_projection(role_fst_actions)
            # or self.can_apply_partial_rules(role_fst_actions)
            or self.can_apply_partition_projection()
            # self.can_apply_interleavings_rule()
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
        all_fst_actions = self.get_all_fst_actions(role_fst_actions)
        same_behaviour_roles = {
            role
            for role, fst_actions in all_fst_actions.items()
            if self.same_behaviour_role(role, role_fst_actions, fst_actions)
        }
        if len(same_behaviour_roles) == len(all_fst_actions):
            return True
        if len(same_behaviour_roles) != len(all_fst_actions) - 2:
            return False
        to_consider = set(all_fst_actions.keys()).difference(same_behaviour_roles)
        r1, r2 = tuple(to_consider)
        r1_ppts = self.action_participants(all_fst_actions[r1])
        r2_ppts = self.action_participants(all_fst_actions[r2])
        if len(r1_ppts) != 1 or next(iter(r1_ppts)) != r2:
            return False
        return len(r2_ppts) == 1 and next(iter(r2_ppts)) == r1
        # for role in to_consider:
        #     fst_actions = all_fst_actions[role]
        #     if role not in candidates:
        #         ppts = self.action_participants(fst_actions)
        #         if len(ppts) == 1:
        #             other_role = next(iter(ppts))
        #             other_ppts = self.action_participants(all_fst_actions[other_role])
        #             if len(other_ppts) == 1 and role == next(iter(other_ppts)):
        #                 candidates.add(role)
        #                 candidates.add(other_role)
        # There should be at most two roles
        # if len(candidates) > 2:
        #     return False
        # Check that all roles either have the same behaviour across branches
        # or only depend on one of the candidate roles
        # valid_roles = same_behaviour_roles.union(candidates)
        # for role in set(all_fst_actions.keys()).difference(valid_roles):
        #     ppts = self.action_participants(all_fst_actions[role])
        #     if len(ppts) != 1 or next(iter(ppts)) not in candidates:
        #         return False
        #     valid_roles.add(role)
        #     break
        # Only the two candidates can can different behaviours
        # return True

    def can_apply_merge_rule(
        self, role_fst_actions: List[Dict[str, Set[LAction]]]
    ) -> bool:
        all_fst_actions = self.get_all_fst_actions(role_fst_actions)
        same_behaviour_roles = {
            role
            for role, fst_actions in all_fst_actions.items()
            if self.same_behaviour_role(role, role_fst_actions, fst_actions)
        }
        if len(same_behaviour_roles) == len(all_fst_actions):
            return True
        return len(same_behaviour_roles) == len(all_fst_actions) - 1

    # def can_apply_partial_rules(self, role_fst_actions: List[Dict[str, Set[LAction]]]):
    #     all_role_fst_actions = {
    #         role: {
    #             action
    #             for branch_fst_actions in role_fst_actions
    #             for action in branch_fst_actions[role]
    #         }
    #         for role in role_fst_actions[0]
    #     }
    #     all_branches = set(range(len(role_fst_actions)))
    #
    #     branches = set(all_branches)
    #     # Compute partition
    #     while branches:
    #         for branch in branches:
    #             branch_fst_actions = role_fst_actions[branch]
    #             roles_with_partial_behaviour = set(
    #                 role
    #                 for role in role_fst_actions[0]
    #                 if branch_fst_actions[role] != all_role_fst_actions[role]
    #             )
    #             if len(roles_with_partial_behaviour) == 0:
    #                 all_branches.remove(branch)
    #                 break
    #             if len(roles_with_partial_behaviour) > 2:
    #                 return False
    #             if len(roles_with_partial_behaviour) == 1:
    #                 merge_partition = self.gen_merge_partition(
    #                     branches,
    #                     role_fst_actions,
    #                     all_role_fst_actions,
    #                     next(iter(roles_with_partial_behaviour)),
    #                 )
    #                 if merge_partition is not None:
    #                     all_branches -= merge_partition
    #                     break
    #             if len(roles_with_partial_behaviour) >= 1:
    #                 # two_role_partition = self.gen_two_role_partition(
    #                 #     branch,
    #                 #     role_fst_actions,
    #                 #     all_role_fst_actions,
    #                 #     roles_with_partial_behaviour,
    #                 # )
    #                 two_role_partition = None
    #                 if two_role_partition is None:
    #                     return False
    #                 else:
    #                     all_branches -= two_role_partition
    #                     break
    #         branches = set(all_branches)
    #     return True

    def can_apply_partial_rules(self, role_fst_actions: List[Dict[str, Set[LAction]]]):
        """ Can partition branches to apply merge rule """
        all_role_fst_actions = self.get_all_fst_actions(role_fst_actions)
        all_branches = set(range(len(role_fst_actions)))

        return self.can_partition_branches(
            all_branches,
            set(all_role_fst_actions.keys()),
            all_role_fst_actions,
            role_fst_actions,
        )

    def can_partition_branches(
        self,
        branches: Set[int],
        candidate_roles: Set[str],
        all_role_fst_actions: Dict[str, Set[LAction]],
        role_fst_actions: List[Dict[str, Set[LAction]]],
    ):
        # Check if all roles can perform all behaviours in all branches
        # (the partition is valid without partitioning on any particular role)
        if self.is_valid_partition(
            all_role_fst_actions, branches, None, role_fst_actions
        ):
            # If branches is empty function will return true
            return True

        candidates = set(candidate_roles)
        for role in candidate_roles:
            all_fst_actions = {
                action
                for branch in branches
                for action in role_fst_actions[branch][role]
            }
            # Can role still perform all its fst actions
            if all_role_fst_actions[role] != all_fst_actions:
                return False
            # If role has full behaviour across all branches, cannot partition
            # based on role
            same_behaviour = True
            for branch in branches:
                if role_fst_actions[branch][role] != all_fst_actions:
                    same_behaviour = False
                    break
            if same_behaviour:
                candidates.remove(role)
                continue
            # Gen partition
            partition = {
                branch
                for branch in branches
                if role_fst_actions[branch][role] != all_role_fst_actions[role]
            }
            # Ensure all other roles can perform all their actions in all branches
            if not self.is_valid_partition(
                all_role_fst_actions, partition, role, role_fst_actions
            ):
                continue
            # Check this role performs all its actions in partition
            partition_fst_actions = {
                action
                for branch in partition
                for action in role_fst_actions[branch][role]
            }
            if partition_fst_actions != all_role_fst_actions[role]:
                continue
            other_branches = branches.difference(partition)
            candidates.remove(role)
            can_partition = self.can_partition_branches(
                other_branches, candidates, all_role_fst_actions, role_fst_actions
            )
            if can_partition:
                return True
            candidates.add(role)
        return False

    def is_valid_partition(
        self, all_role_fst_actions, partition, role, role_fst_actions
    ):
        for b in partition:
            for r in all_role_fst_actions:
                if r != role and role_fst_actions[b][r] != all_role_fst_actions[r]:
                    return False
        return True

    def get_all_fst_actions(self, role_fst_actions) -> Dict[str, Set[LAction]]:
        return {
            role: {
                action
                for branch_fst_actions in role_fst_actions
                for action in branch_fst_actions[role]
            }
            for role in role_fst_actions[0]
        }

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
        all_fst_actions = self.get_all_fst_actions(role_fst_actions)
        same_behaviour_roles = {
            role
            for role in role_subset
            if self.same_behaviour_role(role, role_fst_actions, all_fst_actions[role])
        }
        # All roles which don't have the same behaviour across branches must depend on role
        for r in role_subset:
            if r not in same_behaviour_roles and r != role:
                fst_actions = all_fst_actions[r]
                ppts = self.action_participants(fst_actions)
                if len(ppts) != 1 or role not in ppts:
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
                # return True
                return True
        return True

    def is_valid_composition_of_directed_choices(
        self,
        role_subsets: Tuple[List[str]],
        role_fst_actions: List[Dict[str, Set[LAction]]],
    ):
        all_role_fst_actions = self.get_all_fst_actions(role_fst_actions)
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

    # def clasify_roles(
    #     self,
    #     role_fst_actions: List[Dict[str, Set[LAction]]],
    #     all_fst_actions: Dict[str, Set[LAction]],
    # ) -> Dict[str, Set[LAction]]:
    #     same_behaviour_roles = {
    #         role
    #         for role, fst_actions in all_fst_actions.items()
    #         if self.same_behaviour_role(role, role_fst_actions, fst_actions)
    #     }
    #
    #     # Map every directed role to the role with which it interacts
    #     # If two roles interact with each other and one has the same behaviour across
    #     # all branches, so will the other.
    #     # Also, with the trace equivalence restriction, if a role interacts first with
    #     # a role which has the same behaviour across all branches, this role should
    #     # also have the same behaviour across all branches.
    #     directed_behaviour_roles = {
    #         role: next(iter(self.action_participants(fst_actions)))
    #         for role, fst_actions in all_fst_actions.items()
    #         if role not in same_behaviour_roles
    #         and self.directed_behaviour_role(fst_actions)
    #     }
    #
    #     roles_to_verify = {
    #         role: fst_actions
    #         for role, fst_actions in all_fst_actions.items()
    #         if role not in same_behaviour_roles
    #         and (
    #             role not in directed_behaviour_roles
    #             or directed_behaviour_roles[role] in directed_behaviour_roles
    #         )
    #     }
    #
    #     return roles_to_verify

    # def create_action_mapping(
    #     self, role_fst_actions: List[Dict[str, Set[LAction]]]
    # ) -> Dict[str, Dict[LAction, Set[int]]]:
    #     branch_mapping = {}
    #     for i, proj_fst_actions in enumerate(role_fst_actions):
    #         for role, fst_actions in proj_fst_actions.items():
    #             role_action_mapping: Dict[
    #                 LAction, Set[int]
    #             ] = branch_mapping.setdefault(role, dict())
    #             for action in fst_actions:
    #                 action_branches: Set[int] = role_action_mapping.setdefault(
    #                     action, set()
    #                 )
    #                 action_branches.add(i)
    #
    #     return branch_mapping

    # def can_apply_interleavings_rule(self):
    # ERROR: DOES NOT WORK!!!

    #     role_fst_actions = [
    #         {role: ltype.first_actions() for role, ltype in branch_projection.items()}
    #         for branch_projection in self.projections
    #     ]
    #     all_fst_actions = self.get_all_fst_actions(role_fst_actions)
    #     roles_to_verify = self.clasify_roles(role_fst_actions, all_fst_actions)
    #     if len(roles_to_verify) < 3:
    #         return True
    #     role_order = tuple(roles_to_verify.keys())
    #     roles = {role: idx for idx, role in enumerate(role_order)}
    #     role_actions = tuple(roles_to_verify[role] for role in role_order)
    #     action_branch_mapping = self.create_action_mapping(role_fst_actions)
    #
    #     for action_combination in itertools.product(*role_actions, repeat=1):
    #         is_valid_combination = True
    #
    #         for idx, action in enumerate(action_combination):
    #             participant = action.get_participant()
    #             if participant in roles_to_verify:
    #                 participant_idx = roles[participant]
    #                 ppt_action = action_combination[participant_idx]
    #                 # It is not possible for two roles to perform first actions which involve each other
    #                 # when the actions are not duals of one another
    #                 if (
    #                     ppt_action.get_participant() == role_order[idx]
    #                     and ppt_action.dual() != action
    #                 ):
    #                     is_valid_combination = False
    #                     break
    #         if is_valid_combination:
    #             common_branches = set(range(len(role_fst_actions)))
    #             for idx, action in enumerate(action_combination):
    #                 role = role_order[idx]
    #                 common_branches &= action_branch_mapping[role][action]
    #                 if len(common_branches) == 0:
    #                     return False
    #     return True

    def can_apply_partition_projection(self):
        partition_indices = frozenset(range(len(self.branches)))
        choice_proj: Dict[str, List[LType]] = cast(Dict[str, List[LType]], dict())
        for projections in self.projections:
            for role, projection in projections.items():
                proj = choice_proj.setdefault(role, [])
                proj.append(projection)
        leaders, all_fst_actions = all_actions_in_partition(
            partition_indices, choice_proj
        )
        partition = Partition(choice_proj, partition_indices, all_fst_actions, leaders)
        return partition.is_valid(dict())

    def action_participants(self, local_actions: Set[LAction]) -> Set[str]:
        return {action.get_participant() for action in local_actions}

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

    def same_behaviour_role(
        self,
        role: str,
        role_fst_actions: List[Dict[str, Set[LAction]]],
        fst_actions: Set[LAction],
    ):
        for branch_fst_actions in role_fst_actions:
            if fst_actions != branch_fst_actions[role]:
                return False
        return True

    def directed_behaviour_role(self, role_fst_actions):
        return len(self.action_participants(role_fst_actions)) == 1

    def calc_next_states_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        next_states: Dict[str, Dict[LAction, Set[LType]]],
        update_tvars: Dict[str, bool],
    ):
        for ltype in self.branches:
            ltype.calc_next_states_rec(tvar_deps, next_states, update_tvars)

    def set_next_states_rec(self, next_states: Dict[str, Dict[LAction, Set[LType]]]):
        for ltype in self.branches:
            ltype.set_next_states_rec(next_states)

    def max_rec_depth(self, curr_rec_depth: int) -> int:
        return max(branch.max_rec_depth(curr_rec_depth) for branch in self.branches)

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

    def next_states(self) -> Dict[LAction, Set[LType]]:
        next_states = [id_choice.next_states() for id_choice in self.branches]
        return LChoice.aggregate_states(next_states)

    def next_states_rec(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
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

    def calc_next_states_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        next_states: Dict[str, Dict[LAction, Set[LType]]],
        update_tvars: Dict[str, bool],
    ):
        for ltype in self.branches:
            ltype.calc_next_states_rec(tvar_deps, next_states, update_tvars)

    def set_next_states_rec(self, next_states: Dict[str, Dict[LAction, Set[LType]]]):
        for ltype in self.branches:
            ltype.set_next_states_rec(next_states)

    def max_rec_depth(self, curr_rec_depth: int) -> int:
        return max(branch.max_rec_depth(curr_rec_depth) for branch in self.branches)

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, other):
        if not isinstance(other, LUnmergedChoice):
            return False
        return self.hash() == other.hash()

    def __hash__(self):
        return self.hash()

    # def check_nc_choice(role_fst_actions: List[Dict[str, Set[LAction]]]):
    #     all_fst_actions: Dict[str, Set[LAction]] = {
    #         role: {
    #             action
    #             for branch_fst_actions in role_fst_actions
    #             for action in branch_fst_actions[role]
    #         }
    #         for role in role_fst_actions[0]
    #     }
    # other_roles = {"processing": "routing", "routing": "processing"}
    # common_actions = {
    #     r1: {
    #         action
    #         for action in all_fst_actions[r1]
    #         if action.dual() in all_fst_actions[other_roles[r1]]
    #     }
    #     for r1 in other_roles
    # }
    # # Check actions which are not common to both roles
    # for role in other_roles:
    #     for action in all_fst_actions[role]:
    #         if action not in common_actions[role]:
    #             for other_action in all_fst_actions[other_roles[role]]:
    #                 # if other_action.get_participant() != role:
    #                 found_branch = False
    #                 for branch_fst_actions in role_fst_actions:
    #                     if (
    #                         action in branch_fst_actions[role]
    #                         and other_action in branch_fst_actions[other_roles[role]]
    #                     ):
    #                         found_branch = True
    #                         break
    #                 if not found_branch:
    #                     return False
    # # Check common actions
    # for r, common_fst_actions in common_actions.items():
    #     for action in common_fst_actions:
    #         found_branch = False
    #         for branch_fst_actions in role_fst_actions:
    #             r1_fst_actions = branch_fst_actions[r]
    #             r2_fst_actions = branch_fst_actions[other_roles[r]]
    #             if (
    #                 action in r1_fst_actions
    #                 and action.dual() in r2_fst_actions
    #                 and len(r1_fst_actions) == 1
    #                 and len(r2_fst_actions) == 1
    #             ):
    #                 found_branch = True
    #                 break
    #         if not found_branch:
    #             return False
    #     break
    # for action in all_fst_actions["processing"]:
    #     for action2 in all_fst_actions["routing"]:
    #         found_branch = False
    #         if (
    #             action.get_participant() == "routing"
    #             and action2.get_participant() == "processing"
    #             and action.dual() != action2
    #         ):
    #             continue
    #         for branch_fst_actions in role_fst_actions:
    #             r1_fst_actions = branch_fst_actions["processing"]
    #             r2_fst_actions = branch_fst_actions["routing"]
    #             if action in r1_fst_actions and action2 in r2_fst_actions:
    #                 if action.dual() != action2 or (
    #                     action.dual() == action2
    #                     and len(r1_fst_actions) == 1
    #                     and len(r2_fst_actions) == 1
    #                 ):
    #                     found_branch = True
    #                     break
    #         if not found_branch:
    #             return False
    # return True
