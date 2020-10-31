# from typing import Set, List, Dict, Any
#
# import ltypes
#
#
# from errors.errors import InconsistentChoice, InvalidChoice, NotTraceEquivalent
# from ltypes.laction import LAction
# from ltypes.ltype import LType
#
#
# def hash_ltype_list(ltype_list, tvars):
#     hashes = tuple(elem.hash(tvars) for elem in ltype_list)
#     return sum(hashes) % ltypes.HASH_SIZE
#
#
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
#
#
# class LIDChoice(LType):
#     def __init__(
#         self, role: str, branches: List[LType], decision_roles: List[Set[str]]
#     ):
#         assert len(branches) >= 1, "An ID choice should have at least 1 branch"
#         assert len(branches) == len(decision_roles), "Number of branches should be equal to number of decisions"
#         self.role = role
#         self.branches = branches
#         self.decision_roles = decision_roles
#         self.common_branch_indices, self.disjoint_branch_indices, self.in_disjoint_decision_roles = (
#             self.split_branches_with_disjoint_first_decisions()
#         )
#         self.calculate_hash = True
#         self.hash_code = 0
#
#     def check_valid_id_choice(
#         self,
#         common_states: List[Dict[LAction, Set[LType]]],
#         disjoint_states: List[Dict[LAction, Set[LType]]],
#     ):
#         LIDChoice.check_consistent_choice(self.branches)
#         if LIDChoice.same_first_actions(common_states, disjoint_states):
#             return
#         if self.in_disjoint_decision_roles:
#             self.check_disjoint_decisions(common_states, disjoint_states)
#         else:
#             self.check_first_actions_involve_decision_roles(
#                 common_states, disjoint_states
#             )
#
#     def first_participants(self, tvars: Set[str]) -> Set[str]:
#         return set(
#             role for ltype in self.branches for role in ltype.first_participants(tvars)
#         )
#
#     def first_actions(self, tvars: Set[str]) -> Set[LAction]:
#         return set(
#             action for ltype in self.branches for action in ltype.first_actions(tvars)
#         )
#
#     def set_rec_ltype(self, tvar: str, ltype: LType) -> None:
#         for branch in self.branches:
#             branch.set_rec_ltype(tvar, ltype)
#         self.calculate_hash = True
#         self.hash(set())
#
#     def hash(self, tvars: Set[str]) -> int:
#         if self.calculate_hash:
#             self.hash_code = hash_ltype_list(self.branches, tvars)
#             self.calculate_hash = False
#         return self.hash_code
#
#     def normalise(self) -> LType:
#         self.branches = [branch.normalise() for branch in self.branches]
#         self.calculate_hash = True
#         self.hash(set())
#         return self
#
#     def rec_next_states(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
#         common_next_states = [
#             self.branches[idx].rec_next_states(tvars)
#             for idx in self.common_branch_indices
#         ]
#         disjoint_next_states = [
#             self.branches[idx].rec_next_states(tvars)
#             for idx in self.disjoint_branch_indices
#         ]
#         return LIDChoice.merge_next_states(common_next_states, disjoint_next_states)
#
#     def next_states(self) -> Dict[LAction, Set[LType]]:
#         common_next_states = [
#             self.branches[idx].next_states() for idx in self.common_branch_indices
#         ]
#         disjoint_next_states = [
#             self.branches[idx].next_states() for idx in self.disjoint_branch_indices
#         ]
#         self.check_valid_id_choice(common_next_states, disjoint_next_states)
#         next_states = LIDChoice.merge_next_states(
#             common_next_states, disjoint_next_states
#         )
#         return next_states
#
#     @staticmethod
#     def check_consistent_choice(branches: List[LType]):
#         all_empty = len(branches[0].first_actions(set())) == 0
#         for branch in branches:
#             num_actions = len(branch.first_actions(set()))
#             if (all_empty and num_actions > 0) or (not all_empty and num_actions == 0):
#                 raise InconsistentChoice(
#                     "A role should participate in all branches of a choice or in none"
#                 )
#
#     def split_branches_with_disjoint_first_decisions(self):
#         checked = set()
#         disjoint_branches = []
#         common_branches = []
#         participates_in_disjoint_decisions = False
#         for i in range(len(self.branches)):
#             if i not in checked:
#                 checked.add(i)
#                 decision_role_in_i = self.role in self.decision_roles[i]
#                 disjoint = False
#                 for j in range(i + 1, len(self.branches)):
#                     if j not in checked:
#                         if self.decision_roles[i].isdisjoint(self.decision_roles[j]):
#                             checked.add(j)
#                             if decision_role_in_i:
#                                 disjoint_branches.append(j)
#                                 participates_in_disjoint_decisions = True
#                             else:
#                                 disjoint = True
#                                 if self.role in self.decision_roles[j]:
#                                     common_branches.append(j)
#                                     participates_in_disjoint_decisions = True
#                                 else:
#                                     disjoint_branches.append(j)
#                 if disjoint:
#                     disjoint_branches.append(i)
#                 else:
#                     common_branches.append(i)
#
#         return common_branches, disjoint_branches, participates_in_disjoint_decisions
#
#     @staticmethod
#     def same_first_actions(
#         common_states: List[Dict[LAction, Set[LType]]],
#         disjoint_states: List[Dict[LAction, Set[LType]]],
#     ) -> bool:
#         first_actions = None
#         for states in (common_states, disjoint_states):
#             for branch_states in states:
#                 if first_actions is None:
#                     first_actions = branch_states.keys()
#                 else:
#                     if first_actions != branch_states.keys():
#                         return False
#         return True
#
#     @staticmethod
#     def _check_first_actions_involve_decision_roles(
#         states: List[Dict[LAction, Set[LType]]],
#         branch_indices: List[int],
#         all_decision_roles: List[Set[str]],
#     ):
#         for i, state in enumerate(states):
#             branch_idx = branch_indices[i]
#             decision_roles = all_decision_roles[branch_idx]
#             for action in state.keys():
#                 if action.get_participant() not in decision_roles:
#                     raise InvalidChoice(
#                         "All first actions in a branch should include one of the decision"
#                         " roles for that branch"
#                     )
#
#     def check_first_actions_involve_decision_roles(
#         self,
#         common_states: List[Dict[LAction, Set[LType]]],
#         disjoint_states: List[Dict[LAction, Set[LType]]],
#     ):
#         LIDChoice._check_first_actions_involve_decision_roles(
#             common_states, self.common_branch_indices, self.decision_roles
#         )
#         LIDChoice._check_first_actions_involve_decision_roles(
#             disjoint_states, self.disjoint_branch_indices, self.decision_roles
#         )
#
#     def get_disjoint_branch_indices(
#         self, decision_roles: Set[str], branch_indices: List[int]
#     ):
#         disjoint_indices = []
#         for branch_idx in branch_indices:
#             other_decision_roles = self.decision_roles[branch_idx]
#             if decision_roles.isdisjoint(other_decision_roles):
#                 disjoint_indices.append(branch_idx)
#         return disjoint_indices
#
#     def check_disjoint_decisions(
#         self,
#         common_states: List[Dict[LAction, Set[LType]]],
#         disjoint_states: List[Dict[LAction, Set[LType]]],
#     ):
#         LIDChoice._check_first_actions_involve_decision_roles(
#             common_states, self.common_branch_indices, self.decision_roles
#         )
#
#         common_actions = {
#             action for branch_state in common_states for action in branch_state.keys()
#         }
#         for i, state in enumerate(disjoint_states):
#             branch_idx = self.disjoint_branch_indices[i]
#             decision_roles = self.decision_roles[branch_idx]
#             disjoint_indices = self.get_disjoint_branch_indices(
#                 decision_roles, self.common_branch_indices
#             )
#             disjoint_actions = {
#                 action
#                 for idx in disjoint_indices
#                 for action in common_states[idx].keys()
#             }
#             branch_actions = state.keys()
#             if not disjoint_actions.issubset(branch_actions):
#                 raise InvalidChoice(
#                     "The actions of a disjoint branch must include all first actions"
#                     " of the branches which can happen at the same time"
#                 )
#             if not common_actions.issuperset(branch_actions):
#                 raise InvalidChoice(
#                     "The actions of a disjoint branch must be a subset of the "
#                     "branches which cannot happen in parallel"
#                 )
#
#     @staticmethod
#     def merge_next_states(
#         common_next_states: List[Dict[LAction, Set[LType]]],
#         disjoint_next_states: List[Dict[LAction, Set[LType]]],
#     ) -> Dict[LAction, Set[LType]]:
#         next_states = {}
#         common_actions = {
#             action
#             for branch_state in common_next_states
#             for action in branch_state.keys()
#         }
#
#         for action in common_actions:
#             new_state = set()
#             for state in common_next_states:
#                 if action in state:
#                     new_state |= state[action]
#             for state in disjoint_next_states:
#                 if action in state:
#                     new_state |= state[action]
#             next_states[action] = new_state
#         return next_states
#
#     def to_string(self, indent: str) -> str:
#         new_indent = indent + "\t"
#         str_ltypes = [ltype.to_string(new_indent) for ltype in self.branches]
#         new_line = "\n"
#         return f"{indent}choice {{\n{f'{new_line}{indent}}} or {{{new_line}'.join(str_ltypes)}\n{indent}}}\n"
#
#     def has_rec_var(self, tvar: str) -> bool:
#         for ltype in self.branches:
#             if ltype.has_rec_var(tvar):
#                 return True
#         return False
#
#     def rename_tvars(self, tvars: Set[str], new_tvar: str, new_ltype: LType):
#         for ltype in self.branches:
#             ltype.rename_tvars(tvars, new_tvar, new_ltype)
#         self.calculate_hash = True
#         self.hash(set())
#
#     def flatten_recursion(self):
#         for ltype in self.branches:
#             ltype.flatten_recursion()
#         self.calculate_hash = True
#         self.hash(set())
#
#     def __str__(self) -> str:
#         return self.to_string("")
#
#     def __eq__(self, other):
#         if not isinstance(other, LIDChoice):
#             return False
#         return self.hash(set()) == other.hash(set())
#
#     def __hash__(self):
#         return self.hash(set())
#
#
# class LUnmergedChoice(LType):
#     def __init__(self, choices: List[LIDChoice]) -> None:
#         self.choices = choices
#         self.hash_code = 0
#         self.calculate_hash = True
#
#     @staticmethod
#     def aggregate_next_states(
#         next_states: List[Dict[LAction, Set[LType]]]
#     ) -> Dict[LAction, Set[LType]]:
#         new_states = {}
#
#         for state in next_states:
#             for action, next_state in state.items():
#                 action_state = new_states.setdefault(action, set())
#                 action_state |= next_state
#         return new_states
#
#     def rec_next_states(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
#         # id_choice_next_states = [
#         #     id_choice.rec_next_states(tvars) for id_choice in self.choices
#         # ]
#         next_states = []
#         for id_choice in self.choices:
#             next_states.append(id_choice.rec_next_states(tvars))
#         return LUnmergedChoice.aggregate_next_states(next_states)
#
#     def next_states(self) -> Dict[LAction, Set[LType]]:
#         id_choice_next_states = [id_choice.next_states() for id_choice in self.choices]
#         return merge_next_states(id_choice_next_states)
#
#     def first_participants(self, tvars: Set[str]) -> Set[str]:
#         return set(
#             role for ltype in self.choices for role in ltype.first_participants(tvars)
#         )
#
#     def first_actions(self, tvars: Set[str]) -> Set[LAction]:
#         return set(
#             action for ltype in self.choices for action in ltype.first_actions(tvars)
#         )
#
#     def set_rec_ltype(self, tvar: str, ltype: LType) -> None:
#         for choice in self.choices:
#             choice.set_rec_ltype(tvar, ltype)
#         self.calculate_hash = True
#         self.hash(set())
#
#     def hash(self, tvars: Set[str]) -> int:
#         if self.calculate_hash:
#             self.hash_code = hash_ltype_list(self.choices, tvars)
#             self.calculate_hash = False
#         return self.hash_code
#
#     def to_string(self, indent: str) -> str:
#         new_indent = indent + "\t"
#         str_ltypes = [
#             ltype.to_string(new_indent)
#             for id_choice in self.choices
#             for ltype in id_choice.branches
#         ]
#         new_line = "\n"
#         return f"{indent}choice {{\n{f'{new_line}{indent}}} or {{{new_line}'.join(str_ltypes)}\n{indent}}}\n"
#
#     def normalise(self) -> LType:
#         self.choices = [id_choice.normalise() for id_choice in self.choices]
#         self.calculate_hash = True
#         self.hash(set())
#         return self
#
#     def has_rec_var(self, tvar: str) -> bool:
#         for id_choice in self.choices:
#             if id_choice.has_rec_var(tvar):
#                 return True
#         return False
#
#     def rename_tvars(self, tvars: Set[str], new_tvar: str, new_ltype: LType):
#         for ltype in self.choices:
#             ltype.rename_tvars(tvars, new_tvar, new_ltype)
#         self.calculate_hash = True
#         self.hash(set())
#
#     def flatten_recursion(self):
#         for ltype in self.choices:
#             ltype.flatten_recursion()
#         self.calculate_hash = True
#         self.hash(set())
#
#     def __str__(self) -> str:
#         return self.to_string("")
#
#     def __eq__(self, other):
#         if not isinstance(other, LUnmergedChoice):
#             return False
#         return self.hash(set()) == other.hash(set())
#
#     def __hash__(self):
#         return self.hash(set())
#
#
# class LChoice(LType):
#     def __init__(self, branches: List[LType]) -> None:
#         self.branches = branches
#         self.hash_code = 0
#         self.calculate_hash = True
#
#     def next_states(self) -> Dict[LAction, Set[Any]]:
#         next_states = [id_choice.next_states() for id_choice in self.branches]
#         return LChoice.aggregate_states(next_states)
#
#     def rec_next_states(self, tvars: Set[str]) -> Dict[LAction, Set[Any]]:
#         next_states = [branch.rec_next_states(tvars) for branch in self.branches]
#         return LChoice.aggregate_states(next_states)
#
#     @staticmethod
#     def aggregate_states(all_states: List[Dict[LAction, Set[LType]]]):
#         # Every branch should be carrying out a single, unique first action
#         return {
#             action: state for states in all_states for action, state in states.items()
#         }
#
#     def first_participants(self, tvars: Set[str]) -> Set[str]:
#         return set(
#             role for ltype in self.branches for role in ltype.first_participants(tvars)
#         )
#
#     def first_actions(self, tvars: Set[str]) -> Set[LAction]:
#         return set(
#             action for ltype in self.branches for action in ltype.first_actions(tvars)
#         )
#
#     def set_rec_ltype(self, tvar: str, ltype):
#         for branch in self.branches:
#             branch.set_rec_ltype(tvar, ltype)
#         self.calculate_hash = True
#         self.hash(set())
#
#     def hash(self, tvars: Set[str]) -> int:
#         if self.calculate_hash:
#             self.hash_code = hash_ltype_list(self.branches, tvars)
#             self.calculate_hash = False
#         return self.hash_code
#
#     def to_string(self, indent: str) -> str:
#         new_indent = indent + "\t"
#         str_ltypes = [ltype.to_string(new_indent) for ltype in self.branches]
#         new_line = "\n"
#         return f"{indent}choice {{\n{f'{new_line}{indent}}} or {{{new_line}'.join(str_ltypes)}\n{indent}}}"
#
#     def normalise(self) -> LType:
#         self.branches = [branch.normalise() for branch in self.branches]
#         self.calculate_hash = True
#         self.hash(set())
#         return self
#
#     def has_rec_var(self, tvar: str) -> bool:
#         for ltype in self.branches:
#             if ltype.has_rec_var(tvar):
#                 return True
#         return False
#
#     def rename_tvars(self, tvars: Set[str], new_tvar: str, new_ltype: LType):
#         for ltype in self.branches:
#             ltype.rename_tvars(tvars, new_tvar, new_ltype)
#         self.calculate_hash = True
#         self.hash(set())
#
#     def flatten_recursion(self):
#         for ltype in self.branches:
#             ltype.flatten_recursion()
#         self.calculate_hash = True
#         self.hash(set())
#
#     def __str__(self) -> str:
#         return self.to_string("")
#
#     def __eq__(self, other):
#         if not isinstance(other, LUnmergedChoice):
#             return False
#         return self.hash(set()) == other.hash(set())
#
#     def __hash__(self):
#         return self.hash(set())
