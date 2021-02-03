from enum import Enum
from typing import List, Tuple, cast

from codegen.codegen import CodeGen, ENV, PKG_MESSAGES
from ltypes import HASH_SIZE


class ActionType(Enum):
    send = 0
    recv = 1

    def dual(self):
        return ActionType(1 - self.value)

    def is_send(self) -> bool:
        return self.value == 0

    def __str__(self) -> str:
        if self.value == 0:
            return "!"
        return "?"


class LAction:
    def __init__(
        self,
        proj_role: str,
        participant: str,
        action_type: ActionType,
        label: str,
        payloads: List[Tuple[str, str]],
    ):
        self.participant = participant
        self.label = label
        self.action_type = action_type
        self.proj_role = proj_role
        self.payloads = payloads

    def get_participant(self) -> str:
        return self.participant

    def get_payloads(self) -> Tuple[List[str], List[str]]:
        return self._split_payloads()

    def get_label(self) -> str:
        return self.label

    def is_send(self) -> bool:
        return self.action_type.is_send()

    def dual(self):
        return LAction(
            self.participant,
            self.proj_role,
            self.action_type.dual(),
            self.label,
            self.payloads,
        )

    def hash(self):
        return str(self).__hash__() % HASH_SIZE

    def gen_code(self, role: str, indent: str, env: CodeGen) -> str:
        """
        Generate code for a send/recv action which is not the first message in a
        mixed choice branch
        """
        payload_names, payload_types = self._split_payloads()
        if self.action_type.is_send():
            # Gen Send
            send_cb = env.add_send_callback(
                role, self.participant, self.label, payload_types
            )
            cb_call = CodeGen.method_call(ENV, send_cb, [])
            if len(payload_names) > 0:
                var_names, cb_call_stmt = env.role_var_assignment(
                    role, payload_names, cb_call
                )
            else:
                var_names, cb_call_stmt = [], cb_call
            label_enum = env.add_msg_label(self.label)
            env.add_role_import(role, PKG_MESSAGES)
            env.add_label_channel(role, self.participant)

            label_chan = env.get_channel(role, self.participant, env.msg_label_type())

            channel_sends: List[Tuple[str, str]] = [(label_chan, label_enum)]
            for i, payload_type in enumerate(payload_types):
                env.add_channel(role, self.participant, payload_type)
                payload_chan = env.get_channel(role, self.participant, payload_type)
                channel_sends.append((payload_chan, var_names[i]))

            send_msg_lines = CodeGen.gen_channel_sends(channel_sends)
            impl_lines = [cb_call_stmt, *send_msg_lines]
            return CodeGen.join_lines(indent, impl_lines)
        else:
            # Gen recv
            env.add_label_channel(role, self.participant)
            label_chan = env.get_channel(role, self.participant, env.msg_label_type())

            recv_label_stmt = CodeGen.channel_recv(label_chan)
            chan_fields = []
            for payload_type in payload_types:
                env.add_channel(role, self.participant, payload_type)
                payload_chan = env.get_channel(role, self.participant, payload_type)
                chan_fields.append(payload_chan)

            recv_payload_vars, recv_payload_stmts = env.recv_payloads(
                role, payload_names, chan_fields
            )

            impl_lines = [recv_label_stmt, *recv_payload_stmts]

            recv_cb = env.add_recv_callback(
                role, self.participant, self.label, self.payloads
            )

            recv_cb_call = CodeGen.method_call(ENV, recv_cb, recv_payload_vars)
            impl_lines.append(recv_cb_call)

            return CodeGen.join_lines(indent, impl_lines)

    def _split_payloads(self) -> Tuple[List[str], List[str]]:
        if len(self.payloads) == 0:
            return [], []
        return tuple(zip(*self.payloads))

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, LAction):
            return False
        return self.__str__() == o.__str__()

    def __hash__(self) -> int:
        return self.hash()

    def __str__(self) -> str:
        return f"{self.participant}{self.action_type}{self.label}"
