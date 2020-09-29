from typing import Set, Tuple, Dict, Any

import ltypes
from gtypes import HASH_SIZE
from ltypes.laction import LAction
from ltypes.lend import LEnd
from ltypes.ltype import LType


class LRecVar(LType):
    def __init__(self, var_name: str) -> None:
        super().__init__()
        self.tvar = var_name
        self.ltype: LType = LEnd()

    def rec_next_states(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
        if self.tvar in tvars:
            return {}
        else:
            return self.ltype.rec_next_states(tvars.union({self.tvar}))

    def next_states(self) -> Dict[LAction, Set[LType]]:
        return self.ltype.rec_next_states({self.tvar})

    def first_actions(self, tvars: Set[str]) -> Set[LAction]:
        if self.tvar in tvars:
            return set()
        return self.ltype.first_actions(tvars.union({self.tvar}))

    def first_participants(self, tvars: Set[str]) -> Set[str]:
        if self.tvar in tvars:
            return set()
        return self.ltype.first_participants(tvars.union({self.tvar}))

    def set_rec_ltype(self, tvar: str, ltype: LType):
        if tvar == self.tvar:
            self.ltype = ltype

    def hash(self, tvars: Set[str]) -> int:
        if self.tvar in tvars:
            return self.tvar.__hash__() % HASH_SIZE
        return (
            self.tvar.__hash__() * ltypes.PRIME
            + self.ltype.hash(tvars.union({self.tvar}))
        ) % HASH_SIZE

    def to_string(self, indent: str) -> str:
        return f"{indent}continue {self.tvar}"

    def normalise(self) -> LType:
        return self

    def has_rec_var(self, tvar: str) -> bool:
        return self.tvar == tvar

    def rename_tvars(self, tvars: Set[str], new_tvar: str, ltype: LType):
        if self.tvar in tvars:
            self.ltype = ltype
            self.tvar = new_tvar

    def flatten_recursion(self):
        pass

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, LRecVar):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.hash(set())
