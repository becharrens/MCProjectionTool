from collections import deque
from typing import Set, Dict, Any, Iterable, List, Deque

# from ltypes import lchoice
from errors.errors import NotTraceEquivalent
from ltypes import lmchoice
from ltypes.laction import LAction

# from ltypes.lchoice import merge_next_states, LUnmergedChoice, LChoice
from ltypes.lend import LEnd
from ltypes.lmchoice import LMChoice
from ltypes.lmessage_pass import LMessagePass
from ltypes.lrec_var import LRecVar
from ltypes.lrecursion import LRecursion
from ltypes.ltype import LType


def hash_state(ltypes: List[LType]):
    return lmchoice.hash_ltype_list(ltypes)


def merge_next_states(
    next_states: List[Dict[LAction, Set[LType]]]
) -> Dict[LAction, Set[LType]]:
    new_next_states = None
    for transitions in next_states:
        if new_next_states is None:
            new_next_states = transitions
        else:
            if len(transitions.keys()) != len(new_next_states.keys()):
                raise NotTraceEquivalent(
                    "All local types should have the same set of first actions"
                )
            for action in new_next_states:
                if action not in transitions:
                    raise NotTraceEquivalent(
                        "All ltypes should have the same set of first actions"
                    )
                new_next_states[action] |= transitions[action]
    return new_next_states


class DFAState:
    state_id = 0

    def __init__(self, ltypes: List[LType]) -> None:
        self.ltypes = ltypes
        # If the transitions can be merged, it means all local types have the same first actions
        self.transitions = merge_next_states(
            [ltype.next_states() for ltype in self.ltypes]
        )
        self.uid = DFAState.state_id
        DFAState.state_id += 1
        self.hash_value = hash_state(self.ltypes)

    def hash(self):
        return self.hash_value

    def __hash__(self):
        return self.hash_value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DFAState):
            return False
        return self.__hash__() == other.__hash__()

    def __str__(self) -> str:
        return f"({self.uid})"
        # join_str = ",\n"
        # tab = "\t"
        # return f"(\n{join_str.join((ltype.to_string(tab) for ltype in self.ltypes))}\n)"

    def __repr__(self) -> str:
        return str(self)


class DFA:
    def __init__(self, ltype: LType) -> None:
        self.ltype = ltype
        self.tvar_id = 0
        self.rec_variables: Dict[int, str] = {}
        self.transitions: Dict[DFAState, Dict[LAction, DFAState]] = {}

    def translate(self) -> LType:
        queue: Deque[DFAState] = deque()

        start = DFAState([self.ltype])
        queue.append(start)
        all_states: Dict[int, DFAState] = {start.hash(): start}

        self.transitions: Dict[DFAState, Dict[LAction, DFAState]] = {start: {}}

        while queue:
            current = queue.popleft()
            curr_transitions = {}
            for action, next_state in current.transitions.items():
                next_state_list = list(next_state)
                state_hash = hash_state(next_state_list)

                if state_hash not in all_states:
                    new_state = DFAState(next_state_list)
                    all_states[state_hash] = new_state
                    curr_transitions[action] = new_state
                    queue.append(new_state)
                else:
                    curr_transitions[action] = all_states[state_hash]
            self.transitions[current] = curr_transitions

        return self.dfa_to_ltype(start, set()).normalise()

    def rec_var_name(self, state: DFAState) -> str:
        # hash_code = state.hash
        # if hash_code in self.rec_variables:
        #     return f"t{self.rec_variables[hash_code]}"
        #
        # self.rec_variables[hash_code] = self.tvar_id
        # rec_var = f"t{self.tvar_id}"
        #
        # self.tvar_id += 1
        # return rec_var

        hash_code = state.hash
        if hash_code not in self.rec_variables:
            self.rec_variables[hash_code] = f"t{self.tvar_id}"
            self.tvar_id += 1

        return self.rec_variables[hash_code]

    def dfa_to_ltype(self, state: DFAState, visited: Set[DFAState]) -> LType:
        if state in visited:
            return LRecVar(self.rec_var_name(state))

        visited.add(state)

        curr = LEnd()
        branches = []
        for action, next_state in self.transitions[state].items():
            cont = self.dfa_to_ltype(next_state, visited)
            branches.append(LMessagePass(action, cont))
        if len(branches) == 1:
            curr = branches[0]
        elif len(branches) > 1:
            curr = LMChoice(branches)

        if self.is_recursive(state, state, set()):
            # if self.is_recursive1(state):
            curr = LRecursion(self.rec_var_name(state), curr)

        visited.remove(state)

        return curr

    # def is_recursive2(self, state: DFAState, visited: Set[DFAState]):
    #     if state in visited:
    #         return
    #
    #     visited.add(state)
    #
    #     for next_state in self.transitions[state].values():
    #         if self.is_recursive2(next_state, visited):
    #             return
    #
    #     return
    #
    # def is_recursive1(self, state: DFAState):
    #     visited = set()
    #     for next_state in self.transitions[state].values():
    #         self.is_recursive2(next_state, visited)
    #
    #     return state in visited

    def is_recursive(self, state: DFAState, target: DFAState, visited: Set[DFAState]):
        if state in visited:
            return False

        visited.add(state)

        for next_state in self.transitions[state].values():
            if next_state == target or self.is_recursive(next_state, target, visited):
                return True

        return False

    @staticmethod
    def transition_to_str(start: DFAState, action: LAction, end: DFAState):
        return f"[{start}\n- {action} ->\n{end}]"

    def __str__(self) -> str:
        return "\n,\n".join(
            (
                DFA.transition_to_str(start, action, target)
                for start, transitions in self.transitions.items()
                for action, target in transitions.items()
            )
        )

    def __repr__(self) -> str:
        return str(self)
