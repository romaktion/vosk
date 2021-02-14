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


def split_list(a_list, wanted_parts=1):
    length = len(a_list)
    return [a_list[i * length // wanted_parts: (i + 1) * length // wanted_parts]
            for i in range(wanted_parts)]


def process_file_list(files_list):
    for filename in files_list:
        if filename.endswith('.wav'):
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
            except ValueError as e:
                continue

            field_name = 'result'
            if field_name in json_obj:
                for result in json_obj[field_name]:
                    if 'пиши' in result['word']:
                        print(result)
                        print(json_obj['text'])
                    if 'пишу' in


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

print('cook files...')
cpu_count = multiprocessing.cpu_count()
split_files_list = split_list(list(glob.iglob(walk_dir + '**/*.wav', recursive=True))
                              , cpu_count)

print('finding words...')
with futures.ThreadPoolExecutor(max_workers=cpu_count) as executor:
    dict((executor.submit(process_file_list, files_list), files_list)
         for files_list in split_files_list)
