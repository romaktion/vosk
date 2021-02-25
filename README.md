# vosk
Working with vosk API

word_cuter.py designed for cutting certain words from audio dataset needed to build model for key word spotting using tensorflow:  https://github.com/tensorflow/tensorflow/blob/master/tensorflow/examples/speech_commands/train.py

How to use
1. Edit search_words.txt to define your words to cut ([word]=[min lenth of symbol in word in seconds, the rest of the words are discarded, can leave as default]
2. Run "word_cutter.py" whith one argument: word_cutter.py [path to data set, for exemple: https://github.com/snakers4/open_stt]

P.S. vosk model and data set must be for the same language

Tested only on Windows
