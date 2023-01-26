from ogg_adapter import *
from spleeter.separator import Separator
import sys, os
import tempfile
import gentle
import json

def caseInsensitive(dir, path):
    ls = os.listdir(dir)
    lowerLs = [f.casefold() for f in ls]
    return ls[lowerLs.index(path.casefold())]

beatmap_dir = sys.argv[1]
print(beatmap_dir)

if os.path.exists(os.path.join(beatmap_dir, "lyrics.srt")):
    print("Skipping", sys.argv[1], file=sys.stderr)
    exit(1)

beatmap_info = json.load(open(os.path.join(beatmap_dir, caseInsensitive(beatmap_dir, "info.dat")), 'rb'))
audio_descriptor = os.path.join(beatmap_dir, caseInsensitive(beatmap_dir, beatmap_info["_songFilename"]))

print("Initializing", file=sys.stderr)
audio_adapter: AudioAdapter = PyOggAudioAdapter()
separator: Separator = Separator("spleeter:2stems")

print("Loading", file=sys.stderr)
transcript = open(os.path.join(beatmap_dir, caseInsensitive(beatmap_dir, "lyrics.txt"))).read()
waveform, _ = audio_adapter.load(
    audio_descriptor,
    sample_rate=separator._sample_rate,
)

print("Separating", file=sys.stderr)
sources = separator.separate(waveform, audio_descriptor)

print("Resampling", file=sys.stderr)
vocals = sources["vocals"]
vocals = (np.sum(vocals, axis=1)/vocals.shape[1]).reshape((vocals.shape[0], 1))
vocals = resample(vocals, separator._sample_rate, 8000)

resources = gentle.Resources()

with tempfile.NamedTemporaryFile(suffix='.wav') as fp:
    vocalspath = fp.name
    print("Saving", file=sys.stderr)
    audio_adapter.save(vocalspath, vocals, 8000)
    
    print("Transcribing", file=sys.stderr)
    aligner = gentle.ForcedAligner(resources, transcript)
    result = aligner.transcribe(vocalspath)

print("Fixing", file=sys.stderr)
startIdx = 0
lines = []
for i, word in enumerate(result.words):
    if i > 0 and '\n' in transcript[result.words[i-1].endOffset:word.startOffset]:
        lines.append(result.words[startIdx:i])
        startIdx = i

wordDurations = {}
for word in result.words:
    if word.case == 'success':
        if word.alignedWord not in wordDurations:
            wordDurations[word.alignedWord] = {word.duration}
        else:
            wordDurations[word.alignedWord].add(word.duration)

for word, durations in wordDurations.items():
    wordDurations[word] = sum(durations)/len(durations)

def getDuration(word):
    if word.alignedWord in wordDurations:
        return wordDurations[word.alignedWord]
    elif word.word.casefold() in wordDurations:
        return wordDurations[word.word.casefold()]
    else:
        return 0

knownStarts = [None]*len(lines)
knownEnds = [None]*len(lines)
possibleStarts = [None]*len(lines)
possibleEnds = [None]*len(lines)
for i, line in enumerate(lines):
    startTime = None
    for j, word in enumerate(line):
        if word.case == 'success':
            knownStarts[i] = word.start
            possibleStarts[i] = word.start
            for word2 in line[:j]:
                possibleStarts[i] -= getDuration(word2)
            if possibleStarts[i] < 0:
                possibleStarts[i] = 0
            break
    for j, word in reversed(list(enumerate(line))):
        if word.case == 'success':
            knownEnds[i] = word.end
            possibleEnds[i] = word.end
            for word2 in line[j+1:]:
                possibleEnds[i] += getDuration(word2)
            break

for i, line in enumerate(lines):
    if i+1 < len(lines) and possibleEnds[i] is not None and knownStarts[i+1] is not None and possibleEnds[i] > knownStarts[i+1]:
        possibleEnds[i] = knownStarts[i+1]
    if i > 0 and knownEnds[i-1] is not None and possibleStarts[i] is not None and knownEnds[i-1] > possibleStarts[i]:
        possibleStarts[i] = knownEnds[i-1]

i = 0
while i < len(lines):
    if possibleStarts[i] is None:
        breakStartIdx = i
        if i == 0:
            breakStartTime = 0.0
        else:
            breakStartTime = possibleEnds[i-1]
        breakEndTime = None
        while i < len(lines):
            if possibleStarts[i] is not None:
                breakEndTime = possibleStarts[i]
                break
            i += 1
        breakEndIdx = i-1
        if breakEndTime is None:
            breakEndTime = waveform.shape[0]/separator._sample_rate
        breakTime = breakEndTime-breakStartTime
        talkTime = sum(getDuration(word) for line in lines[breakStartIdx:breakEndIdx+1] for word in line)
        spaceTime = breakTime-talkTime
        eachSpaceTime = spaceTime/(breakEndIdx-breakStartIdx+2)
        t = breakStartTime+eachSpaceTime
        for j in range(breakStartIdx, breakEndIdx+1):
            possibleStarts[j] = t
            t += sum(map(getDuration, lines[j]))
            possibleEnds[j] = t
            t += eachSpaceTime
    else:
        i += 1

textLines = [""]*len(lines)
for i, line in enumerate(lines):
    startOffset = transcript.rfind('\n', 0, line[0].startOffset)
    if startOffset == -1: startOffset = 0
    else: startOffset += 1
    textLines[i] = transcript[startOffset:transcript.find('\n', line[-1].endOffset)]

def secToHMSMS(sec):
    totalms = round(sec*1000)
    ms = totalms%1000
    seconds = (totalms//1000)%60
    minutes = (totalms//60000)%60
    hours = totalms//3600000
    return (hours,minutes,seconds,ms)

print("Writing", file=sys.stderr)
with open(os.path.join(beatmap_dir, "lyrics.srt"), 'w') as fout:
    for i, (startTime, endTime, s) in enumerate(zip(possibleStarts, possibleEnds, textLines)):
        print(i+1, file=fout)
        print("%02d:%02d:%02d,%03d --> "%secToHMSMS(startTime), end='', file=fout)
        print("%02d:%02d:%02d,%03d"%secToHMSMS(endTime), file=fout)
        print(s, file=fout)
        print(file=fout)
with open(os.path.join(beatmap_dir, "lyrics-aud-generated.txt"), 'w') as fout:
    for startTime, endTime, s in zip(possibleStarts, possibleEnds, textLines):
        print("%.06f\t%.06f\t%s"%(startTime, endTime, s), file=fout)

