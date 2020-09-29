from abc import ABC, abstractmethod
from typing import Set, Dict, Tuple, Any

from ltypes.laction import LAction


class LType(ABC):
    @abstractmethod
    def next_states(self) -> Dict[LAction, Set[Any]]:
        pass

    @abstractmethod
    def rec_next_states(self, tvars: Set[str]) -> Dict[LAction, Set[Any]]:
        pass

    @abstractmethod
    def first_participants(self, tvars: Set[str]) -> Set[str]:
        pass

    @abstractmethod
    def first_actions(self, tvars: Set[str]) -> Set[LAction]:
        pass

    @abstractmethod
    def set_rec_ltype(self, tvar: str, ltype):
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
