from typing import Set, Tuple, Dict, Optional, Any, List

import ltypes
from codegen.codegen import CodeGen
from ltypes.laction import LAction
from ltypes.ltype import LType

# continuation hash to string
# hash(str(action hash) + str(cont hash))
def hash_msg_pass(action_hash: int, cont_hash: int):
    return (action_hash + cont_hash * ltypes.PRIME) % ltypes.HASH_SIZE


class LMessagePass(LType):
    def __init__(self, action: LAction, cont: LType) -> None:
        super().__init__()
        self.action = action
        self.cont = cont
        self.hash_value: Optional[int] = None

    def next_states(self) -> Dict[LAction, Set[LType]]:
        return {self.action: {self.cont}}

    def next_states_rec(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
        return {self.action: {self.cont}}

    def first_actions(self) -> Set[LAction]:
        return {self.action}

    def first_actions_rec(self, tvars: Set[str]) -> Set[LAction]:
        return {self.action}

    def set_rec_ltype(self, tvar: str, ltype):
        self.cont.set_rec_ltype(tvar, ltype)

    def hash(self) -> int:
        if self.hash_value is None:
            self.hash_value = hash_msg_pass(self.action.hash(), self.cont.hash())
        return self.hash_value

    def hash_rec(self, const_tvar_hash: bool = False) -> int:
        return hash_msg_pass(self.action.hash(), self.cont.hash_rec(const_tvar_hash))

    def to_string(self, indent: str) -> str:
        return f"{indent}{self.action};\n{self.cont.to_string(indent)}"

    def normalise(self) -> LType:
        self.cont: LType = self.cont.normalise()
        return self

    def has_rec_var(self, tvar: str) -> bool:
        return self.cont.has_rec_var(tvar)

    def rename_tvars(self, tvars: Set[str], new_tvar, ltype):
        self.cont.rename_tvars(tvars, new_tvar, ltype)

    def flatten_recursion(self):
        self.cont.flatten_recursion()

    def get_next_state(self, laction: LAction, tvars: Set[str]) -> Optional[Any]:
        if laction == self.action:
            return self.cont
        return None

    def check_valid_projection(self) -> None:
        self.cont.check_valid_projection()

    def calc_fst_actions_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        fst_actions: Dict[str, Set[LAction]],
        update_tvars: Dict[str, bool],
    ):
        reset_values = tuple(tvar for tvar, update in update_tvars.items() if update)
        for tvar, update in tuple(update_tvars.items()):
            if update:
                fst_actions[tvar].add(self.action)
                update_tvars[tvar] = False
        self.cont.calc_fst_actions_rec(tvar_deps, fst_actions, update_tvars)
        for tvar in reset_values:
            update_tvars[tvar] = True

    def set_fst_actions_rec(self, fst_actions: Dict[str, Set[LAction]]):
        self.cont.set_fst_actions_rec(fst_actions)

    def calc_next_states_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        next_states: Dict[str, Dict[LAction, Set[LType]]],
        update_tvars: Dict[str, bool],
    ):
        reset_values = tuple(tvar for tvar, update in update_tvars.items() if update)
        for tvar, update in tuple(update_tvars.items()):
            if update:
                action_next_states = next_states[tvar].setdefault(self.action, set())
                action_next_states.add(self.cont)
                update_tvars[tvar] = False
        self.cont.calc_next_states_rec(tvar_deps, next_states, update_tvars)
        for tvar in reset_values:
            update_tvars[tvar] = True

    def set_next_states_rec(self, next_states: Dict[str, Dict[LAction, Set[LType]]]):
        self.cont.set_next_states_rec(next_states)

    def max_rec_depth(self, curr_rec_depth: int) -> int:
        return self.cont.max_rec_depth(curr_rec_depth)

    def gen_code(self, role: str, indent: str, env: CodeGen) -> str:
        cont_impl = self.cont.gen_code(role, indent, env)
        action_impl = self.action.gen_code(role, indent, env)
        return "\n".join([action_impl, cont_impl])

    def get_participant(self) -> str:
        return self.action.get_participant()

    def msg_payloads(self) -> Tuple[List[str], List[str]]:
        return self.action.get_payloads()

    def msg_label(self) -> str:
        return self.action.get_label()

    def is_send(self) -> bool:
        return self.action.is_send()

    def get_continuation(self) -> LType:
        return self.cont

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, LMessagePass):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.hash()
