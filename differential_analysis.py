from SBox import Sbox
from itertools import product
from tqdm import tqdm
import pickle

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

# modify accordingly
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

# compute the active sbox number table of 16-bit differential
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


from multiprocessing import Process
def multi_work(iter_function, totalProcess = 8, lenList = 2**16, base=0):
    gap = lenList // totalProcess
    process_list = []
    print("Totally %d processes" % totalProcess)

    for i in range(totalProcess):
        process = Process(target=iter_function, args=(base + i * gap, base + (i + 1) * gap))
        process.start()
        process_list.append(process)

    for t in process_list:
        t.join()
    print("Exiting Main Process")
    
# a global table : differential -> the number of active sbox of the input differential 
ACTIVE_SBOX_TABLE = compute_active_sbox_table()

# count the number of of active sbox of the input differential characteristics
def count_active_sbox(dc):
    return sum([ACTIVE_SBOX_TABLE[diff] for diff in dc])

# the differential characteristic analyzer
class CipherN_analyzer():
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
    sp_table = None
    differential_characteristic_table = []

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
        
    def compute_sbox_perm_table(self, saved  = True, filter = True):
        sp_table = []
        for i in tqdm(range(2**16)):
            table = self.compute_sbox_perm_diff(i,filter)
            sp_table.append(table)
        if saved:
            pickle.dump(sp_table, open("./sp_table.pickle", "wb"))
        self.sp_table = sp_table
        return sp_table

    def load_sbox_perm_table(self, path="./sp_table.pickle"):
        try:
            with open(path, "rb") as f:
                self.sp_table = pickle.load(f)
            return True
        except Exception as error:
            print(error)
            return False

    def compute_all_differential_characteristics(self):
        # have been computed 
        table = []
        for i in tqdm(range(2**16)):
            differential_characteristics_table = [[([i],0, 1)]]
            # ([i],1): ([input_diff,..,output_diff], the diff prob)
            for Round in range(1, self.cipherN_paras["NUM_ROUNDS"] + 1):
                diff_table = []
                for item in differential_characteristics_table[Round - 1]:
                    prob = item[2]
                    active_sbox_num = item[1]
                    differential_characteristic = item[0][:]  # copy by slice
                    current_diff = differential_characteristic[-1]
                    # if it's the last round, we will not add the active sbox num since it's over
                    # new_active_sbox_num : new_diff is not included
                    new_active_sbox_num = active_sbox_num + ACTIVE_SBOX_TABLE[current_diff]
                    next_diffs = self.sp_table[current_diff]
                    for diff, p in next_diffs:
                        new_prob = prob*p
                        if new_prob < self.cipherN_paras["PATH_MIN_PROB"]:
                            # drop low probablity item
                            continue
                        else:
                            new_diff = differential_characteristic + [diff]
                            diff_table.append((new_diff, new_active_sbox_num, new_prob))
                differential_characteristics_table.append(diff_table)
            table.append(differential_characteristics_table)
        self.differential_characteristic_table.extend(table)
        return table
        
    def sort_differential_characteristics_by_prob(self, round_num=5, topN=10):
        if len(self.differential_characteristic_table) != 0:
            all_input_differential_characteristics = self.differential_characteristic_table
        else:
            all_input_differential_characteristics = self.compute_all_differential_characteristics()
        final_table = []
        for input_diff, differential_characteristic_i in enumerate(all_input_differential_characteristics):
            # item in  differential_characteristics[round_num] is:  (dc, dc_prob), sorted by dc_prob
            differential_characteristic_i_of_roundN = differential_characteristic_i[round_num]
            if len(differential_characteristic_i_of_roundN) == 0:
                # bad differential_characteristic prob < 2^-16
                continue
            else:
                final_table += differential_characteristic_i_of_roundN
        res = sorted(final_table, key=lambda x: (-x[-1],x[1]))[1:topN+1]
        
        print(f"[+] Top {topN}/{len(final_table)} differential_characteristic (dc) of round {round_num} sorted by dc_prob")
        for i in range(min(topN, len(res))):
            # undo the permutation in the last round
            res[i][0][-1] = do_inv_pbox(res[i][0][-1])
            print("*"*32,f"Top {i+1}","*"*32)
            print(f"dc = {tuple([parse_Sbox_input(s) for s in res[i][0]])}")
            print(f"dc = {res[i][0]}")
            print(f"dc_probablity = {res[i][-1]}")
            print(f"active_sbox_num = {res[i][1]}")
        print()
        
            
    def sort_differential_characteristics_by_active_sbox_num(self, round_num=5, topN=10):
        if len(self.differential_characteristic_table) != 0:
            all_input_differential_characteristics = self.differential_characteristic_table
        else:
            all_input_differential_characteristics = self.compute_all_differential_characteristics()
        final_table = []
        for input_diff, differential_characteristic_i in enumerate(all_input_differential_characteristics):
            # item in  differential_characteristics[round_num] is:  (dc, dc_prob), sorted by dc_prob
            differential_characteristic_i_of_roundN = differential_characteristic_i[round_num]
            if len(differential_characteristic_i_of_roundN) == 0:
                # bad differential_characteristic prob < 2^-16
                continue
            else:
                final_table += differential_characteristic_i_of_roundN
        res = sorted(final_table, key=lambda x: (x[1],-x[-1]))[1:topN+1]
            
        print(f"[+] Top {topN} differential_characteristic (dc) of round {round_num} sorted by active_sbox_num")
        for i in range(min(topN, len(res))):
            # undo the permutation in the last round
            res[i][0][-1] = do_inv_pbox(res[i][0][-1])
            print("*"*32,f"Top {i+1}","*"*32)
            print(f"dc = {tuple([parse_Sbox_input(s) for s in res[i][0]])}")
            print(f"dc = {res[i][0]}")
            print(f"dc_probablity = {res[i][-1]}")
            print(f"active_sbox_num = {res[i][1]}")
        print()

if __name__ == "__main__":
    analyzer = CipherN_analyzer()
    if not analyzer.load_sbox_perm_table():
        analyzer.compute_sbox_perm_table()
    # analyzer.compute_sbox_perm_table()
    # analyzer.compute_all_differential_characteristics()
    for nround in range(1,11):
        analyzer.sort_differential_characteristics_by_prob(nround, 10)
        analyzer.sort_differential_characteristics_by_active_sbox_num(nround, 10)