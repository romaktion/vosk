#!/usr/bin/env python3

# Author: romaktion@gmail.com
import glob
import ntpath
import os
import sys
from pathlib import Path
import word_cutter
import random
from shutil import copyfile

walk_dir = sys.argv[1]
out_dir = sys.argv[2]
Path(out_dir).mkdir(parents=True, exist_ok=True)

files = list(glob.iglob(walk_dir + '**/*.wav', recursive=True))
if len(files) == 0:
    print("files is empty!")
    exit(1)

split_files = word_cutter.split_list(files, 74)

for sf in split_files:
    random.shuffle(sf)
    for f in sf[:int(144 / 2)]:
        copyfile(f, os.path.join(out_dir, ntpath.basename(f)))

print("Done!")
