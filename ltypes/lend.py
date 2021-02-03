from typing import Set, Dict, Tuple, Any, Optional, List

from codegen.codegen import CodeGen, ENV
from codegen.namegen import NameGen
from ltypes.laction import LAction
from ltypes.ltype import LType


class LEnd(LType):
    def first_actions(self) -> Set[LAction]:
        return set()

    def first_actions_rec(self, tvars: Set[str]) -> Set[LAction]:
        return set()

    def set_rec_ltype(self, tvar: str, ltype):
        pass

    def hash(self) -> int:
        return 0

    def hash_rec(self, const_tvar_hash: bool = False) -> int:
        return 0

    def next_states_rec(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
        return {}

    def next_states(self) -> Dict[LAction, Set[LType]]:
        return {}

    def to_string(self, indent: str) -> str:
        return f"{indent}end"

    def normalise(self) -> LType:
        return self

    def has_rec_var(self, tvar: str) -> bool:
        return False

    def rename_tvars(self, tvars: Set[str], new_tvar: str, ltype: LType):
        pass

    def flatten_recursion(self):
        pass

    def get_next_state(self, laction: LAction, tvars: Set[str]) -> Optional[LType]:
        return None

    def check_valid_projection(self) -> None:
        return

    def calc_fst_actions_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        fst_actions: Dict[str, Set[LAction]],
        update_tvars: Dict[str, bool],
    ):
        pass

    def set_fst_actions_rec(self, fst_actions: Dict[str, Set[LAction]]):
        pass

    def calc_next_states_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        next_states: Dict[str, Dict[LAction, Set[Any]]],
        update_tvars: Dict[str, bool],
    ):
        pass

    def set_next_states_rec(self, next_states: Dict[str, Dict[LAction, Set[Any]]]):
        pass

    def max_rec_depth(self, curr_rec_depth: int) -> int:
        return curr_rec_depth

    def gen_code(self, role: str, indent: str, env: CodeGen) -> str:
        done_cb = env.add_done_callback(role)
        return_stmt = CodeGen.return_stmt(CodeGen.method_call(ENV, done_cb, []))
        return CodeGen.indent_line(indent, return_stmt)

    def ensure_unique_tvars(self, tvar_mapping: Dict[str, str], namegen: NameGen):
        pass

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        return isinstance(o, LEnd)

    def __hash__(self) -> int:
        return 0
