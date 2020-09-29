from typing import Set, Tuple, Dict

import ltypes
from ltypes.laction import LAction
from ltypes.ltype import LType


class LMessagePass(LType):
    def __init__(self, action: LAction, cont: LType) -> None:
        super().__init__()
        self.action = action
        self.cont = cont

    def rec_next_states(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
        return {self.action: {self.cont}}

    def next_states(self) -> Dict[LAction, Set[LType]]:
        return {self.action: {self.cont}}

    def first_participants(self, tvars: Set[str]) -> Set[str]:
        return set(self.action.get_participant())

    def first_actions(self, tvars: Set[str]) -> Set[LAction]:
        return {self.action}

    def set_rec_ltype(self, tvar: str, ltype):
        self.cont.set_rec_ltype(tvar, ltype)

    def hash(self, tvars: Set[str]) -> int:
        return (
            self.action.__hash__() * ltypes.PRIME + self.cont.hash(tvars)
        ) % ltypes.HASH_SIZE

    def to_string(self, indent: str) -> str:
        return f"{indent}{self.action};\n{self.cont.to_string(indent)}"

    def normalise(self) -> LType:
        self.cont: LType = self.cont.normalise()
        return self

    def has_rec_var(self, tvar: str) -> bool:
        return self.cont.has_rec_var(tvar)

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, LMessagePass):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.hash(set())
