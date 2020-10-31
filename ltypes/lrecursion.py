from typing import Set, Tuple, Dict, Type, cast, Optional, Any

import ltypes
from gtypes.gtype import GType
from ltypes.laction import LAction
from ltypes.ltype import LType


class LRecursion(LType):
    def __init__(self, tvar: str, ltype: LType) -> None:
        super().__init__()
        self.tvar = tvar
        self.ltype = ltype
        self.ltype.set_rec_ltype(self.tvar, self)

    def rec_next_states(self, tvars: Set[str]) -> Dict[LAction, Set[LType]]:
        return self.ltype.rec_next_states(tvars)

    def next_states(self) -> Dict[LAction, Set[LType]]:
        return self.ltype.next_states()

    def set_rec_ltype(self, tvar, gtype):
        assert tvar != self.tvar
        self.ltype.set_rec_ltype(tvar, gtype)

    def first_participants(self, tvars):
        return self.ltype.first_participants(tvars)

    def first_actions(self, tvars: Set[str]) -> Set[LAction]:
        return self.ltype.first_actions(tvars)

    def hash(self, tvars):
        return (
            self.tvar.__hash__() * ltypes.PRIME + self.ltype.hash(tvars)
        ) % ltypes.HASH_SIZE

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

    def is_first_interaction_with_role(self, laction: LAction, tvars: Set[str]) -> bool:
        if self.tvar not in tvars:
            tvars.add(self.tvar)
        return self.ltype.is_first_interaction_with_role(laction, tvars)

    def interacts_with_role_before_action(
        self, role: str, laction: LAction, tvars: Set[str]
    ) -> bool:
        if self.tvar not in tvars:
            tvars.add(self.tvar)
        return self.ltype.interacts_with_role_before_action(laction, tvars)

    def check_valid_projection(self, tvars: Set[str]) -> None:
        # TODO: is this correct?
        # tvars.add(self.tvar)
        self.ltype.check_valid_projection(tvars)

    def __str__(self) -> str:
        return self.to_string("")

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, LRecursion):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return self.ltype.hash(set())
