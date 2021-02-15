#!/usr/bin/env python3

from vosk import Model, KaldiRecognizer, SetLogLevel
import sys
import os
import wave
import json
import glob
from concurrent import futures
import multiprocessing
from pydub import AudioSegment
import ntpath
import re

count_txt_files = 0
count_words = 0


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
            for search_word in search_words:
                if search_word in file.read():
                    files_list.append(txt_file.replace(".txt", ".wav"))
    count_txt_files += len(files_list)
    if len(files_list) > 0:
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

        field_name = 'result'
        if field_name in json_obj:
            for result in json_obj[field_name]:
                word = result['word']
                for search_word in search_words:
                    if search_word in word:
                        print(result)
                        print(json_obj['text'])
                        """
                        segment = AudioSegment.from_wav(filename)
                        segment = segment[word['start'] * 1000
                                          :word['end'] * 1000]
                        segment.export(ntpath.basename(filename), format="wav")
                        """
                        count_words += 1


SetLogLevel(0)

model_path = 'model'

if not os.path.exists(model_path):
    print("Please download the model from https://alphacephei.com/vosk/models and unpack as 'model' in the current "
          "folder.")
    exit(1)

walk_dir = sys.argv[1]

print('walk_dir = ' + walk_dir)
print('walk_dir (absolute) = ' + os.path.abspath(walk_dir))

model = Model(model_path)

print('finding words...')
cpu_amount = multiprocessing.cpu_count()
workers_count = 0
split_txt_files_list = split_list(list(glob.iglob(walk_dir + '**/*.txt', recursive=True))
                                  , cpu_amount)
with futures.ThreadPoolExecutor(max_workers=cpu_amount) as executor:
    process_txt_files_list_futures = dict((executor.submit(process_txt_files_list, txt_files_list, get_search_words())
                                           , txt_files_list)
                                          for txt_files_list in split_txt_files_list)
    for future in futures.as_completed(process_txt_files_list_futures):
        if future.exception() is not None:
            print('%r generated an exception: %s' % (future.exception()))
        else:
            workers_count += 1
            if workers_count == cpu_amount:
                print('count_txt_files = %d' % count_txt_files)
                print('count_words = %d' % count_words)
