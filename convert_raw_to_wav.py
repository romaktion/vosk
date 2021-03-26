#!/usr/bin/env python3

# Author: romaktion@gmail.com
import glob
import multiprocessing
import ntpath
import os
import subprocess
import sys
from concurrent import futures
from pathlib import Path
import word_cutter


def convert(files_list):
    for f in files_list:
        process = subprocess.run(["ffmpeg", "-f", "s16le", "-i", f, "-ab", "160k", "-ac", "1", "-ar", "16000"
                                     , os.path.join(out_dir, "conv_" + ntpath.basename(f).replace(".raw", ".wav"))]
                                 , stderr=subprocess.DEVNULL
                                 , stdout=subprocess.DEVNULL
                                 , stdin=subprocess.PIPE)
        if process.returncode != 0:
            print('Converting wav to wav failed for %s!' % f)


walk_dir = sys.argv[1]
out_dir = sys.argv[2]
Path(out_dir).mkdir(parents=True, exist_ok=True)

files = list(glob.iglob(walk_dir + '**/*.raw', recursive=True))
if len(files) == 0:
    print("files is empty!")
    exit(1)
cpu_amount = multiprocessing.cpu_count() \
    if len(files) >= multiprocessing.cpu_count() \
    else len(files)
split_files = word_cutter.split_list(files, cpu_amount)

with futures.ThreadPoolExecutor(max_workers=cpu_amount) as executor:
    process_futures = dict((executor.submit(convert, fl), fl) for fl in split_files)
    for pf in futures.as_completed(process_futures):
        if pf.exception() is not None:
            print('generated an exception: %s' % pf.exception())
        else:
            print("Done!")
