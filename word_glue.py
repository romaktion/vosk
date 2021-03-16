#!/usr/bin/env python3

# Author: romaktion@gmail.com
import os
import re
import sys
from collections import namedtuple


def get_glue_words():
    with open("glue_words.txt", 'r') as glue_words_file:
        ret = []
        for word in re.sub(r"[\r\n\t\s]*", "", glue_words_file.read()).split(","):
            if '-' in word:
                split = word.split('-')
                if len(split) == 2:
                    t = (str(split[0]).lower(), str(split[1]).lower())
                    ret.append(t)
        return ret

walk_dir = os.path.abspath(sys.argv[1])

