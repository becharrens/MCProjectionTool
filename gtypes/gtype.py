from abc import ABC, abstractmethod
from typing import Dict, Set, Tuple

from gtypes.gaction import GAction
from ltypes.laction import LAction
from ltypes.ltype import LType


class GType(ABC):
    def __init__(self):
        self.ppts: Set[str] = set()

    @abstractmethod
    def project(self, roles: Set[str]) -> Dict[str, LType]:
        pass

    @abstractmethod
    def first_actions(self, tvars: Set[str]) -> Set[GAction]:
        pass

    @abstractmethod
    def set_rec_gtype(self, tvar: str, gtype) -> None:
        pass

    @abstractmethod
    def hash(self, tvars: Set[str]) -> int:
        pass

    @abstractmethod
    def to_string(self, indent: str) -> str:
        pass

    @abstractmethod
    def normalise(self):
        pass

    @abstractmethod
    def has_rec_var(self, tvar: str) -> bool:
        pass

    @abstractmethod
    def build_mapping(
        self,
        mapping: Dict[str, Dict[LAction, Set[GAction]]],
        role_mapping: Dict[str, GAction],
        tvars: Set[str],
    ) -> None:
        pass

    @abstractmethod
    def all_participants(
        self, curr_tvar: str, tvar_ppts: Dict[str, Tuple[Set[str], Set[str]]]
    ) -> None:
        """
        tvar_ppts - OrderedDict({tvar: (set(roles), set(tvars))})

        Map every tvar to the set of participants in its body and the set of
        recursive variables which are present in its body, since they must
        their participants must also be taken into account.

        Order of keys reflects the hierarchy of the recursion variables
        """
        pass

    @abstractmethod
    def set_rec_participants(self, tvar_ppts: Dict[str, Set[str]]) -> None:
        pass

    def get_participants(self) -> Set[str]:
        return self.ppts

    @abstractmethod
    def ensure_unique_tvars(
        self, tvar_mapping: Dict[str, str], tvar_names: Set[str], uid: int
    ):
        pass

    @staticmethod
    def unique_tvar(tvar: str, tvar_names: Set[str], uid: int) -> Tuple[str, int]:
        while True:
            unique_tvar = f"{tvar}_{uid}"
            uid += 1
            if unique_tvar not in tvar_names:
                tvar_names.add(unique_tvar)
                return unique_tvar, uid
