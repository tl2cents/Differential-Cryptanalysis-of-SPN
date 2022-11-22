#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# A basic Substitution-Permutation Network cipher, implemented by following
# 'A Tutorial on Linear and Differential Cryptanalysis'
# by Howard M. Heys
#
# modified by tl2cents 2022 11.22
# Original author: Chris Hicks
# Original source : https://github.com/physics-sec/Differential-Cryptanalysis/blob/master/basic_SPN.py
#
# Basic SPN cipher which takes as input a 16-bit input block and has 4 rounds.
# Each round consists of (1) substitution (2) transposition (3) key mixing

import hashlib
import os

blockSize = 16
verboseState = False

# (1) Substitution: 4x4 bijective, one sbox used for all 4 sub-blocks of size 4. Nibble wise
sbox = {0: 0xE, 1: 0x4, 2: 0xD, 3: 0x1, 4: 0x2, 5: 0xF, 6: 0xB, 7: 0x8, 8: 0x3,
        9: 0xA, 0xA: 0x6, 0xB: 0xC, 0xC: 0x5, 0xD: 0x9, 0xE: 0x0, 0xF: 0x7}  # key:value
sbox_inv = {0xE: 0, 0x4: 1, 0xD: 2, 0x1: 3, 0x2: 4, 0xF: 5, 0xB: 6, 0x8: 7,
            0x3: 8, 0xA: 9, 0x6: 0xA, 0xC: 0xB, 0x5: 0xC, 0x9: 0xD, 0x0: 0xE, 0x7: 0xF}

# Apply sbox (1) to a 16 bit state and return the result


def apply_sbox(state, sbox):
    subStates = [state & 0x000f, (state & 0x00f0) >>
                 4, (state & 0x0f00) >> 8, (state & 0xf000) >> 12][::-1]
    for idx, subState in enumerate(subStates):
        subStates[idx] = sbox[subState]
    return subStates[0] | subStates[1] << 4 | subStates[2] << 8 | subStates[3] << 12


# (2) Permutation. Applied bit-wise
pbox = {0: 0, 1: 4, 2: 8, 3: 12, 4: 1, 5: 5, 6: 9, 7: 13,
        8: 2, 9: 6, 10: 10, 11: 14, 12: 3, 13: 7, 14: 11, 15: 15}
pbox_inv = {0: 0, 4: 1, 8: 2, 12: 3, 1: 4, 5: 5, 9: 6, 13: 7,
            2: 8, 6: 9, 10: 10, 14: 11, 3: 12, 7: 13, 11: 14, 15: 15}

# (3) Key mixing: bitwise XOR between round subkey and data block input to round
# Key schedule: independant random round keys.
# We take the sha-hash of a 128-bit 'random' seed and then take the first (nround*16)-bits
# of the output as out round keys K1-KN (Each 16 bits long). (not secure, this is just a demo)


def keyGeneration(split_length = blockSize):
    k = hashlib.sha512(os.urandom(64)).hexdigest()[2:]
    sub_len = split_length//4
    sub_num = len(k)//sub_len
    return [k[sub_len*i:sub_len*(i+1)] for i in range(sub_num)]

# Simple SPN Cipher encrypt function


def encrypt(pt, k, nround=4):
    assert len(k) >= nround + 1, "Sub keys not enough!"
    state = pt
    if verboseState:
        print('**pt = {:04x}**'.format(state))

    subKeys = [int(subK, 16) for subK in k[:nround + 1]]
    if verboseState:
        print('**subkeys = {}**'.format(subKeys))
    # First nround - 1 rounds of sinple SPN cipher
    for roundN in range(0, nround-1):

        if verboseState:
            print(roundN, end=' ')
        # XOR state with round key (3, subkeys 1,..,4)
        state = state ^ subKeys[roundN]
        if verboseState:
            print(hex(state), end=' ')

        # Break state into nibbles, perform sbox on each nibble, write to state (1)
        state = apply_sbox(state, sbox)
        if verboseState:
            print(hex(state), end=' ')

        # Permute the state bitwise (2)
        state_temp = 0
        for bitIdx in range(0, blockSize):
            if (state & (1 << bitIdx)):
                state_temp |= (1 << pbox[bitIdx])
        state = state_temp
        if verboseState:
            print(hex(state))

    # Final round of SPN cipher (k_{n-1}, sbox, k_n)
    state = state ^ subKeys[-2]  # penultimate subkey (key 4) mixing
    if verboseState:
        print(str(3), hex(state), end=' ')
    state = apply_sbox(state, sbox)
    if verboseState:
        print(hex(state), end=' ')
    state = state ^ subKeys[-1]  # Final subkey (key 5) mixing
    if verboseState:
        print(hex(state))
    if verboseState:
        print('**ct = {:04x}**'.format(state))

    return state

# Simple SPN Cipher decrypt function
def decrypt(ct, k, nround=4):
    state = ct
    if verboseState:
        print('**ct = {:04x}**'.format(state))

    # Derive round keys
    subKeys = [int(subK, 16) for subK in k[:nround + 1]]
    if verboseState:
        print('**subkeys = {}**'.format(subKeys))
        
    if verboseState:
            print(nround-1, end=' ')
            
    if verboseState:
        print(hex(state), end=' ')

    # Undo final round key
    state = state ^ subKeys[-1]
    if verboseState:
        print(hex(state), end=' ')

    # Apply inverse s-box
    state = apply_sbox(state, sbox_inv)
    if verboseState:
        print(hex(state))
    state = state ^ subKeys[-2]

    # Undo first nround -1  rounds of simple SPN cipher
    for roundN in range(nround-2, -1, -1):

        if verboseState:
            print(roundN, end=' ')
            
        # Un-permute the state bitwise (2)
        state_temp = 0
        for bitIdx in range(0, blockSize):
            if (state & (1 << bitIdx)):
                state_temp |= (1 << pbox_inv[bitIdx])
        state = state_temp
        if verboseState:
            print(hex(state), end=' ')

        # Apply inverse s-box
        state = apply_sbox(state, sbox_inv)
        if verboseState:
            print(hex(state), end=' ')
            
           # XOR state with round key (3, subkeys 4,..,0)
        state = state ^ subKeys[roundN]
        if verboseState:
            print(hex(state))
    return state


if __name__ == "__main__":
    key = keyGeneration()
    print(f"[+] subkeys:   {key}")
    msg = int.from_bytes(b"12", "big")
    print(f"[+] msg:   {msg}")
    enc_msg = encrypt(msg, key,10)
    print(f"[+] enc_msg:   {bytes.fromhex(hex(enc_msg)[2:].zfill(4))}")
    dec_msg = decrypt(enc_msg, key,10)
    print(f"[+] dec_msg:   {bytes.fromhex(hex(dec_msg)[2:].zfill(4))}")