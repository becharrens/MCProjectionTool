from typing import Set, Tuple, Dict, Any, Optional, List

import ltypes
from codegen.codegen import CodeGen
from codegen.namegen import NameGen
from gtypes import HASH_SIZE
from ltypes.laction import LAction
from ltypes.lend import LEnd
from ltypes.ltype import LType


class LRecVar(LType):
    def __init__(self, var_name: str) -> None:
        super().__init__()
        self.tvar = var_name
        self.ltype: LType = LEnd()
        # self.fst_actions: Optional[Set[LAction]] = None
        # self.hash_value: Optional[int] = None
        # self.nxt_states: Optional[Dict[LAction, Set[LType]]] = None

    def next_states_rec(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
        if self.tvar in tvars:
            return {}
        else:
            return self.ltype.next_states_rec(tvars.union({self.tvar}))

    def next_states(self) -> Dict[LAction, Set[LType]]:
        return self.ltype.next_states()

    def first_actions(self) -> Set[LAction]:
        return self.ltype.first_actions()

    def first_actions_rec(self, tvars: Set[str]) -> Set[LAction]:
        if self.tvar in tvars:
            return set()
        return self.ltype.first_actions_rec(tvars.union({self.tvar}))

    def set_rec_ltype(self, tvar: str, ltype: LType):
        if tvar == self.tvar:
            self.ltype = ltype

    def hash(self) -> int:
        # ltype should be LRecursion, which should have computed
        # its hash already
        return self.ltype.hash()

    def hash_rec(self, const_tvar_hash: bool = False) -> int:
        if const_tvar_hash:
            return hash("tvar") % HASH_SIZE
        return self.hash()

    def to_string(self, indent: str) -> str:
        return f"{indent}continue {self.tvar};"

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

    def get_next_state(self, laction: LAction, tvars: Set[str]) -> Optional[Any]:
        if self.tvar in tvars:
            return None
        return self.ltype.get_next_state(laction, tvars.union({self.tvar}))

    def check_valid_projection(self) -> None:
        return

    def calc_fst_actions_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        fst_actions: Dict[str, Set[LAction]],
        update_tvars: Dict[str, bool],
    ):
        for tvar, update in tuple(update_tvars.items()):
            if update:
                tvar_deps[tvar].add(self.tvar)

    def set_fst_actions_rec(self, fst_actions: Dict[str, Set[LAction]]):
        pass

    def calc_next_states_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        next_states: Dict[str, Dict[LAction, Set[LAction]]],
        update_tvars: Dict[str, bool],
    ):
        for tvar, update in tuple(update_tvars.items()):
            if update:
                tvar_deps[tvar].add(self.tvar)

    def set_next_states_rec(self, next_states: Dict[str, Dict[LAction, Set[LAction]]]):
        pass

    def max_rec_depth(self, curr_rec_depth: int) -> int:
        return curr_rec_depth

    def gen_code(self, role: str, indent: str, env: CodeGen) -> str:
        impl = CodeGen.continue_stmt(self.tvar)
        return CodeGen.indent_line(indent, impl)

    def ensure_unique_tvars(self, tvar_mapping: Dict[str, str], namegen: NameGen):
        self.tvar = tvar_mapping[self.tvar]

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, LRecVar):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.hash()
