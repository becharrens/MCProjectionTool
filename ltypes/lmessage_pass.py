from typing import Set, Tuple, Dict, Optional, Any

import ltypes
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

    def first_participants(self, tvars: Set[str]) -> Set[str]:
        return set(self.action.get_participant())

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

    def hash_rec(self, tvars: Set[str]) -> int:
        return hash_msg_pass(self.action.hash(), self.cont.hash_rec(tvars))

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

    def is_first_interaction_with_role(self, laction: LAction, tvars: Set[str]) -> bool:
        if self.action == laction:
            return True
        if laction.get_participant() == self.action.get_participant():
            return False
        return self.cont.is_first_interaction_with_role(laction, tvars)

    def interacts_with_role_before_action(
        self, role: str, laction: LAction, tvars: Set[str]
    ) -> bool:
        if self.action == laction:
            return False
        if self.action.get_participant() == role:
            return True
        return self.cont.interacts_with_role_before_action(role, laction, tvars)

    def check_valid_projection(self) -> None:
        self.cont.check_valid_projection()

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, LMessagePass):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.hash()
