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
        for word in re.sub(r"[\r\n\t\s]*", "", glue_words_file.read()).split(","):
            if '-' in word:
                split = word.split('-')
                if len(split) > 1:
                    ret.append(split)
        return ret


def perform_glue_words(targets, to_dir):
    Path(to_dir).mkdir(parents=True, exist_ok=True)
    combined = AudioSegment.empty()
    out_name = ""
    for i, target in enumerate(targets):
        combined += AudioSegment.from_wav(target)
        out_name += ntpath.basename(target).replace(".wav", "")
        if i < len(targets) - 1:
            out_name += "_"
        else:
            out_name += ".wav"
    combined.export(os.path.join(to_dir, out_name), format="wav")


walk_dir = sys.argv[1]
out_dir = sys.argv[2]
shutil.rmtree(out_dir, ignore_errors=True)
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

# TODO: multithreading
for idx, files_to_glue in enumerate(files_to_glue_top):
    s = ""
    for gw in glue_words[idx]:
        s += gw
    d = os.path.join(out_dir, s)
    count = 0
    min_files = len(files_to_glue[0])
    while count < min_files:
        t = []
        for files in files_to_glue:
            t.append(files[count])
        perform_glue_words(t, d)
        count += 1
