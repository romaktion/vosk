#!/usr/bin/env python3

# Author: romaktion@gmail.com
import glob
import multiprocessing
import ntpath
import os
import shutil
import subprocess
import sys
from concurrent import futures
from pathlib import Path

import word_cutter

process_txt_files_threshold = 100000
max_audio_files = 25000


def process_txt_files_list2(in_txt_files_list, search_words):
    global found_files_list
    global last_count_all_txt_files
    global count_all_txt_files
    global all_txt_files_list
    global process_txt_files_threshold
    global out_dir
    global max_audio_files
    for txt_file in in_txt_files_list:
        if len(found_files_list) >= max_audio_files:
            return
        count_all_txt_files += 1
        if (count_all_txt_files - last_count_all_txt_files) > (process_txt_files_threshold - 1):
            last_count_all_txt_files = count_all_txt_files
            print('%d txt files processed, %d files left...' % (last_count_all_txt_files
                                                                , len(all_txt_files_list) - last_count_all_txt_files))
        with open(txt_file, 'r') as file:
            read_file = file.read()
            condition = True
            for search_word in search_words:
                if search_word in read_file.lower():
                    condition = False
                    break
            if condition:
                wav_ext = '.wav'
                wav_file = txt_file.replace(".txt", wav_ext)
                out_file = os.path.join(out_dir, "rus_" + ntpath.basename(wav_file))
                offset = len(out_file) - len(wav_ext)
                out_file = out_file[:offset] + '_0' + out_file[offset:]
                while os.path.isfile(out_file):
                    right = out_file.rfind(wav_ext)
                    left = out_file[:right].rfind('_')
                    new_num = int(out_file[(left + 1):right]) + 1
                    out_file = out_file[:(left + 1)] + str(new_num) + out_file[right:]
                if not os.path.isfile(wav_file):
                    opus_file = txt_file.replace(".txt", ".opus")
                    if os.path.isfile(opus_file):
                        process = subprocess.run(["ffmpeg", "-i", opus_file, out_file]
                                                 , stderr=subprocess.DEVNULL
                                                 , stdout=subprocess.DEVNULL
                                                 , stdin=subprocess.PIPE)
                        if process.returncode != 0:
                            print('Converting opus to wav failed for %s!' % opus_file)
                            continue
                    else:
                        print('Audio file not found for %d or audio has unknown format!' % txt_file)
                        continue
                else:
                    shutil.copyfile(wav_file, out_file)
                found_files_list.append(wav_file)


walk_dir = sys.argv[1]
out_dir = sys.argv[2]

print('txt files collecting...')
all_txt_files_list = list(glob.iglob(walk_dir + '**/*.txt', recursive=True))
cpu_amount = multiprocessing.cpu_count() \
    if len(all_txt_files_list) >= multiprocessing.cpu_count() \
    else len(all_txt_files_list)
split_txt_files_list = word_cutter.split_list(all_txt_files_list, cpu_amount)
print('found %d txt files for searching' % len(all_txt_files_list))

shutil.rmtree(out_dir, ignore_errors=True)
Path(out_dir).mkdir(parents=True, exist_ok=True)
with futures.ThreadPoolExecutor(max_workers=cpu_amount) as executor:
    found_files_list = []
    sw = word_cutter.get_search_words()
    print('collecting and prepare audio files...')
    workers_count = 0
    last_count_all_txt_files = 0
    count_all_txt_files = 0
    process_txt_files_list_futures = dict((executor.submit(process_txt_files_list2, txt_files_list, sw)
                                           , txt_files_list)
                                          for txt_files_list in split_txt_files_list)
    for process_txt_files_list_future in futures.as_completed(process_txt_files_list_futures):
        if process_txt_files_list_future.exception() is not None:
            print('generated an exception: %s' % process_txt_files_list_future.exception())
        else:
            workers_count += 1
            if workers_count == cpu_amount:
                if len(found_files_list) > 0:
                    print('%d audio files prepared (1st pass)' % len(found_files_list))
