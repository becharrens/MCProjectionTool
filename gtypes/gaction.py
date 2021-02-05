from typing import List, Optional, Tuple

from codegen.codegen import uncapitalize
from codegen.namegen import NameGen
from gtypes import HASH_SIZE
from ltypes.laction import LAction, ActionType


def default_payload_name(idx: int) -> str:
    return f"p_{idx}"


class GAction:
    def __init__(
        self,
        participants: List[str],
        label: str,
        payloads: List[Tuple[Optional[str], str]],
    ):
        assert len(set(participants)) == 2
        self.participants = participants
        self.label = label
        self.payloads = self.normalise_payloads(payloads)

    def get_participants(self):
        return self.participants

    def project(self, role):
        if role == self.participants[0]:
            return LAction(
                self.participants[0],
                self.participants[1],
                ActionType.send,
                self.label,
                self.payloads,
            )
        if role == self.participants[1]:
            return LAction(
                self.participants[1],
                self.participants[0],
                ActionType.recv,
                self.label,
                self.payloads,
            )
        return None

    def normalise_payloads(
        self, payloads: List[Tuple[Optional[str], str]]
    ) -> List[Tuple[str, str]]:
        norm_payloads: List[Tuple[str, str]] = []
        namegen = NameGen()
        for i, (payload_name, payload_type) in enumerate(payloads):
            if payload_name is None:
                payload_name = default_payload_name(i)
            else:
                payload_name = uncapitalize(payload_name)
            payload_name = namegen.unique_name(payload_name)
            norm_payloads.append((payload_name, payload_type))
        return norm_payloads

    def get_payloads(self):
        return self.payloads

    def get_label(self):
        return self.label

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, GAction):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return str(self).__hash__() % HASH_SIZE

    def __str__(self) -> str:
        if len(self.payloads) > 0:
            str_payloads = [f"{pname}:{ptype}" for pname, ptype in self.payloads]
            payloads_str = f'({", ".join(str_payloads)})'
        else:
            payloads_str = ""
        sender, recv = self.participants
        return f"{self.label}{payloads_str} from {sender} to {recv}"
        # return f'{"->".join(self.participants)}:{self.label}'
