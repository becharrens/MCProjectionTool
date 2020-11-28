from abc import ABC, abstractmethod
from collections import deque
from typing import Dict, Set, Tuple, Deque

from gtypes.gaction import GAction
from ltypes.laction import LAction
from ltypes.ltype import LType


class GType(ABC):
    def __init__(self):
        pass

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
