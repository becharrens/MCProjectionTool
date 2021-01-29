from typing import Set, Dict, Tuple, List, Optional

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

    def ensure_unique_tvars(
        self, tvar_mapping: Dict[str, str], tvar_names: Set[str], uid: int
    ):
        pass

    def fst_global_actions_rec(
        self,
        curr_tvar: str,
        rec_gactions: Dict[str, Tuple[Set[str], Set[GAction]]],
        tvar_deps: Dict[str, Set[str]],
    ):
        pass

    def set_rec_fst_global_actions(self, rec_gactions: Dict[str, Set[GAction]]):
        pass

    def ensure_consistent_payloads(self, payload_mapping: Dict[str, List[Tuple[Optional[str], str]]]) -> None:
        pass

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        return isinstance(o, GEnd)

    def __hash__(self) -> int:
        return 0
