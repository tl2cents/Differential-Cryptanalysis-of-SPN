from SBox import Sbox
from itertools import product, combinations
import random
from tqdm import tqdm
import pickle
import networkx as nx
import matplotlib.pyplot as plt


def generate_Sbox(nbits = 4):
    # return S and S_INV
    L = list(range(2**nbits))
    random.shuffle(L)
    return {i:j for i,j in enumerate(L)},{j:i for i,j in enumerate(L)}

def generate_permutation(LEN = 16):
    # return P and P_inv
    L = list(range(LEN))
    random.shuffle(L)
    return {i:j for i,j in enumerate(L)},{j:i for i,j in enumerate(L)}

    
# (1) Substitution: 4x4 bijective, one sbox used for all 4 sub-blocks of size 4. Nibble wise
sbox = {0: 0xE, 1: 0x4, 2: 0xD, 3: 0x1, 4: 0x2, 5: 0xF, 6: 0xB, 7: 0x8, 8: 0x3,
        9: 0xA, 0xA: 0x6, 0xB: 0xC, 0xC: 0x5, 0xD: 0x9, 0xE: 0x0, 0xF: 0x7}  # key:value
sbox_inv = {0xE: 0, 0x4: 1, 0xD: 2, 0x1: 3, 0x2: 4, 0xF: 5, 0xB: 6, 0x8: 7,
            0x3: 8, 0xA: 9, 0x6: 0xA, 0xC: 0xB, 0x5: 0xC, 0x9: 0xD, 0x0: 0xE, 0x7: 0xF}

# (2) Permutation. Applied bit-wise
pbox = {0: 0, 1: 4, 2: 8, 3: 12, 4: 1, 5: 5, 6: 9, 7: 13,
        8: 2, 9: 6, 10: 10, 11: 14, 12: 3, 13: 7, 14: 11, 15: 15}
pbox_inv = {0: 0, 4: 1, 8: 2, 12: 3, 1: 4, 5: 5, 9: 6, 13: 7,
            2: 8, 6: 9, 10: 10, 14: 11, 3: 12, 7: 13, 11: 14, 15: 15}

# if you wanna test new sboxes and pboxes, you can set new_box = True
new_box = False
if new_box:
    sbox,sbox_inv = generate_Sbox()
    pbox,pbox_inv = generate_permutation()
    S = Sbox(sbox)
    print(f"[+] sbox = {sbox} \n[+] pbox = {pbox}")
    
    print(f"[+] new box table :\n {S.difference_distribution_table() = }")
# modify accordingly
def do_sbox(number):
    return sbox[number]

# modify accordingly
def do_inv_sbox(number):
    return sbox_inv[number]

# modify accordingly
def do_pbox(number):
    number_temp = 0
    for bitIdx in range(0, 16):
        if (number & (1 << bitIdx)):
            number_temp |= (1 << pbox[bitIdx])
    number = number_temp
    return number


def do_inv_pbox(state):
    state_temp = 0
    for bitIdx in range(0, 16):
        if (state & (1 << bitIdx)):
            state_temp |= (1 << pbox_inv[bitIdx])
    state = state_temp
    return state

# convert an integer to the input of Sbox
def parse_Sbox_input(input_number, SBOX_BITS=4, NUM_SBOXES=4):
    mask = (1 << SBOX_BITS) - 1
    STATE = []
    for i in range(NUM_SBOXES):
        STATE.append(mask & input_number)
        input_number = input_number >> SBOX_BITS
    return STATE[::-1]

# merge the output of Sbox to an integer
def merge_Sbox_output(STATE, SBOX_BITS=4, NUM_SBOXES=4):
    assert len(STATE) == NUM_SBOXES
    out_number = 0
    for state in STATE:
        out_number = (out_number << SBOX_BITS) | state
    return out_number


def compute_active_sbox_table():
    table = []
    for i in range(2**16):
        diff_ls = parse_Sbox_input(i)
        cnt = 0
        for sub_diff in diff_ls:
            if sub_diff !=0:
                cnt+=1
        table.append(cnt)
    return table

# setup directed graph
namespace = globals()
def draw_directed_graph(source, title):
    # source is a list like [ (start node, [(end node, edge weight)]) ]
    G1 = nx.DiGraph()
    # load
    for item in source:
        start_node = item[0]
        edges = item[1] 
        for end_node, w in edges:
            print(start_node, end_node, w)
            G1.add_edge(start_node, end_node, weight = w)
    
    # weight classify
    for i in [0,20,40,60,80]:
        ii = i / 100
        namespace['E%d' % (i)] = [
            (u, v) for (u, v, d) in G1.edges(data=True
            ) if (d['weight'] >= ii)&(d['weight'] < ii + 0.2)]
    
    # position
    pos = nx.shell_layout(G1)
    plt.rcParams['figure.figsize']= (25, 25)
    # student_pos = nx.spring_layout(G1,k=1.5)
    # nx.draw_networkx(G1,student_pos,arrowsize=5)
    # nodes
    nx.draw_networkx_nodes(G1, pos, node_size = 800, alpha = 0.2,
                           node_color='dodgerblue',node_shape='o')
    
    # lines
    for i in [0,20,40,60,80]:
        ii = i / 100 + 0.05
        nx.draw_networkx_edges(G1, pos, 
                              edgelist = namespace['E%d' % (i)],
                           width = 2, edge_color = 'dodgerblue', alpha = ii, 
                           arrowstyle = "->",arrowsize = 10)
    # texts
    nx.draw_networkx_labels(G1, pos, font_size= 8, 
                            font_family='sans-serif', 
                            font_color = 'k')
    # show and save
    plt.axis('off')
    plt.show()
    plt.savefig(title + ".png")
    
ACTIVE_SBOX_TABLE = compute_active_sbox_table()
def count_active_sbox(dc):
    return sum([ACTIVE_SBOX_TABLE[diff] for diff in dc])

class active_sbox_analyzr():
    cipherN_paras = {
        "NUM_ROUNDS": 10,
        "SBOX_BITS": 4,
        "NUM_SBOXES": 4,
        "MIN_PROB": 0.01,
        "PATH_MIN_PROB": 1/2**16,
        "Sbox": sbox,
        "Pbox": pbox,
        "Sbox_INV": sbox_inv,
        "Pbox_INV": pbox_inv,
        "do_sbox": do_sbox,
        "do_inv_sbox": do_inv_sbox,
        "do_pbox": do_pbox,
        "do_inv_pbox": do_inv_pbox
    }

    def __init__(self, cipherN_paras = None) -> None:
        if cipherN_paras != None:
            self.cipherN_paras = cipherN_paras
        self.Sbox = Sbox(self.cipherN_paras["Sbox"])
        self.Sbox_difference_table = self.Sbox.difference_distribution_dict()
       
    def compute_sbox_perm_diff(self, IN_NUM, filter=True):
        # IN_NUM: the input differential
        # IN_STATE is a list of 4 4-bit number in this cipher
        IN_STATE = parse_Sbox_input(
            IN_NUM, self.cipherN_paras["SBOX_BITS"], self.cipherN_paras["NUM_SBOXES"])
        OUT_STATE = [self.Sbox_difference_table[state] for state in IN_STATE]
        temp_table = product(*OUT_STATE)
        result_table = []
        for item in temp_table:
            prob = 1
            out_state = []
            for out_diff, p in item:
                out_state.append(out_diff)
                prob *= p
            prob = prob / \
                (1 << (self.cipherN_paras["SBOX_BITS"]
                 * self.cipherN_paras["NUM_SBOXES"]))
            if filter and prob < self.cipherN_paras["MIN_PROB"]:
                # drop this item
                continue
            out_number = merge_Sbox_output(
                out_state, self.cipherN_paras["SBOX_BITS"], self.cipherN_paras["NUM_SBOXES"])
            permed_state = do_pbox(out_number)
            result_table.append((permed_state, prob))
        return result_table
    
    def set_up_directed_graph(self, filter_bound = 1):
        """_summary_
        We view all the input differentials (s1,s2,s3,s4) as nodes in directed_graph
        After one zeta function (sbox and permutation), input differential -> output differential, an edge with weight = probablity
        We only consider the differentials with exactly one active box (or set the parameter filter_bound)
        Returns:
            dict: key: start node, valus: [(end node, edge weight)]) ]
        """
        edges_table = {}
        for IN_NUM in range(1 , 1 << (self.cipherN_paras["SBOX_BITS"]*self.cipherN_paras["NUM_SBOXES"])):
                if ACTIVE_SBOX_TABLE[IN_NUM] > filter_bound :
                    continue
                OUT_NUMS = self.compute_sbox_perm_diff(IN_NUM,False)
                candidate = []
                for OUT_NUM, prob in OUT_NUMS:
                    if ACTIVE_SBOX_TABLE[OUT_NUM] > filter_bound:
                        continue
                    else:
                        candidate.append((OUT_NUM,prob))
                # print(f"{IN_NUM = } ,{candidate = }")
                edges_table.setdefault(IN_NUM,candidate)
        return edges_table
    
    def draw_directed_graph_of_active_sbox(self, filter_bound = 1):
        # Note , the filter_bound is the upper bound for active box number\
        # bound 2 is too large to be drawed
        source = self.set_up_directed_graph(filter_bound)
        draw_directed_graph(source,"Directed Graph of Active Sbox")
        
    def find_circle_of_one_active_sbox_path(self):
        source = self.set_up_directed_graph()
        G = nx.DiGraph()
        # load
        for start_node in source:
            edges = source[start_node]
            G.add_node(start_node)
            for end_node, w in edges:
                G.add_edge(start_node, end_node)
        print(f"[+] {len(G.nodes()) = }")
        print(f"[+] {len(G.edges()) = }")
        
        cs = list(nx.simple_cycles(G))
        if len(cs) != 0 :
            print("[+] circle found")
            for circle in cs:
                print(f"[+] {circle = } with avg_active_sbox_num =  {1.0}")
            return cs
        else:
            try:
                path = nx.find_cycle(G)
                print("[+] circle found")
                return  path
            except:
                print("[+] no circle found")
                dag_longest_path = nx.dag_longest_path(G)
                print(f"[+] {dag_longest_path = }")
                
    def find_circle_with_extra_n_active_sbox_path(self, active_num_ls = [2,3], extra_nodes_num = 2):
        source = self.set_up_directed_graph(filter_bound = max(active_num_ls))
        G = nx.DiGraph()
        # load all one active_sbox
        set_of_n_active_diffs = [x for x in source if ACTIVE_SBOX_TABLE[x] in active_num_ls]
        set_of_1_active_diff = [x for x in source if ACTIVE_SBOX_TABLE[x]==1]
        assert len(set_of_1_active_diff) == 4*15
        candidates = combinations(set_of_n_active_diffs, extra_nodes_num)
        
        for start_node in set_of_1_active_diff:
            G.add_node(start_node)
            edges = source[start_node]
            for end_node, w in edges:
                if end_node in set_of_1_active_diff:
                    G.add_edge(start_node, end_node, weight = ACTIVE_SBOX_TABLE[start_node] + ACTIVE_SBOX_TABLE[end_node])
        print("[+] Nodes number : " , len(G.nodes()))
        print("[+] Edges number : " , len(G.edges())) 
        
        best_circle = (None, 4)
        for candidate in candidates:
            for start_node in candidate:
                # add edges with start node = new node
                edges = source[start_node]
                G.add_node(start_node)
                for end_node, w in edges:
                    if ACTIVE_SBOX_TABLE[end_node] == 2 and end_node not in candidate:
                        continue
                    G.add_edge(start_node, end_node, weight = ACTIVE_SBOX_TABLE[start_node] + ACTIVE_SBOX_TABLE[end_node])
            for start_node in set_of_1_active_diff:
                # add edges with start node = old node
                edges = source[start_node]
                for end_node, w in edges:
                    if end_node not in candidate:
                        continue
                    G.add_edge(start_node, end_node, weight = ACTIVE_SBOX_TABLE[start_node] + ACTIVE_SBOX_TABLE[end_node])
        
            simple_cycles = list(nx.simple_cycles(G))
            if len(simple_cycles) == 0:
                for start_node in candidate:
                    G.remove_node(start_node)
                continue
            for circle in simple_cycles:
                avg_active_sbox = count_active_sbox(circle)/len(circle)
                if best_circle[1] >= avg_active_sbox:
                    best_circle = (circle,avg_active_sbox)
                    print("[+] circle with avg_active_sbox " , best_circle)
            for start_node in candidate:
                G.remove_node(start_node)

if __name__ == "__main__":
    analyzer = active_sbox_analyzr()
    analyzer.find_circle_of_one_active_sbox_path()
    # analyzer.find_circle_with_extra_n_active_sbox_path([2,3],2)
    