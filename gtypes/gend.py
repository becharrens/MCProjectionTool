from typing import Set, Dict, Tuple

from gtypes.gaction import GAction
from gtypes.gtype import GType
from ltypes.laction import LAction
from ltypes.lend import LEnd
from ltypes.ltype import LType


class GEnd(GType):
    def first_actions(self, tvars: Set[str]) -> Set[str]:
        return set()

    def set_rec_gtype(self, tvar: str, gtype: GType) -> None:
        pass

    def hash(self, tvars: Set[str]) -> int:
        return 1

    def project(self, roles: Set[str]) -> Dict[str, LType]:
        return {role: LEnd() for role in roles}

    def to_string(self, indent: str) -> str:
        return f"{indent}end"

    def normalise(self):
        return self

    def has_rec_var(self, tvar: str) -> bool:
        return False

    def build_mapping(
        self,
        mapping: Dict[str, Dict[LAction, Set[GAction]]],
        role_mapping: Dict[str, GAction],
        tvars: Set[str],
    ) -> None:
        pass

    def all_participants(
        self, curr_tvar: str, tvar_ppts: Dict[str, Tuple[Set[str], Set[str]]]
    ) -> None:
        pass

    def set_rec_participants(self, tvar_ppts: Dict[str, Set[str]]) -> None:
        pass

    def ensure_unique_tvars(
        self, tvar_mapping: Dict[str, str], tvar_names: Set[str], uid: int
    ):
        pass

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        return isinstance(o, GEnd)

    def __hash__(self) -> int:
        return 0
