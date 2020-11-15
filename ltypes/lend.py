from typing import Set, Dict, Tuple, Any, Optional

from ltypes.laction import LAction
from ltypes.ltype import LType


class LEnd(LType):
    def first_participants(self, tvars: Set[str]) -> Set[str]:
        return set()

    def first_actions(self) -> Set[LAction]:
        return set()

    def first_actions_rec(self, tvars: Set[str]) -> Set[LAction]:
        return set()

    def set_rec_ltype(self, tvar: str, ltype):
        pass

    def hash(self) -> int:
        return 0

    def hash_rec(self, tvars: Set[str]) -> int:
        return 1

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

    def is_first_interaction_with_role(self, laction: LAction, tvars: Set[str]) -> bool:
        return False

    def interacts_with_role_before_action(
        self, role: str, laction: LAction, tvars: Set[str]
    ) -> bool:
        return True

    def check_valid_projection(self) -> None:
        return

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        return isinstance(o, LEnd)

    def __hash__(self) -> int:
        return 0
