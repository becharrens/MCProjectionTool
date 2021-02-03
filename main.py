import os
from collections import OrderedDict, deque
from pathlib import Path
from typing import Set, Dict

from codegen.codegen import INDENT, CodeGen
from dfa.dfa import DFA
from ltypes.laction import LAction
from ltypes.ltype import LType
from parser import parser as scr_parser
import argparse


def compute_recursion_fst_actions(
    fst_actions: Dict[str, Set[LAction]], tvar_deps: Dict[str, Set[str]]
):
    computed = set()
    for tvar, tvar_fst_actions in fst_actions.items():
        tvar_queue = deque(tvar_deps[tvar])
        # Compute transitive closure of tvars
        visited = set(tvar_deps[tvar])
        visited.add(tvar)
        while tvar_queue:
            new_tvar = tvar_queue.popleft()
            tvar_fst_actions |= fst_actions[new_tvar]
            if new_tvar not in computed:
                new_tvars = tvar_deps[new_tvar].difference(visited)
                tvar_queue.extend(new_tvars)
                visited |= new_tvars
        computed.add(tvar)


def compute_recursion_next_states(
    next_states: Dict[str, Dict[LAction, Set[LType]]], tvar_deps: Dict[str, Set[str]]
):
    computed = set()
    for tvar, tvar_next_states in next_states.items():
        tvar_queue = deque(tvar_deps[tvar])
        # Compute transitive closure of tvars
        visited = set(tvar_deps[tvar])
        visited.add(tvar)
        while tvar_queue:
            new_tvar = tvar_queue.popleft()
            for laction, nxt_states in next_states[new_tvar].items():
                action_next_states = tvar_next_states.setdefault(laction, set())
                action_next_states |= nxt_states
            if new_tvar not in computed:
                new_tvars = tvar_deps[new_tvar].difference(visited)
                tvar_queue.extend(new_tvars)
                visited |= new_tvars
        computed.add(tvar)


def yes_no_answer(prompt: str):
    answer = ""
    valid_answers = {"yes", "y", "n", "no"}
    while answer not in valid_answers:
        answer = input(prompt).lower()
        if answer not in valid_answers:
            print("Invalid answer, please answer with 'yes/y' or 'no/n'")
    return answer


def write_impl(
    out_dir: str, root_pkg: str, protocol_pkg: str, impl_files: Dict[str, str]
) -> None:
    impl_dir = str(Path(out_dir, root_pkg, protocol_pkg))
    if os.path.isdir(impl_dir):
        print(f"Directory '{impl_dir}' already exists")
        answer = yes_no_answer(
            "Do you want to generate implementation here and overwrite existing files? "
        )
        if answer in {"no", "n"}:
            return

    out_dir_path = Path(out_dir)
    for file, impl in impl_files.items():
        file_path = out_dir_path / file
        os.makedirs(str(file_path.parent), exist_ok=True)
        with file_path.open(mode="w") as f:
            f.write(impl)


def print_output(*args, verbose=False):
    if verbose:
        print(*args)


def main():
    parser = argparse.ArgumentParser(
        description="Tool to project Scribble protocols with mixed choice"
    )
    parser.add_argument(
        "file",
        metavar="file",
        type=str,
        help="path to the file where the scribble protocols are defined",
    )
    parser.add_argument(
        "--out-dir",
        dest="out_dir",
        type=str,
        help="path to the directory which contains the root-pkg of the project",
    )
    parser.add_argument(
        "--root-pkg",
        dest="root_pkg",
        default="GoMChoice",
        type=str,
        help="path to the directory under which to generate the implementation, relative to the out-dir",
    )
    parser.add_argument(
        "--project",
        dest="protocol",
        type=str,
        help="project the local types for the specified protocol",
    )
    parser.add_argument(
        "--gen-code-go",
        dest="codegen_proto",
        type=str,
        help="name of protocol for which to generate go implementation",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="show verbose output - all global types, projections and generated code",
    )
    args = parser.parse_args()
    try:
        protocols = scr_parser.parse_file(args.file)
        for proto_name, protocol in protocols.items():
            role = None
            try:
                print_output(f"PROTOCOL {proto_name}\n", verbose=args.verbose)
                print_output(str(protocol.gtype), verbose=args.verbose)
                projections = protocol.gtype.project(set(protocol.roles))
                print_output("Preliminary projections", verbose=args.verbose)
                projections = {
                    role: ltype.normalise() for role, ltype in projections.items()
                }

                for role, ltype in projections.items():
                    # print(f"{role}@{protocol.protocol}:\n")
                    # Compute hashes for recursive constructs:
                    # - First compute a preliminary hash where all tvars return same
                    #   constant hash
                    # - Then, propagate the hash max recursion depth - 1 times to
                    #   ensure that the hashes for recursive variables with the same structure
                    #   have the same hash
                    max_rec_depth = ltype.max_rec_depth(0)
                    ltype.hash_rec(True)
                    for i in range(max_rec_depth - 1):
                        ltype.hash_rec(False)

                    # Force the caching of the hashes, using the updated hash values for the
                    # recursive variables
                    ltype.hash()
                    pass
                    # print(str(ltype), "\n\n")
                print_output("Done", verbose=args.verbose)

                print_output("Calculating rec first actions", verbose=args.verbose)
                for role, ltype in projections.items():
                    # print(f"{role}@{protocol.protocol}:\n")
                    fst_actions = {}
                    tvar_deps = {}
                    update_tvars = {}
                    ltype.calc_fst_actions_rec(tvar_deps, fst_actions, update_tvars)
                    compute_recursion_fst_actions(fst_actions, tvar_deps)
                    ltype.set_fst_actions_rec(fst_actions)
                print_output(f"fst actions: Done", verbose=args.verbose)
                print_output("Calculating rec next_states", verbose=args.verbose)
                for role, ltype in projections.items():
                    # print(f"{role}@{protocol.protocol}:\n")
                    next_states = {}
                    tvar_deps = {}
                    update_tvars = {}
                    ltype.calc_next_states_rec(tvar_deps, next_states, update_tvars)
                    compute_recursion_next_states(next_states, tvar_deps)
                    ltype.set_next_states_rec(next_states)
                print_output(f"next states: Done", verbose=args.verbose)

                print_output("Checking projections...\n\n", verbose=args.verbose)
                for ltype in projections.values():
                    # Checking projection for one ltype will check all projections types
                    ltype.check_valid_projection()
                    break
                print_output("Normalised projections", verbose=args.verbose)
                norm_projections = {}
                print_projections = args.verbose or (
                    args.protocol is not None and args.protocol == proto_name
                )
                for role, ltype in projections.items():
                    dfa = DFA(ltype)
                    new_ltype = dfa.translate()
                    print_output(
                        f"{role}@{protocol.protocol}:\n", verbose=print_projections
                    )
                    print_output(str(new_ltype), "\n\n", verbose=print_projections)
                    norm_projections[role] = new_ltype
                print_output(
                    "\n\n=============================>\n", verbose=args.verbose
                )
                # if args.codegen_proto is not None:
                if args.codegen_proto is not None and proto_name == args.codegen_proto:
                    codegen = CodeGen(protocol.roles, protocol.protocol, args.root_pkg)
                    impl_files = codegen.gen_impl(norm_projections)
                    for file_name, impl in impl_files.items():
                        print(file_name, end=":\n\n")
                        print(impl)
                    if args.out_dir is not None:
                        write_impl(
                            args.out_dir,
                            args.root_pkg,
                            codegen.protocol_pkg,
                            impl_files,
                        )
                    print("\n\n=============================>\n")
            except Exception as e:
                name = "@".join([x for x in [role, proto_name] if x is not None])
                print("!!!!!!!!!!!!!!!!!!!!!!!!")
                print(f"Error: {name}:", repr(e))
                print("!!!!!!!!!!!!!!!!!!!!!!!!")
                print("\n=============================>\n")

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
