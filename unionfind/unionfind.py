from typing import List, Any, Set, Dict


class UnionFind:
    def __init__(self):
        self.uid = 0
        self.elems: Dict[str, Elem] = {}
        self.leaders: Set[int] = set()
        self.all_subsets: Dict[int, Elem] = {}

    def add(self, participants: List[str], branch: Any):
        if participants[0] in self.elems and participants[1] in self.elems:
            root1 = self.elems[participants[0]].find_root()
            root2 = self.elems[participants[1]].find_root()
            if root1 == root2:
                self.elems[participants[0]].add(branch)
            else:
                new_root, old_root = root1.union(root2)
                new_root.add(branch)
                self.leaders.remove(old_root.get_uid())

        elif participants[0] in self.elems:
            self.elems[participants[0]].add(branch)
            self.elems[participants[1]] = self.elems[participants[0]]
            pass
        elif participants[1] in self.elems:
            self.elems[participants[1]].add(branch)
            self.elems[participants[0]] = self.elems[participants[1]]
        else:
            elem = Elem(self.uid, branch)
            self.leaders.add(self.uid)
            self.all_subsets[self.uid] = elem
            self.elems[participants[0]] = elem
            self.elems[participants[1]] = elem
            self.uid += 1
            pass

    def get_subsets(self):
        return tuple(self.all_subsets[leader].get_values() for leader in self.leaders)


class Elem:
    def __init__(self, uid: int, value: Any):
        self.uid = uid
        self.values = [value]
        self.parent = self

    def __len__(self):
        return len(self.values)

    def add(self, value):
        root = self.find_root()
        root.values.append(value)

    def find_root(self):
        root = self
        while root.parent != root:
            root = root.parent

        # Path compression
        node = self
        while node.parent != root:
            node, node.parent = node.parent, root
        return root

    def union(self, other):
        # other: Elem
        # Assumes both nodes are roots
        root1 = self.find_root()
        root2 = other.find_root()

        if len(root1) < len(root2):
            root1, root2 = root2, root1

        root1.values += root2.values
        root2.parent = root1

        return root1, root2

    def get_uid(self):
        return self.uid

    def get_values(self):
        return self.values
