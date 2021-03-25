#!/usr/bin/env python3

# Author: romaktion@gmail.com
import glob
import ntpath
import os
import re
import shutil
import sys
from pathlib import Path
from pydub import AudioSegment


def get_glue_words():
    with open("glue_words.txt", 'r') as glue_words_file:
        ret = []
        for w in re.sub(r"[\r\n\t\s]*", "", glue_words_file.read()).split(","):
            if '-' in w:
                split = w.split('-')
                if len(split) > 1:
                    ret.append(split)
        return ret


walk_dir = sys.argv[1]
out_dir = walk_dir
files_to_glue_top = []
glue_words = get_glue_words()
for glue_word in glue_words:
    min_files = sys.maxsize
    files = []
    for word in glue_word:
        found = list(glob.iglob(os.path.join(walk_dir, word) + '**/*.wav', recursive=True))
        flen = len(found)
        if flen < min_files:
            min_files = flen
        files.append(found)
    files_to_glue = []
    for f in files:
        files_to_glue.append(f[:min_files])
    files_to_glue_top.append(files_to_glue)


testing_list_file = open(os.path.join(out_dir, "testing_list.txt"), 'a')
validation_list_file = open(os.path.join(out_dir, "validation_list.txt"), 'a')

# TODO: multithreading
for idx, files_to_glue in enumerate(files_to_glue_top):
    s = ""
    for gw in glue_words[idx]:
        s += gw
    d = os.path.join(out_dir, s)
    shutil.rmtree(d, ignore_errors=True)
    count = 0
    min_files = len(files_to_glue[0])
    half_min_files = min_files / 2
    while count < min_files:
        t = []
        for files in files_to_glue:
            t.append(files[count])

        Path(d).mkdir(parents=True, exist_ok=True)
        combined = AudioSegment.empty()
        out_name = ""
        for i, target in enumerate(t):
            combined += AudioSegment.from_wav(target)
            out_name += ntpath.basename(target).replace(".wav", "")
            if i < len(t) - 1:
                out_name += "_"
            else:
                out_name += ".wav"
        to_write = s + '/' + out_name + '\n'
        if combined.duration_seconds / len(s) > 0.07:
            if count > half_min_files:
                testing_list_file.write(to_write)
            else:
                validation_list_file.write(to_write)
        combined.export(os.path.join(d, out_name), format="wav")

        count += 1
