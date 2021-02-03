from pathlib import Path
from typing import Dict, Tuple, List, FrozenSet, Set, Iterable, cast, Any

import jinja2

from codegen.namegen import NameGen

LABEL = "label"

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

# TEMPLATE ENV VARIABLES
T_IMPORTS = "imports"
T_ROLE_FUNCTION = "role_function"
T_ROLE_IMPL = "role_impl"
T_ROLE_CHAN_TYPE = "role_chan_type"
T_ROLE_ENV = "role_env"
T_ROLE_RESULT = "role_result"
T_CALLBACKS_INTERFACE = "interface_name"
T_CALLBACK_SIGS = "callback_sigs"
T_MSG_LABEL_TYPE = "label_type"
T_MSG_ENUM_VALUES = "msg_enums"
T_CHANNEL_STRUCTS = "channel_structs"
T_RESULT_STRUCTS = "result_structs"
T_ROLE_CHAN_FIELDS = "field_decls"
T_ROLE_CHAN_STRUCT = "struct_name"
T_ROLE_CHAN_VAR = "var_name"
T_RESULT_FUNC = "result_func"
T_ROLE_IMPL_FUNC = "role_func"
T_ROLE_ENV_TYPE = "role_env_type"
T_ROLE_START_FUNC = "func_name"
T_ENV_VAR = "env_var"
T_INIT_ROLE_ENV_METHOD = "method"

ROLE_IMPL_TEMPLATE = "roles.j2"
CALLBACKS_TEMPLATE = "callbacks.j2"
MESSAGES_TEMPLATE = "messages.j2"
CHANNELS_TEMPLATE = "channels.j2"
RESULTS_TEMPLATE = "results.j2"
ENTRYPOINT_TEMPLATE = "entrypoint.j2"

ENTRYPOINT_FILE = "entrypoint.go"
MSGS_IMPL_FILE = "messages.go"
RESULTS_FILE = "results.go"
CHANNELS_FILE = "channels.go"

# Code generation constants
DONE_CB = "Done"
ENV = "env"
ROLE_CHAN = "roleChannels"
RESULT = "result"


# UTIL
def uncapitalize(string: str) -> str:
    if len(string) < 2:
        return string.lower()
    return "".join([string[0].lower(), string[1:]])


class ImportsEnv:
    def __init__(self, root_pkg: PKG, protocol_pkg: PKG) -> None:
        super().__init__()
        self.imports: Set[PKG] = set()
        self.protocol_pkg = protocol_pkg
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

        self.role_mapping: Dict[ROLE, ROLE] = CodeGen.unique_roles(roles)
        self.roles = list(self.role_mapping.values())

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
            imports_env.import_pkg(PKG_CALLBACKS)
            imports_env.import_pkg(PKG_CHANNELS)
            imports_env.import_pkg(PKG_RESULTS)

        self.role_var_names: Dict[ROLE, NameGen] = {
            role: NameGen() for role in self.roles
        }

        # Callbacks
        self.callback_imports: Dict[ROLE, ImportsEnv] = {
            role: ImportsEnv(self.root_pkg, self.protocol_pkg) for role in self.roles
        }
        self.role_interfaces = CodeGen.role_env_interfaces(self.roles)
        self.callbacks: Dict[ROLE, Dict[str, Tuple[str, str]]] = {
            role: {} for role in self.roles
        }
        self.callback_names: Dict[ROLE, NameGen] = {}

        # Result Structs
        self.result_structs: Dict[ROLE, str] = CodeGen.create_result_structs(self.roles)

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
        self.channel_imports.import_pkg(PKG_MESSAGES)
        chan_key = (other_role, msg_type)
        if chan_key in self.channels[role]:
            return
        role_chan = self._chan_name_for_role(role, other_role, LABEL)
        # recv_chan = self._chan_name_for_role(other_role, role, LABEL)
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

    def gen_channels(self) -> List[Tuple[str, List[str]]]:
        role_channels: Dict[ROLE, List[str]] = {}
        for role, chan_fields in self.channels.items():
            chan_field_decls: List[str] = []
            for chan_key, chan_name in chan_fields.items():
                _, msg_type = chan_key
                chan_field_decls.append(CodeGen.chan_field_decl(chan_name, msg_type))
            role_channels[role] = chan_field_decls

        return [
            (self.channel_structs[role], chan_fields)
            for role, chan_fields in role_channels.items()
        ]

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

    def gen_role_callbacks(self, role: str) -> List[str]:
        interface_methods = [
            CodeGen.function_sig(cb_name, cb_params, cb_return_type)
            for cb_name, (cb_params, cb_return_type) in self.callbacks[role].items()
        ]
        return interface_methods

    @staticmethod
    def create_result_structs(roles: List[ROLE]) -> Dict[ROLE, str]:
        namegen = NameGen()
        return {
            role: namegen.unique_name(CodeGen.result_struct(role)) for role in roles
        }

    def get_result_struct(self, role: ROLE):
        return self.result_structs[role]

    def gen_result_structs(self) -> List[str]:
        return list(self.result_structs.values())

    # ROLE IMPL
    def role_var_assignment(
        self, role: str, variables: List[str], rhs: str
    ) -> Tuple[List[str], str]:
        return CodeGen.var_assignment(self.role_var_names[role], variables, rhs)

    def add_role_import(self, role: ROLE, pkg: PKG):
        self.role_imports[role].import_pkg(pkg)

    # GEN IMPL
    def gen_impl(self, ltypes: Dict[ROLE, Any]) -> Dict[str, str]:
        # Values should be LType, but import would cause cyclic dependency
        impl_files = {}
        for role, ltype in ltypes.items():
            role = self.role_mapping[role]
            ltype.ensure_unique_tvars({}, NameGen())

            role_impl = ltype.gen_code(role, INDENT, self)

            role_file_name = CodeGen.role_go_file_name(role)

            # ROLE IMPLEMENTATIONS
            role_impl_file_path = str(
                Path(self.root_pkg, self.protocol_pkg, PKG_ROLES, role_file_name)
            )
            role_impl_file = self.render_impl_template(role, role_impl)
            impl_files[role_impl_file_path] = role_impl_file

            # CALLBACKS INTERFACES
            role_callbacks_file_path = str(
                Path(self.root_pkg, self.protocol_pkg, PKG_CALLBACKS, role_file_name)
            )
            role_callbacks_impl = self.render_callbacks_template(role)
            impl_files[role_callbacks_file_path] = role_callbacks_impl

        # MESSAGES
        msgs_file_path = str(
            Path(self.root_pkg, self.protocol_pkg, PKG_MESSAGES, MSGS_IMPL_FILE)
        )
        msgs_impl = self.render_msgs_template()
        impl_files[msgs_file_path] = msgs_impl

        # CHANNELS
        channels_file_path = str(
            Path(self.root_pkg, self.protocol_pkg, PKG_CHANNELS, CHANNELS_FILE)
        )
        channels_impl = self.render_channels_template()
        impl_files[channels_file_path] = channels_impl

        # RESULTS
        results_file_path = str(
            Path(self.root_pkg, self.protocol_pkg, PKG_RESULTS, RESULTS_FILE)
        )
        results_impl = self.render_results_template()
        impl_files[results_file_path] = results_impl

        # ENTRYPOINT
        entrypoint_file_path = str(
            Path(self.root_pkg, self.protocol_pkg, ENTRYPOINT_FILE)
        )
        entrypoint_impl = self.gen_entrypoint()
        impl_files[entrypoint_file_path] = entrypoint_impl
        return impl_files

    def render_impl_template(self, role: ROLE, role_impl: str) -> str:
        env = {
            T_IMPORTS: self.role_imports[role].gen_imports(),
            T_ROLE_FUNCTION: CodeGen.role_impl_function_name(role),
            T_ROLE_IMPL: role_impl,
            T_ROLE_CHAN_TYPE: CodeGen.pkg_access(
                PKG_CHANNELS, self.channel_structs[role]
            ),
            T_ROLE_ENV: CodeGen.pkg_access(PKG_CALLBACKS, self.role_interfaces[role]),
            T_ROLE_RESULT: CodeGen.pkg_access(PKG_RESULTS, self.result_structs[role]),
        }
        return CodeGen.render_template(ROLE_IMPL_TEMPLATE, env)

    def render_callbacks_template(self, role: ROLE) -> str:
        role_callbacks = self.gen_role_callbacks(role)
        env = {
            T_IMPORTS: self.callback_imports[role].gen_imports(),
            T_CALLBACKS_INTERFACE: self.role_interfaces[role],
            T_CALLBACK_SIGS: role_callbacks,
        }
        return CodeGen.render_template(CALLBACKS_TEMPLATE, env)

    def render_msgs_template(self):
        env = {
            T_MSG_LABEL_TYPE: self.label_type,
            T_MSG_ENUM_VALUES: list(self.label_values.values()),
        }
        return CodeGen.render_template(MESSAGES_TEMPLATE, env)

    def render_channels_template(self):
        env = {
            T_IMPORTS: self.channel_imports.gen_imports(),
            T_CHANNEL_STRUCTS: self.gen_channels(),
        }
        return CodeGen.render_template(CHANNELS_TEMPLATE, env)

    def render_results_template(self):
        env = {T_RESULT_STRUCTS: list(self.result_structs.values())}
        return CodeGen.render_template(RESULTS_TEMPLATE, env)

    def gen_result_interface(self) -> List[str]:
        namegen = NameGen()
        interface_methods = [
            namegen.unique_name(CodeGen.role_result_method(role)) for role in self.roles
        ]

        result_params = [
            CodeGen.var_signature([(RESULT, self.result_structs[role])])
            for role in self.roles
        ]
        return [
            CodeGen.function_sig(method_name, result_param, "")
            for method_name, result_param in zip(interface_methods, result_params)
        ]

    def gen_init_interface(self) -> List[str]:
        namegen = NameGen()
        interface_methods = [
            namegen.unique_name(CodeGen.role_result_method(role)) for role in self.roles
        ]
        return_types = [
            CodeGen.pkg_access(PKG_CALLBACKS, self.role_interfaces[role])
            for role in self.roles
        ]
        return [
            CodeGen.function_sig(method_name, "", return_type)
            for method_name, return_type in zip(interface_methods, return_types)
        ]

    def gen_entrypoint(self):
        # GEN IMPORTS
        imports = self.gen_entrypoint_imports()

        entrypoint_namegen = NameGen()

        # GEN INIT ENV INTERFACE
        init_interface_name = entrypoint_namegen.unique_name(
            CodeGen.init_interface_name(self.protocol)
        )
        init_interface_methods, init_method_decls = self.gen_init_protocol_interface()

        # GEN RESULT ENV INTERFACE
        result_interface_name = entrypoint_namegen.unique_name(
            CodeGen.result_interface_name(self.protocol)
        )
        result_interface_methods, result_method_decls = (
            self.gen_protocol_result_interface()
        )

        # GEN ROLE START FUNCTIONS
        start_func_names, role_start_funcs = self.gen_role_start_functions(
            entrypoint_namegen, result_interface_methods
        )

        # GEN CHANNELS
        all_channels: Dict[Tuple[FrozenSet[ROLE, ROLE], str], str] = {}
        create_chan_stmts = []
        namegen = NameGen()
        for role, chan_fields in self.channels.items():
            for other_role, msg_type in chan_fields.keys():
                chan_key = (frozenset((role, other_role)), msg_type)
                if chan_key not in all_channels:
                    msg_type_in_var = self.normalise_label_type_name(msg_type)
                    chan_var = CodeGen.channel_var(role, other_role, msg_type_in_var)
                    make_chan = CodeGen.make_expr(CodeGen.chan_type(msg_type))
                    [chan_var], chan_assign = self.var_assignment(
                        namegen, [chan_var], make_chan
                    )
                    all_channels[chan_key] = chan_var
                    create_chan_stmts.append(chan_assign)

        # GEN CHANNEL STRUCTS
        chan_struct_vars: Dict[ROLE, VAR] = {}
        channel_struct_assigns: List[Dict[str, Any]] = []
        for role, chan_fields in self.channels.items():
            role_chan_var = CodeGen.role_channel_var(role)
            chan_struct_vars[role] = role_chan_var
            chan_field_decls: List[Tuple[str, str]] = []
            for (other_role, msg_type), chan_field_name in chan_fields.items():
                chan_var_key = (frozenset((role, other_role)), msg_type)
                chan_field_decls.append((chan_field_name, all_channels[chan_var_key]))
            role_chan_assign = {
                T_ROLE_CHAN_VAR: role_chan_var,
                T_ROLE_CHAN_STRUCT: CodeGen.pkg_access(
                    PKG_CHANNELS, self.channel_structs[role]
                ),
                T_ROLE_CHAN_FIELDS: chan_field_decls,
            }
            channel_struct_assigns.append(role_chan_assign)

        # GEN ROLE ENV ASSIGNMENTS
        env_vars: Dict[ROLE, VAR] = {}
        role_env_assigns: List[Dict[str, Any]] = []
        for role in self.roles:
            role_env_var = namegen.unique_name(CodeGen.role_env_variable(role))
            env_vars[role] = role_env_var
            env_assign = {
                T_ENV_VAR: role_env_var,
                T_INIT_ROLE_ENV_METHOD: init_interface_methods[role],
            }
            role_env_assigns.append(env_assign)

        # GEN ROLE GOROUTINES
        role_func_calls: List[Dict[str, Any]] = []
        for role in self.roles:
            func_call_env = {
                "start_role_func": start_func_names[role],
                "chan_var": chan_struct_vars[role],
                "env_var": env_vars[role],
            }
            role_func_calls.append(func_call_env)

        entrypoint_function = entrypoint_namegen.unique_name(
            CodeGen.entrypoint_function_name(self.protocol)
        )

        return self.render_entrypoint_template(
            channel_struct_assigns,
            create_chan_stmts,
            entrypoint_function,
            imports,
            init_interface_name,
            init_method_decls,
            result_interface_name,
            result_method_decls,
            role_env_assigns,
            role_func_calls,
            role_start_funcs,
        )

    def render_entrypoint_template(
        self,
        channel_struct_assigns: List[Dict[str, Any]],
        create_chan_stmts: List[str],
        entrypoint_function: str,
        imports: ImportsEnv,
        init_interface_name: str,
        init_method_decls: List[str],
        result_interface_name: str,
        result_method_decls: List[str],
        role_env_assigns: List[Dict[str, Any]],
        role_func_calls: List[Dict[str, Any]],
        role_start_funcs: List[Dict[str, Any]],
    ):
        entrypoint_env = {
            "protocol_pkg": self.protocol_pkg,
            T_IMPORTS: imports.gen_imports(),
            "init_interface_name": init_interface_name,
            "init_method_sigs": init_method_decls,
            "result_interface_name": result_interface_name,
            "result_method_sigs": result_method_decls,
            "role_start_funcs": role_start_funcs,
            "entrypoint_function": entrypoint_function,
            "make_chan_stmts": create_chan_stmts,
            "chan_struct_assigns": channel_struct_assigns,
            "role_env_assigns": role_env_assigns,
            "role_func_calls": role_func_calls,
        }
        return CodeGen.render_template(ENTRYPOINT_TEMPLATE, entrypoint_env)

    def gen_role_start_functions(
        self, endpoint_namegen: NameGen, result_interface_methods: Dict[ROLE, str]
    ) -> Tuple[Dict[ROLE, str], List[Dict[str, Any]]]:
        start_funcs = {}
        role_start_funcs: List[Dict[str, Any]] = []
        for role in self.roles:
            start_func_name = endpoint_namegen.unique_name(
                CodeGen.start_role_function(role)
            )
            start_funcs[role] = start_func_name
            role_chan_type = CodeGen.pkg_access(
                PKG_CHANNELS, self.channel_structs[role]
            )
            role_env_type = CodeGen.pkg_access(
                PKG_CALLBACKS, self.role_interfaces[role]
            )
            result_func = result_interface_methods[role]
            role_func_env = {
                T_ROLE_START_FUNC: start_func_name,
                T_ROLE_CHAN_TYPE: role_chan_type,
                T_ROLE_ENV_TYPE: role_env_type,
                T_ROLE_IMPL_FUNC: CodeGen.pkg_access(
                    PKG_ROLES, CodeGen.role_impl_function_name(role)
                ),
                T_RESULT_FUNC: result_func,
            }
            role_start_funcs.append(role_func_env)
        return start_funcs, role_start_funcs

    def gen_entrypoint_imports(self) -> ImportsEnv:
        imports = ImportsEnv(self.root_pkg, self.protocol_pkg)
        imports.add_sync_import()
        if len(self.roles) > 0:
            imports.import_pkg(PKG_RESULTS)
            imports.import_pkg(PKG_ROLES)
            imports.import_pkg(PKG_CALLBACKS)
            imports.import_pkg(PKG_CHANNELS)
        # Add whatever imports are needed for the channels (i.e. import messages or not?)
        imports.imports |= self.channel_imports.imports
        return imports

    @staticmethod
    def role_impl_function_name(role: ROLE) -> str:
        return role.capitalize()

    def gen_init_protocol_interface(self) -> Tuple[Dict[ROLE, str], List[str]]:
        namegen = NameGen()

        interface_methods = {}
        method_decls = []

        for role in self.roles:
            return_type = CodeGen.pkg_access(PKG_CALLBACKS, self.role_interfaces[role])
            method_name = namegen.unique_name(CodeGen.new_role_env_method(role))
            method_decls.append(CodeGen.function_sig(method_name, "", return_type))
            interface_methods[role] = method_name

        return interface_methods, method_decls

    def gen_protocol_result_interface(self) -> Tuple[Dict[ROLE, str], List[str]]:
        namegen = NameGen()

        interface_methods = {}
        method_decls = []

        for role in self.roles:
            param_type = CodeGen.pkg_access(PKG_RESULTS, self.result_structs[role])
            method_name = namegen.unique_name(CodeGen.process_role_result_method(role))
            method_decls.append(
                CodeGen.function_sig(
                    method_name, CodeGen.var_signature([(RESULT, param_type)]), ""
                )
            )
            interface_methods[role] = method_name

        return interface_methods, method_decls

    def normalise_label_type_name(self, msg_type: MSG_TYPE) -> MSG_TYPE:
        if msg_type == self.msg_label_type():
            return LABEL
        return msg_type

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
    def unique_roles(roles: List[ROLE]) -> Dict[ROLE, ROLE]:
        namegen = NameGen()
        # Build role mapping by lower-casing all roles. When resolving conflicts, roles
        # which are already lowercase should keep their name as is.
        unique_role_names = {}
        for role in set(roles):
            if role == role.lower():
                unique_role_names[role] = namegen.unique_name(role.lower())
        for role in set(roles):
            if role not in unique_role_names:
                unique_role_names[role] = namegen.unique_name(role.lower())

        return unique_role_names

    @staticmethod
    def chan_field_decl(chan_name: CHAN_NAME, msg_type: MSG_TYPE) -> str:
        return f"{chan_name} {CodeGen.chan_type(msg_type)}"

    @staticmethod
    def chan_type(msg_type: MSG_TYPE) -> str:
        return f"chan {msg_type}"

    @staticmethod
    def chan_struct_name(role: ROLE) -> str:
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
            [var], recv_stmt = self.role_var_assignment(role, [payload_name], chan_recv)
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

    @staticmethod
    def role_go_file_name(role: str) -> str:
        return f"{role}.go"

    @staticmethod
    def role_env_interfaces(roles: List[ROLE]) -> Dict[ROLE, str]:
        namegen = NameGen()
        return {
            role: namegen.unique_name(CodeGen.role_env_interface(role))
            for role in roles
        }

    @staticmethod
    def render_template(template: str, env: Dict[str, Any]) -> str:
        templates_dir_path = (Path(__file__).parent / "templates").absolute()
        template_loader = jinja2.FileSystemLoader(templates_dir_path)
        template_env = jinja2.Environment(loader=template_loader)
        template = template_env.get_template(template)
        result = template.render(**env)
        return result

    @staticmethod
    def role_result_method(role: str) -> str:
        return f"Result_From_{role.capitalize()}"

    @staticmethod
    def role_init_state_method(role: str) -> str:
        return f"New_{role.capitalize()}_Env"

    @staticmethod
    def var_assignment(
        namegen: NameGen, variables: List[VAR], rhs: str
    ) -> Tuple[List[str], str]:
        unique_vars = [namegen.unique_name(var) for var in variables]
        var_assign = f"{', '.join(unique_vars)} := {rhs}"
        return unique_vars, var_assign

    @staticmethod
    def channel_var(role: ROLE, other_role: ROLE, msg_type: MSG_TYPE) -> VAR:
        return f"{role.lower()}_{other_role.lower()}_{msg_type}_chan"

    @staticmethod
    def make_expr(expr: str) -> str:
        return f"make({expr})"

    @staticmethod
    def role_channel_var(role: ROLE) -> VAR:
        return f"{role.lower()}_chan"

    @staticmethod
    def role_env_variable(role: ROLE) -> VAR:
        return f"{role.lower()}_env"

    @staticmethod
    def new_role_env_method(role: ROLE) -> str:
        return f"New_{role.capitalize()}_Env"

    @staticmethod
    def process_role_result_method(role: ROLE) -> str:
        return f"{role.capitalize()}_Result"

    @staticmethod
    def init_interface_name(protocol: str) -> str:
        return f"Init_{protocol.capitalize()}_Env"

    @staticmethod
    def result_interface_name(protocol: str) -> str:
        return f"{protocol.capitalize()}_Result_Env"

    @staticmethod
    def start_role_function(role: ROLE) -> str:
        return f"Start_{role.capitalize()}"

    @staticmethod
    def entrypoint_function_name(protocol: str) -> str:
        return f"{protocol.capitalize()}"
