from typing import Dict, Tuple, List, FrozenSet, Set, Iterable, cast

from codegen.namegen import NameGen

ROLE = str
CHAN_NAME = str
CALLBACK_NAME = str
PAYLOAD_NAME = str

TYPE = str
MSG_TYPE = TYPE
PAYLOAD_TYPE = TYPE
RESULT_STRUCT = TYPE

MSG_ENUM = str
MSG_LABEL = str
CALLBACK = str
VAR = str
VAR_SIG = List[Tuple[PAYLOAD_NAME, PAYLOAD_TYPE]]
RETURN_TYPE = List[TYPE]
PARAM_DECL = VAR_SIG
ARGS = List[VAR]
IMPORTS = str

PKG = str


# PKGS
# =========================
PKG_CALLBACKS = "callbacks"
PKG_CHANNELS = "channels"
PKG_MESSAGES = "messages"
PKG_PROTOCOL = "protocol"
PKG_RESULTS = "results"
PKG_ROLES = "roles"
PKG_SYNC = "sync"
PKGS = {PKG_ROLES, PKG_MESSAGES, PKG_PROTOCOL, PKG_RESULTS, PKG_CALLBACKS, PKG_CHANNELS}
# =========================

INDENT = "   "
NEWLINE = "\n"
QUOTE = '"'

# Code generation constants
DONE_CB = "Done"
ENV = "env"
ROLE_CHAN = "roleChannels"

# UTIL
def uncapitalize(string: str) -> str:
    if len(string) < 2:
        return string.lower()
    return "".join([string[0].lower(), string[1:]])


class ImportsEnv:
    def __init__(self, root_pkg: PKG, protocol: PKG) -> None:
        super().__init__()
        self.imports: Set[PKG] = set()
        self.protocol_pkg = protocol
        self.root_pkg = root_pkg
        self.import_sync = False

    def import_pkg(self, pkg: PKG):
        self.imports.add(pkg)

    def add_sync_import(self) -> None:
        self.import_sync = True

    def gen_imports(self) -> str:
        if len(self.imports) == 0:
            return ""
        import_stmts = [
            f"{self.root_pkg}/{self.protocol_pkg}/{pkg}" for pkg in self.imports
        ]
        if self.import_sync:
            import_stmts.append(PKG_SYNC)
        return f"import (\n{ NEWLINE.join(f'{INDENT}{QUOTE}{import_stmt}{QUOTE}' for import_stmt in import_stmts) }\n)"


class CodeGen:
    def __init__(self, roles: List[ROLE], protocol: str, root_pkg: str) -> None:
        super().__init__()

        self.roles: List[ROLE] = CodeGen.unique_roles(roles)

        self.protocol = protocol
        self.protocol_pkg = protocol.lower()
        self.root_pkg = root_pkg

        # Channels
        self.channel_imports: ImportsEnv = ImportsEnv(root_pkg, self.protocol_pkg)
        self.channel_structs: Dict[ROLE, str] = CodeGen.role_chan_structs(self.roles)
        self.channels: Dict[ROLE, Dict[Tuple[ROLE, MSG_TYPE], CHAN_NAME]] = {
            role: {} for role in self.roles
        }
        self.channel_names: Dict[ROLE, NameGen] = {}

        # Role Impl
        self.role_imports: Dict[ROLE, ImportsEnv] = {
            role: ImportsEnv(root_pkg, self.protocol_pkg) for role in self.roles
        }
        for imports_env in self.role_imports.values():
            # Add common imports for all role implementations
            imports_env.add_sync_import()
            imports_env.import_pkg(PKG_CALLBACKS)
            imports_env.import_pkg(PKG_CHANNELS)

        self.role_var_names: Dict[ROLE, NameGen] = {
            role: NameGen() for role in self.roles
        }
        self.role_impl: Dict[ROLE, str] = {}

        # Callbacks
        self.callback_imports: Dict[ROLE, ImportsEnv] = {
            role: ImportsEnv(root_pkg, protocol) for role in self.roles
        }
        self.callbacks: Dict[ROLE, Dict[str, Tuple[str, str]]] = {
            role: {} for role in self.roles
        }
        self.callback_names: Dict[ROLE, NameGen] = {}

        # Result Structs
        self.result_struct_names = NameGen()
        self.result_structs: Dict[ROLE, str] = {}
        self.create_result_structs()

        # Protocol Imports
        self.protocol_imports = ImportsEnv(self.root_pkg, self.protocol_pkg)

        # Message label enum
        self.label_type: MSG_TYPE = f"{protocol.capitalize()}_Label"

        # Message label enum values
        self.msg_enum_namegen = NameGen()
        self.label_values: Dict[str, MSG_ENUM] = {}

    # CHANNELS
    def _chan_name_for_role(
        self, role: ROLE, other_role: ROLE, msg_type: MSG_TYPE
    ) -> CHAN_NAME:
        if role not in self.channel_names:
            self.channel_names[role] = NameGen()

        chan_name = CodeGen.role_channel(other_role, msg_type)
        name_gen = self.channel_names[role]
        return name_gen.unique_name(chan_name)

    def add_channel(
        self, curr_role: ROLE, other_role: ROLE, msg_type: MSG_TYPE
    ) -> None:
        chan_key = (other_role, msg_type)
        if chan_key in self.channels[curr_role]:
            return
        role_chan = self._chan_name_for_role(curr_role, other_role, msg_type)
        # recv_chan = self._chan_name_for_role(other_role, curr_role, msg_type)
        self.channels[curr_role][chan_key] = role_chan

    def add_label_channel(self, role: ROLE, other_role: ROLE) -> None:
        msg_type = self.msg_label_type()
        chan_key = (other_role, msg_type)
        if chan_key in self.channels[role]:
            return
        role_chan = self._chan_name_for_role(role, other_role, "label")
        # recv_chan = self._chan_name_for_role(other_role, role, "label")
        self.channels[role][chan_key] = role_chan

    def add_msg_label(self, label: MSG_LABEL) -> MSG_ENUM:
        if label in self.label_values:
            return CodeGen.pkg_access(PKG_MESSAGES, self.label_values[label])

        label_enum = self.msg_enum_namegen.unique_name(CodeGen.msg_label_enum(label))
        self.label_values[label] = label_enum
        return CodeGen.pkg_access(PKG_MESSAGES, label_enum)

    def msg_label_type(self):
        return CodeGen.pkg_access(PKG_MESSAGES, self.label_type)

    def get_channel(
        self, role: ROLE, other_role: ROLE, msg_type: MSG_TYPE
    ) -> CHAN_NAME:
        return self.channels[role][(other_role, msg_type)]

    def gen_channels(self) -> Tuple[str, List[Tuple[ROLE, List[str]]]]:
        role_channels: Dict[ROLE, List[str]] = {}
        for role, chan_fields in self.channels.items():
            chan_field_decls: List[str] = []
            for chan_key, chan_name in chan_fields.items():
                _, msg_type = chan_key
                chan_field_decls.append(CodeGen.chan_field_decl(chan_name, msg_type))
            role_channels[role] = chan_field_decls
        return (
            self.channel_imports.gen_imports(),
            [
                (self.channel_structs[role], chan_fields)
                for role, chan_fields in role_channels.items()
            ],
        )

    @staticmethod
    def _add_role_chan(
        role_channels: Dict[ROLE, List[str]],
        role: ROLE,
        chan_field: CHAN_NAME,
        msg_type: MSG_TYPE,
    ):
        role_chan_fields = role_channels.setdefault(role, [])
        role_chan_fields.append(CodeGen.chan_field_decl(chan_field, msg_type))

    # CALLBACKS
    def _new_callback_name(self, role: ROLE, cb_name: CALLBACK) -> CALLBACK:
        if role not in self.callback_names:
            self.callback_names[role] = NameGen()

        name_gen = self.callback_names[role]
        return name_gen.unique_name(cb_name)

    def _add_callback(
        self, role: ROLE, cb_name: CALLBACK, params: PARAM_DECL, ret_type: RETURN_TYPE
    ) -> None:
        role_callbacks = self.callbacks[role]
        if cb_name in role_callbacks:
            return

        ret_type_str = CodeGen.return_type(ret_type)
        if len(ret_type) > 1:
            ret_type_str = f"({ret_type_str})"
        params_str = CodeGen.var_signature(params)

        role_callbacks[cb_name] = (params_str, ret_type_str)

    def add_send_callback(
        self, role: ROLE, recv: ROLE, label: str, payloads: RETURN_TYPE
    ):
        cb_name = CodeGen.send_callback_name(recv, label)
        cb_name = self._new_callback_name(role, cb_name)

        self._add_callback(role, cb_name, [], payloads)
        return cb_name

    def add_recv_callback(
        self, role: ROLE, sender: ROLE, label: str, payloads: PARAM_DECL
    ):
        cb_name = CodeGen.recv_callback_name(sender, label)
        cb_name = self._new_callback_name(role, cb_name)

        self._add_callback(role, cb_name, payloads, [])
        return cb_name

    def add_done_callback(self, role: ROLE):
        self.callback_imports[role].import_pkg(PKG_RESULTS)
        return_type = CodeGen.pkg_access(PKG_RESULTS, self.result_structs[role])
        self._add_callback(role, DONE_CB, [], [return_type])
        return DONE_CB

    def gen_callbacks(self) -> Dict[ROLE, Tuple[str, str, List[str]]]:
        callback_interfaces = {}
        interface_namegen = NameGen()
        for role in self.roles:
            role_interface = interface_namegen.unique_name(
                CodeGen.role_env_interface(role)
            )
            interface_methods = [
                CodeGen.function_sig(cb_name, cb_params, cb_return_type)
                for cb_name, (cb_params, cb_return_type) in self.callbacks.items()
            ]
            imports_str = self.callback_imports[role].gen_imports()
            callback_interfaces[role] = (imports_str, role_interface, interface_methods)
        return callback_interfaces

    # RESULT STRUCTS
    def _add_result_struct(self, role: ROLE):
        struct_name = CodeGen.result_struct(role)
        struct_name = self.result_struct_names.unique_name(struct_name)

        self.result_structs[role] = struct_name

    def create_result_structs(self):
        for role in self.roles:
            self._add_result_struct(role)

    def get_result_struct(self, role: ROLE):
        return self.result_structs[role]

    def gen_result_structs(self) -> List[str]:
        return list(self.result_structs.values())

    # ROLE IMPL
    def var_assignment(
        self, role: str, variables: List[str], rhs: str
    ) -> Tuple[List[str], str]:
        namegen = self.role_var_names[role]
        unique_vars = [namegen.unique_name(var) for var in variables]
        var_assign = f"{', '.join(unique_vars)} := {rhs}"
        return unique_vars, var_assign

    def add_role_import(self, role: ROLE, pkg: PKG):
        self.role_imports[role].import_pkg(pkg)

    # NAMES AND CODEGEN FUNCTIONS
    # @staticmethod
    # def role_channel(role: ROLE, msg_type: MSG_TYPE, is_send: bool) -> CHAN_NAME:
    #     if is_send:
    #         return f"{msg_type.capitalize()}_To_{role.capitalize()}"
    #     return f"{msg_type.capitalize()}_From_{role.capitalize()}"

    @staticmethod
    def role_channel(role: ROLE, msg_type: MSG_TYPE) -> CHAN_NAME:
        return f"{role.capitalize()}_{msg_type}"

    @staticmethod
    def var_signature(var_decl: VAR_SIG) -> str:
        var_sig = [
            f"{uncapitalize(payload_name)} {payload_type}"
            for payload_name, payload_type in var_decl
        ]
        return ", ".join(var_sig)

    @staticmethod
    def return_type(ret_type: RETURN_TYPE) -> str:
        if len(ret_type) == 0:
            return ""
        if len(ret_type) == 1:
            return ret_type[0]
        return f'({", ".join(ret_type)})'

    @staticmethod
    def send_callback_name(recv: ROLE, label: MSG_TYPE) -> CALLBACK:
        return f"{label.capitalize()}_To_{recv.capitalize()}"

    @staticmethod
    def recv_callback_name(sender: ROLE, label: MSG_TYPE) -> CALLBACK:
        return f"{label.capitalize()}_From_{sender.capitalize()}"

    @staticmethod
    def result_struct(role):
        return f"{role.capitalize()}_Result"

    @staticmethod
    def unique_roles(roles: List[ROLE]) -> List[ROLE]:
        namegen = NameGen()
        return [namegen.unique_name(role.lower()) for role in set(roles)]

    @staticmethod
    def chan_field_decl(chan_name: CHAN_NAME, msg_type: MSG_TYPE):
        return f"{chan_name} chan {msg_type}"

    @staticmethod
    def chan_struct_name(role: ROLE):
        return f"{role.capitalize()}_Chan"

    @staticmethod
    def role_chan_structs(roles: List[ROLE]) -> Dict[ROLE, str]:
        namegen = NameGen()
        return {
            role: namegen.unique_name(CodeGen.chan_struct_name(role)) for role in roles
        }

    @staticmethod
    def pkg_access(pkg: PKG, access: str) -> str:
        return f"{pkg}.{access}"

    @staticmethod
    def msg_label_enum(label: MSG_LABEL) -> MSG_ENUM:
        return label.capitalize()

    @staticmethod
    def role_env_interface(role: ROLE) -> str:
        return f"{role.capitalize()}_Env"

    @staticmethod
    def function_sig(func_name: str, params: str, return_type: str) -> str:
        return f"{func_name}({params}) {return_type}"

    @staticmethod
    def method_call(var: str, method: str, args: ARGS) -> str:
        args_str = ", ".join(args)
        return f"{var}.{method}({args_str})"

    @staticmethod
    def return_stmt(value: str) -> str:
        return f"return {value}"

    @staticmethod
    def incr_indent(indent: str) -> str:
        return indent + INDENT

    @staticmethod
    def indent_line(indent: str, line: str) -> str:
        return f"{indent}{line}"

    @staticmethod
    def indent_lines(indent: str, lines: List[str]) -> List[str]:
        return [CodeGen.indent_line(indent, line) for line in lines]

    @staticmethod
    def channel_send(chan_field: str, msg: str) -> str:
        return f"{ROLE_CHAN}.{chan_field} <- {msg}"

    @staticmethod
    def gen_channel_sends(channel_sends: List[Tuple[str, str]]) -> List[str]:
        return [
            CodeGen.channel_send(chan_field, msg) for chan_field, msg in channel_sends
        ]

    @staticmethod
    def join_lines(indent: str, lines: List[str]) -> str:
        lines = CodeGen.indent_lines(indent, lines)
        lines_str = "\n".join(lines)
        return f"{lines_str}\n"

    @staticmethod
    def channel_recv(recv_chan: str) -> str:
        return f"<-{ROLE_CHAN}.{recv_chan}"

    def recv_payloads(
        self, role: ROLE, payloads: List[PAYLOAD_NAME], chan_fields: List[CHAN_NAME]
    ) -> Tuple[List[VAR], List[str]]:
        payload_vars = []
        recv_stmts = []
        for payload_name, chan_field in zip(payloads, chan_fields):
            # Assumes payload names are not capitalised
            chan_recv = CodeGen.channel_recv(chan_field)
            [var], recv_stmt = self.var_assignment(role, [payload_name], chan_recv)
            payload_vars.append(var)
            recv_stmts.append(recv_stmt)
        return payload_vars, recv_stmts

    @staticmethod
    def gen_label_decl(tvar: str) -> str:
        return f"{tvar}:"

    @staticmethod
    def continue_stmt(tvar: str) -> str:
        return f"continue {tvar}"

    @staticmethod
    def decr_indent(indent: str) -> str:
        return indent[: len(indent) - len(INDENT)]

    @staticmethod
    def _inf_for_loop(indent: str, impl: str) -> str:
        return "\n".join([f"{indent}for {{", impl, f"{indent}}}"])

    @staticmethod
    def labelled_for_loop(indent: str, label: str, impl: str) -> str:
        label_decl = CodeGen.gen_label_decl(label)
        label_decl = CodeGen.indent_line(CodeGen.decr_indent(indent), label_decl)
        return "\n".join([label_decl, CodeGen._inf_for_loop(indent, impl)])

    @staticmethod
    def gen_case_stmt(expr: str):
        return f"case {expr}:"

    @staticmethod
    def recv_label_var(sender: str) -> str:
        return f"label_from_{sender}"

    @staticmethod
    def gen_switch(indent: str, switch_expr: str, switch_cases: List[str]) -> str:
        cases_str = "\n".join(switch_cases)
        return f"{indent}switch {switch_expr} {{\n{cases_str}\n{indent}}}"

    @staticmethod
    def gen_select(indent: str, select_cases: List[str]) -> str:
        cases_str = "\n".join(select_cases)
        return f"{indent}select {{\n{cases_str}\n{indent}}}"

    @staticmethod
    def switch_default_case(indent: str) -> str:
        default_case = CodeGen.indent_line(indent, "default:")
        new_indent = CodeGen.incr_indent(indent)
        default_impl = 'panic("Invalid choice was made")'
        default_impl = CodeGen.indent_line(new_indent, default_impl)
        return "\n".join([default_case, default_impl])
