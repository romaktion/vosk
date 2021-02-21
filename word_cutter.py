#!/usr/bin/env python3

# Author: romaktion@gmail.com

# word_cuter.py designed for cutting certain words from audio dataset needed to build model for key word spotting
# using tensorflow:  https://github.com/tensorflow/tensorflow/blob/master/tensorflow/examples/speech_commands/train.py


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
from pathlib import Path
import subprocess
import shutil

model_path = 'model'
out_folder = os.path.abspath('speech_dataset')
testing_list_file_name = 'testing_list.txt'
validation_list_file_name = 'validation_list.txt'

count_txt_files = {}
count_words = {}
count_pure_words = {}


def map_range(value, left_min, left_max, right_min, right_max):
    # Figure out how 'wide' each range is
    left_span = left_max - left_min
    right_span = right_max - right_min

    # Convert the left range into a 0-1 range (float)
    value_scaled = float(value - left_min) / float(left_span)

    # Convert the 0-1 range into a value in the right range.
    return right_min + (value_scaled * right_span)


def get_search_words():
    with open("search_words.txt", 'r') as search_words_file:
        ret = {}
        for word in re.sub(r"[\n\t\s]*", "", search_words_file.read()).split(","):
            split = word.split('=')
            ret[str(split[0])] = float(split[1])
        return ret


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
                    count_txt_files[search_word] += 1
    if len(files_list) > 0:
        process_files_list(files_list, search_words)


def process_files_list(files_list, search_words):
    global count_words
    for filename in files_list:
        wf = wave.open(filename, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print("Audio file must be wav format mono PCM.")
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
                    start = result['start']
                    end = result['end']
                    duration = end - start
                    if duration < search_words[search_word]:
                        continue
                    if search_word in word:
                        segment = AudioSegment.from_wav(filename)
                        is_pure_word = word == search_word
                        if not is_pure_word:
                            found = str(word).find(search_word)
                            time_per_symbol = map_range(duration / len(word), 0.05, 0.1798333333333333, 0.05, 0.25)
                            start += found * time_per_symbol
                            end -= (len(word) - (found + len(search_word))) * time_per_symbol
                        segment = segment[start * 1000:end * 1000]
                        out_category_path = os.path.join(out_folder
                                                         , search_word
                                                         if True  # is_pure_word
                                                         else os.path.join(search_word, 'raw'))
                        Path(out_category_path).mkdir(parents=True, exist_ok=True)
                        out_path = os.path.join(out_category_path, ntpath.basename(filename))
                        wav_ext = '.wav'
                        offset = len(out_path) - len(wav_ext)
                        out_path = out_path[:offset] + '_0' + out_path[offset:]
                        while os.path.isfile(out_path):
                            right = out_path.rfind(wav_ext)
                            left = out_path[:right].rfind('_')
                            new_num = int(out_path[(left + 1):right]) + 1
                            out_path = out_path[:(left + 1)] + str(new_num) + out_path[right:]
                        segment.export(out_path, format="wav")
                        if os.path.isfile(out_path):
                            (validation_list_file if is_pure_word else testing_list_file)\
                                .write(search_word + '/' + ntpath.basename(out_path) + '\n')
                            count_words[search_word] += 1
                            if is_pure_word:
                                count_pure_words[search_word] += 1
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
shutil.rmtree(out_folder, ignore_errors=True)
Path(out_folder).mkdir(parents=True, exist_ok=True)
testing_list_file = open(os.path.join(out_folder, testing_list_file_name), 'w')
validation_list_file = open(os.path.join(out_folder, validation_list_file_name), 'w')
with futures.ThreadPoolExecutor(max_workers=cpu_amount) as executor:
    workers_count = 0
    sw = get_search_words()
    for w in sw:
        count_txt_files[w] = 0
        count_words[w] = 0
        count_pure_words[w] = 0
    process_txt_files_list_futures = dict((executor.submit(process_txt_files_list, txt_files_list, sw)
                                           , txt_files_list)
                                          for txt_files_list in split_txt_files_list)
    for future in futures.as_completed(process_txt_files_list_futures):
        if future.exception() is not None:
            print('generated an exception: %s' % future.exception())
        else:
            workers_count += 1
            if workers_count == cpu_amount:
                validation_list_file.close()
                testing_list_file.close()
                for count_txt_file in count_txt_files:
                    print('count_txt_file for %s = %d' % (count_txt_file, count_txt_files[count_txt_file]))
                for count_word in count_words:
                    print('count_words for %s = %d' % (count_word, count_words[count_word]))
                for count_pure_word in count_pure_words:
                    print('count_pure_words for %s = %d' % (count_pure_word, count_pure_words[count_pure_word]))
