from collections import OrderedDict, deque
from typing import Set, Dict

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
    args = parser.parse_args()
    try:
        protocols = scr_parser.parse_file(args.file)
        for proto_name, protocol in protocols.items():
            role = None
            try:
                print(f"PROTOCOL {proto_name}\n")
                print(str(protocol.gtype))
                projections = protocol.gtype.project(set(protocol.roles))
                print("Preliminary projections")
                projections = {
                    role: ltype.normalise() for role, ltype in projections.items()
                }

                for role, ltype in projections.items():
                    # print(f"{role}@{protocol.protocol}:\n")
                    # Compute hashes for recursive constructs:
                    # - First compute a preliminary hash where all tvars return same
                    #   constant hash
                    ltype.hash_rec(True)
                    # - Recompute the hash of the recursions using their preliminary
                    #   hashes of each recursive constuct as the hash for each tvar
                    ltype.hash()
                    # print(str(ltype), "\n\n")
                print("Done")

                print("Calculating rec first actions")
                for role, ltype in projections.items():
                    # print(f"{role}@{protocol.protocol}:\n")
                    fst_actions = {}
                    tvar_deps = {}
                    update_tvars = {}
                    ltype.calc_fst_actions_rec(tvar_deps, fst_actions, update_tvars)
                    compute_recursion_fst_actions(fst_actions, tvar_deps)
                    ltype.set_fst_actions_rec(fst_actions)
                print(f"fst actions: Done")
                print("Calculating rec next_states")
                for role, ltype in projections.items():
                    # print(f"{role}@{protocol.protocol}:\n")
                    next_states = {}
                    tvar_deps = {}
                    update_tvars = {}
                    ltype.calc_next_states_rec(tvar_deps, next_states, update_tvars)
                    compute_recursion_next_states(next_states, tvar_deps)
                    ltype.set_next_states_rec(next_states)
                print(f"next states: Done")

                print("Checking projections...\n\n")
                for ltype in projections.values():
                    # Checking projection for one ltype will check all projections types
                    ltype.check_valid_projection()
                    break
                print("Normalised projections")
                for role, ltype in projections.items():
                    dfa = DFA(ltype)
                    new_ltype = dfa.translate()
                    print(f"{role}@{protocol.protocol}:\n")
                    print(str(new_ltype), "\n\n")
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
