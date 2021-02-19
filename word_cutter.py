#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer, SetLogLevel
import sys
import os
import wave
import json
import glob
from concurrent import futures
import threading
import multiprocessing
from pydub import AudioSegment
import ntpath
import re
from pathlib import Path
import subprocess

model_path = 'model'

count_txt_files = 0
count_words = 0
count_txt_files_lock = threading.Lock()
count_words_lock = threading.Lock()


def get_search_words():
    with open("search_words.txt", 'r') as search_words_file:
        return re.sub(r"[\n\t\s]*", "", search_words_file.read()).split(",")


def split_list(a_list, wanted_parts=1):
    length = len(a_list)
    return [a_list[i * length // wanted_parts: (i + 1) * length // wanted_parts]
            for i in range(wanted_parts)]


def process_txt_files_list(txt_files_list, search_words):
    global count_txt_files
    files_list = []
    for txt_file in txt_files_list:
        with open(txt_file, 'r') as file:
            read_file = file.read()
            for search_word in search_words:
                if search_word in read_file:
                    wav_file = txt_file.replace(".txt", ".wav")
                    if not os.path.isfile(wav_file):
                        opus_file = txt_file.replace(".txt", ".opus")
                        if os.path.isfile(opus_file):
                            process = subprocess.run(["ffmpeg", "-i", opus_file, wav_file]
                                                     , stderr=subprocess.DEVNULL
                                                     , stdout=subprocess.DEVNULL
                                                     , stdin=subprocess.PIPE)
                            if process.returncode != 0:
                                print('Converting opus to wav failed for %s!' % opus_file)
                                continue
                        else:
                            print('Audio file not found for %d or audio has unknown format!' % txt_file)
                            continue
                    files_list.append(wav_file)
    if len(files_list) > 0:
        count_txt_files += len(files_list)
        process_files_list(files_list, search_words)


def process_files_list(files_list, search_words):
    global count_words
    for filename in files_list:
        wf = wave.open(filename, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print("Audio file must be WAV format mono PCM.")
            exit(1)

        rec = KaldiRecognizer(model, wf.getframerate())

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            rec.AcceptWaveform(data)

        try:
            json_obj = json.loads(rec.FinalResult())
        except ValueError:
            continue

        result_field_name = 'result'
        if result_field_name in json_obj:
            for result in json_obj[result_field_name]:
                word = result['word']
                for search_word in search_words:
                    if search_word in word:
                        print(result)
                        print(json_obj['text'])
                        segment = AudioSegment.from_wav(filename)
                        segment = segment[result['start'] * 1000:result['end'] * 1000]
                        out_category_path = os.path.join('out'
                                                         , search_word
                                                         if word == search_word
                                                         else os.path.join(search_word, 'raw'))
                        Path(out_category_path).mkdir(parents=True, exist_ok=True)
                        out_path = os.path.join(out_category_path, ntpath.basename(filename))
                        segment.export(out_path, format="wav")
                        if os.path.isfile(out_path):
                            # with count_words_lock:
                            count_words += 1
                        else:
                            print('Failed to cut segment for word "%s" from file %s' % (search_word, filename))


SetLogLevel(0)

if not os.path.exists(model_path):
    print("Please download the model from https://alphacephei.com/vosk/models and unpack as 'model' in the current "
          "folder.")
    exit(1)

walk_dir = sys.argv[1]

print('walk_dir = ' + os.path.abspath(walk_dir))

model = Model(model_path)

print('finding words...')
all_txt_files_list = list(glob.iglob(walk_dir + '**/*.txt', recursive=True))
cpu_amount = multiprocessing.cpu_count() \
    if len(all_txt_files_list) >= multiprocessing.cpu_count() \
    else len(all_txt_files_list)
split_txt_files_list = split_list(all_txt_files_list, cpu_amount)
print('found %d txt files for searching, start finding&cutting...' % len(all_txt_files_list))

with futures.ThreadPoolExecutor(max_workers=cpu_amount) as executor:
    workers_count = 0
    process_txt_files_list_futures = dict((executor.submit(process_txt_files_list, txt_files_list, get_search_words())
                                           , txt_files_list)
                                          for txt_files_list in split_txt_files_list)
    for future in futures.as_completed(process_txt_files_list_futures):
        if future.exception() is not None:
            print('generated an exception: %s' % future.exception())
        else:
            workers_count += 1
            if workers_count == cpu_amount:
                print('count_txt_files = %d' % count_txt_files)
                print('count_words = %d' % count_words)
