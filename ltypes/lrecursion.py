from typing import Set, Tuple, Dict, Type, cast, Optional, Any, List

import ltypes
from gtypes.gtype import GType
from ltypes.laction import LAction
from ltypes.ltype import LType


def hash_rec(rec_hash: int):
    return (hash("tvar") + rec_hash * ltypes.PRIME) % ltypes.HASH_SIZE


class LRecursion(LType):
    def __init__(self, tvar: str, ltype: LType) -> None:
        super().__init__()
        self.tvar = tvar
        self.ltype = ltype
        # self.update_hash = True
        self.ltype.set_rec_ltype(self.tvar, self)
        self.fst_actions: Optional[Set[LAction]] = None
        self.hash_value: Optional[int] = None
        self.nxt_states: Optional[Dict[LAction, Set[LType]]] = None

    def next_states_rec(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
        return self.ltype.next_states_rec(tvars)

    def next_states(self) -> Dict[LAction, Set[LType]]:
        return self.nxt_states

    def set_rec_ltype(self, tvar, gtype):
        assert tvar != self.tvar
        self.ltype.set_rec_ltype(tvar, gtype)

    def first_actions(self) -> Set[LAction]:
        return self.fst_actions

    def first_actions_rec(self, tvars: Set[str]) -> Set[LAction]:
        return self.ltype.first_actions_rec(tvars)

    def hash(self) -> int:
        # if self.update_hash:
        #     # Compute hash (forcing computation)
        #     self.update_hash = False
        #     self.hash_value = hash_rec(self.ltype.hash_rec(False))
        #     # Cache hash values for all local types in body
        return self.hash_value

    # Use string hash
    def hash_rec(self, const_tvar_hash):
        self.hash_value = hash_rec(self.ltype.hash_rec(const_tvar_hash))
        return self.hash_value

    def to_string(self, indent: str) -> str:
        next_indent = indent + "\t"
        return f"{indent}rec {self.tvar} {{\n{self.ltype.to_string(next_indent)}\n{indent}}}"

    def normalise(self) -> LType:
        if self.ltype.has_rec_var(self.tvar):
            self.flatten_recursion()
            self.ltype = self.ltype.normalise()
            return self
        return self.ltype.normalise()

    def rename_tvars(self, tvars: Set[str], new_tvar, ltype) -> Set[str]:
        return self.ltype.rename_tvars(tvars, new_tvar, ltype)

    def flatten_recursion(self):
        tvars = set()
        while isinstance(self.ltype, LRecursion):
            ltype: LRecursion = cast(LRecursion, self.ltype)
            tvars.add(ltype.tvar)
            self.ltype = ltype.ltype
        if len(tvars) > 0:
            self.ltype.rename_tvars(tvars, self.tvar, self)

    def has_rec_var(self, tvar: str) -> bool:
        return self.ltype.has_rec_var(tvar)

    def get_next_state(self, laction: LAction, tvars: Set[str]) -> Optional[Any]:
        return self.ltype.get_next_state(laction, tvars)

    def check_valid_projection(self) -> None:
        self.ltype.check_valid_projection()

    def calc_fst_actions_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        fst_actions: Dict[str, Set[LAction]],
        update_tvars: Dict[str, bool],
    ):
        tvar_deps[self.tvar] = set()
        fst_actions[self.tvar] = set()
        update_tvars[self.tvar] = True
        self.ltype.calc_fst_actions_rec(tvar_deps, fst_actions, update_tvars)
        del update_tvars[self.tvar]

    def set_fst_actions_rec(self, fst_actions: Dict[str, Set[LAction]]):
        self.fst_actions = fst_actions[self.tvar]
        self.ltype.set_fst_actions_rec(fst_actions)

    def calc_next_states_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        next_states: Dict[str, Dict[LAction, Set[LType]]],
        update_tvars: Dict[str, bool],
    ):
        tvar_deps[self.tvar] = set()
        next_states[self.tvar] = dict()
        update_tvars[self.tvar] = True
        self.ltype.calc_next_states_rec(tvar_deps, next_states, update_tvars)
        del update_tvars[self.tvar]

    def set_next_states_rec(self, next_states: Dict[str, Dict[LAction, Set[LType]]]):
        self.nxt_states = next_states[self.tvar]
        self.ltype.set_next_states_rec(next_states)

    def max_rec_depth(self, curr_rec_depth: int) -> int:
        return self.ltype.max_rec_depth(curr_rec_depth + 1)

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, LRecursion):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.hash()
