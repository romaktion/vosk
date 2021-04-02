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
import datetime

model_path = 'model'
out_folder = os.path.abspath('speech_dataset')
testing_list_file_name = 'testing_list.txt'
validation_list_file_name = 'validation_list.txt'

process_txt_files_threshold = 100000
process_audio_files_threshold = 100
max_audio_files_per_word = 5000

debug_raw_words = False

count_audio_files = {}
count_words = {}
count_raw_words = {}
count_pure_words = {}
found_files_list = []
inappropriate_words = {}

testing_texts_to_write = {}
validation_texts_to_write = {}


def get_search_words():
    with open("search_words.txt", 'r') as search_words_file:
        ret = {}
        for word in re.sub(r"[\r\n\t\s]*", "", search_words_file.read()).split(","):
            if '=' in word:
                split = word.split('=')
                if len(split) == 2:
                    ret[str(split[0]).lower()] = float(split[1])
        return ret


def split_list(a_list, wanted_parts=1):
    length = len(a_list)
    return [a_list[i * length // wanted_parts: (i + 1) * length // wanted_parts]
            for i in range(wanted_parts)]


def find_whole_word(word):
    return re.compile(r'\b({0})\b'.format(word), flags=re.IGNORECASE).search


def process_txt_files_list(txt_files_list, search_words, pass_num):
    global count_audio_files
    global found_files_list
    global last_count_all_txt_files
    global count_all_txt_files
    global all_txt_files_list
    global process_txt_files_threshold
    for txt_file in txt_files_list:
        count_all_txt_files += 1
        if (count_all_txt_files - last_count_all_txt_files) > (process_txt_files_threshold - 1):
            last_count_all_txt_files = count_all_txt_files
            print('%d txt files processed, %d files left...' % (last_count_all_txt_files
                                                                , len(all_txt_files_list) - last_count_all_txt_files))
        with open(txt_file, 'r') as file:
            read_file = file.read()
            for search_word in search_words:
                read_file_lower = read_file.lower()
                if pass_num == 0:
                    condition = find_whole_word(search_word)(read_file_lower) is not None
                elif pass_num == 1:
                    condition = search_word in read_file_lower
                else:
                    print("Unknown pass num!")
                wav_file = txt_file.replace(".txt", ".wav")
                if condition and count_audio_files[search_word] < max_audio_files_per_word \
                        and wav_file not in found_files_list:
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
                    found_files_list.append(wav_file)
                    count_audio_files[search_word] += 1


def process_files_list(files_list, search_words):
    global count_words
    global count_raw_words
    global count_pure_words
    global testing_texts_to_write
    global validation_texts_to_write
    global amount_all_audio_files
    global count_all_audio_files
    global last_count_all_audio_files
    global process_audio_files_threshold
    global inappropriate_words
    global debug_raw_words
    for filename in files_list:
        count_all_audio_files += 1
        if (count_all_audio_files - last_count_all_audio_files) > (process_audio_files_threshold - 1):
            last_count_all_audio_files = count_all_audio_files
            print('%d audio files processed, %d files left...' % (last_count_all_audio_files
                                                                  ,
                                                                  amount_all_audio_files - last_count_all_audio_files))
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
                    if search_word in word:
                        start = result['start']
                        end = result['end']
                        saved_start = start
                        saved_end = end
                        symbol_duration = (end - start) / len(word)
                        inappropriate = symbol_duration < search_words[search_word]
                        if inappropriate:
                            inappropriate_words[search_word] += 1
                        is_pure_word = word == search_word
                        if not is_pure_word:
                            found = str(word).find(search_word)
                            start += found * symbol_duration
                            end -= (len(word) - (found + len(search_word))) * symbol_duration
                        segment = AudioSegment.from_wav(filename)
                        segment = segment[start * 1000:end * 1000]
                        out_category_path = os.path.join(out_folder, search_word)
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
                            text_to_write = search_word + '/' + ntpath.basename(out_path) + '\n'
                            count_words[search_word] += 1
                            if is_pure_word:
                                count_pure_words[search_word] += 1
                                if not inappropriate:
                                    validation_texts_to_write[search_word].append(text_to_write)
                            else:
                                count_raw_words[search_word] += 1
                                if not inappropriate:
                                    testing_texts_to_write[search_word].append(text_to_write)
                                if debug_raw_words:
                                    segment = AudioSegment.from_wav(filename)
                                    segment = segment[saved_start * 1000:saved_end * 1000]
                                    out_category_path = os.path.join(out_folder, os.path.join(search_word, 'raw'))
                                    Path(out_category_path).mkdir(parents=True, exist_ok=True)
                                    segment.export(os.path.join(out_category_path, ntpath.basename(out_path))
                                                   , format="wav")
                        else:
                            print('Failed to cut segment for word "%s" from file %s' % (search_word, filename))


if __name__ == '__main__':
    SetLogLevel(0)

    if not os.path.exists(model_path):
        print("Please download the model from https://alphacephei.com/vosk/models and unpack as 'model' in the current "
              "folder.")
        exit(1)

    start_time = datetime.datetime.now()
    walk_dir = sys.argv[1]

    print('start time: ' + str(start_time))
    print('walk_dir: ' + os.path.abspath(walk_dir))

    model = Model(model_path)

    print('txt files collecting...')
    all_txt_files_list = list(glob.iglob(walk_dir + '**/*.txt', recursive=True))
    cpu_amount = multiprocessing.cpu_count() \
        if len(all_txt_files_list) >= multiprocessing.cpu_count() \
        else len(all_txt_files_list)
    split_txt_files_list = split_list(all_txt_files_list, cpu_amount)

    print('found %d txt files for searching' % len(all_txt_files_list))
    shutil.rmtree(out_folder, ignore_errors=True)
    with futures.ThreadPoolExecutor(max_workers=cpu_amount) as executor:
        sw = get_search_words()
        for w in sw:
            count_audio_files[w] = 0
            count_words[w] = 0
            count_raw_words[w] = 0
            count_pure_words[w] = 0
            inappropriate_words[w] = 0
            testing_texts_to_write[w] = []
            validation_texts_to_write[w] = []
        print('collecting and prepare audio files...')

        # process txt files 1st pass
        workers_count = 0
        last_count_all_txt_files = 0
        count_all_txt_files = 0
        process_txt_files_list_futures = dict((executor.submit(process_txt_files_list, txt_files_list, sw, 0)
                                               , txt_files_list)
                                              for txt_files_list in split_txt_files_list)
        for process_txt_files_list_future in futures.as_completed(process_txt_files_list_futures):
            if process_txt_files_list_future.exception() is not None:
                print('generated an exception: %s' % process_txt_files_list_future.exception())
            else:
                workers_count += 1
                if workers_count == cpu_amount:
                    if len(found_files_list) > 0:
                        print('audio files prepared (1st pass)')
                        for audio_file in count_audio_files:
                            print('count_audio_files for %s = %d' % (
                                audio_file, count_audio_files[audio_file]))

                        # process txt files 2nd pass
                        workers_count = 0
                        count_all_txt_files = 0
                        last_count_all_txt_files = 0

                        remove_keys = []
                        for audio_file in count_audio_files:
                            if count_audio_files[audio_file] > max_audio_files_per_word:
                                remove_keys.append(audio_file)
                        for key in remove_keys:
                            sw.pop(key)

                        process_txt_files_list_futures = dict(
                            (executor.submit(process_txt_files_list, txt_files_list, sw, 1)
                             , txt_files_list)
                            for txt_files_list in split_txt_files_list)
                        for process_txt_files_list_future2 in futures.as_completed(process_txt_files_list_futures):
                            if process_txt_files_list_future2.exception() is not None:
                                print('generated an exception: %s' % process_txt_files_list_future2.exception())
                            else:
                                workers_count += 1
                                if workers_count == cpu_amount:
                                    if len(found_files_list) > 0:
                                        split_found_files_list = split_list(found_files_list, cpu_amount)
                                        amount_all_audio_files = 0
                                        print('audio files prepared (2nd pass)')
                                        for audio_file in count_audio_files:
                                            print('count_audio_files for %s = %d' % (
                                                audio_file, count_audio_files[audio_file]))
                                            amount_all_audio_files += count_audio_files[audio_file]

                                        # process audio files
                                        workers_count = 0
                                        count_all_audio_files = 0
                                        last_count_all_audio_files = 0
                                        print('cutting words from audio files...')
                                        process_files_list_futures = dict(
                                            (executor.submit(process_files_list, found_files_list, sw)
                                             , found_files_list)
                                            for found_files_list in split_found_files_list)
                                        for process_files_list_future in process_files_list_futures:
                                            if process_files_list_future.exception() is not None:
                                                print(
                                                    'generated an exception: %s' % process_files_list_future.exception())
                                            else:
                                                workers_count += 1
                                                if workers_count == cpu_amount:
                                                    Path(out_folder).mkdir(parents=True, exist_ok=True)
                                                    testing_list_file = open(
                                                        os.path.join(out_folder, testing_list_file_name), 'w')
                                                    validation_list_file = open(
                                                        os.path.join(out_folder, validation_list_file_name), 'w')
                                                    for testing_texts_to_write_list in testing_texts_to_write:
                                                        for testing_text_to_write in testing_texts_to_write[
                                                            testing_texts_to_write_list]:
                                                            testing_list_file.write(testing_text_to_write)
                                                    for validation_texts_to_write_list in validation_texts_to_write:
                                                        for validation_text_to_write in validation_texts_to_write[
                                                            validation_texts_to_write_list]:
                                                            validation_list_file.write(validation_text_to_write)
                                                    testing_list_file.close()
                                                    validation_list_file.close()
                                                    for count_word in count_words:
                                                        print('count_words for %s = %d' % (
                                                            count_word, count_words[count_word]))
                                                    for count_raw_word in count_raw_words:
                                                        print('count_raw_words for %s = %d' % (
                                                            count_raw_word, count_raw_words[count_raw_word]))
                                                    for count_pure_word in count_pure_words:
                                                        print('count_pure_words for %s = %d' % (
                                                            count_pure_word, count_pure_words[count_pure_word]))
                                                    for inappropriate_word in inappropriate_words:
                                                        print('inappropriate_words for %s = %d' % (
                                                            inappropriate_word,
                                                            inappropriate_words[inappropriate_word]))
                                                    end_time = datetime.datetime.now()
                                                    print('end time: ' + str(end_time))
                                                    delta = end_time - start_time
                                                    print('all done in %d minutes %d seconds!'
                                                          % (int(delta.seconds / 60), delta.seconds))
                    else:
                        print('audio files not found!')
