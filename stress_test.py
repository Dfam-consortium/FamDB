#!/usr/bin/env python3

import subprocess

# file_dir = "/local/agray/dfam_exp"
file_dir = "/home/agray/FamDB/medium_dfam"

def finalize_args(args):
    args.insert(0, "./famdb.py")
    args.insert(1, "--db_dir")
    args.insert(2, file_dir)
 

commands = [
    ["families", "-d", "human"],
    ["families", "-a", "human"],
    ["families", "-ad", "mus musculus"],
    ["lineage", "-ad", "mus musculus"]
]

for args in commands:
    finalize_args(args)
    file_str = "./stress_tests/"+"_".join(args[3:])+".out"
    with open(file_str, "w") as outfile:
        subprocess.run(args, stdout=outfile, stderr=subprocess.PIPE)

