lines = open("lyrics.srt").read().split('\n\n')
fout = open("lyrics.srt", 'w')
last = None
i = 1
for line in lines:
    line = line.split('\n')
    if len(line) < 2: continue
    time = line[1]
    s = '\n'.join(line[2:])
    if s != last:
        print(i, file=fout)
        print(time, file=fout)
        print(s, file=fout)
        print(file=fout)
        i += 1
    last = s
fout.close()

