#!/usr/bin/env python3

# Author: romaktion@gmail.com
import glob
import ntpath
import os
import subprocess
import sys
from pathlib import Path

walk_dir = sys.argv[1]
out_dir = sys.argv[2]
Path(out_dir).mkdir(parents=True, exist_ok=True)

files = list(glob.iglob(walk_dir + '**/*.wav', recursive=True))

for f in files:
    process = subprocess.run(["ffmpeg", "-i", f, "-ab", "160k", "-ac", "1", "-ar", "16000"
                                 , os.path.join(out_dir, "conv_" + ntpath.basename(f))]
                             , stderr=subprocess.DEVNULL
                             , stdout=subprocess.DEVNULL
                             , stdin=subprocess.PIPE)
    if process.returncode != 0:
        print('Converting wav to wav failed for %s!' % f)
