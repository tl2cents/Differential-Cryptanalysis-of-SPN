"""
A repository for Sbox analysis. Similar to the sage.crypto.Sbox library.
You can use this library to analyze any Sbox.

Author: tl2cents 2022.11.22
"""

import numpy as np
from copy import deepcopy

# @sbox example dict
# sbox =     {0:0xE, 1:0x4, 2:0xD, 3:0x1, 4:0x2, 5:0xF, 6:0xB, 7:0x8, 8:0x3, 9:0xA, 0xA:0x6, 0xB:0xC, 0xC:0x5, 0xD:0x9, 0xE:0x0, 0xF:0x7} #key:value
# sbox_inv = {0xE:0, 0x4:1, 0xD:2, 0x1:3, 0x2:4, 0xF:5, 0xB:6, 0x8:7, 0x3:8, 0xA:9, 0x6:0xA, 0xC:0xB, 0x5:0xC, 0x9:0xD, 0x0:0xE, 0x7:0xF}

class Sbox():
    box_dict = None
    box_permutation = None
    box_size = None
    diff_table = None
    diff_prob_table = None
    max_diff_prob = None

    def __init__(self, box: dict) -> None:
        box_size = len(box)
        box_permutation = [box[s] for s in box]
        assert sorted(box_permutation) == list(
            range(box_size)), "Sbox must be a permutation!"
        self.box_dict = deepcopy(box)
        self.box_size = box_size
        self.box_permutation = box_permutation

    def difference_distribution_table(self):
        if type(self.diff_table) != type(None):
            return self.diff_table
        table = np.zeros((self.box_size, self.box_size), dtype=int)
        for input_diff in range(self.box_size):
            for x_1 in range(self.box_size):
                x_2 = x_1 ^ input_diff
                out_diff = self.box_dict[x_1] ^ self.box_dict[x_2]
                table[input_diff, out_diff] += 1
        self.diff_table = table
        self.diff_prob_table = table/self.box_size
        return table

    def difference_prob_table(self):
        if type(self.diff_prob_table) != type(None):
            return self.diff_prob_table
        return self.difference_distribution_table()/self.box_size

    def maximal_difference_probability(self):
        # we will not consider zero difference
        return np.max(self.diff_prob_table[1:, :])

    def fetch_max_prob_io(self):
        # return the (input difference, output difference) with max maximal difference probability
        distribution_table = self.difference_distribution_table()[1:, :]
        max_prob = np.max(distribution_table)
        io_list = []
        for inpu_diff in range(self.box_size-1):
            for out_diff in range(self.box_size):
                if distribution_table[inpu_diff, out_diff] == max_prob:
                    io_list.append((inpu_diff, out_diff))
        return max_prob/self.box_size, io_list

    def difference_prob_dict(self):
        P = self.difference_prob_table()
        diff_dict = {}
        for i in range(self.box_size):
            # diff_dict[input_diff] : [(out_diff,prob)]
            diff_dict.setdefault(i, [])
            for j in range(self.box_size):
                if P[i][j] != 0:
                    diff_dict[i].append((j, P[i][j]))
        return diff_dict

    def difference_distribution_dict(self):
        P = self.difference_distribution_table()
        diff_dict = {}
        for i in range(self.box_size):
            # diff_dict[input_diff] : [(out_diff,prob)]
            diff_dict.setdefault(i, [])
            for j in range(self.box_size):
                if P[i][j] != 0:
                    diff_dict[i].append((j, P[i][j]))
        return diff_dict
    
if __name__ == "__main__":
    print("Try this on your on")