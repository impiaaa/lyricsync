import sys

def secToHMSMS(sec):
    totalms = round(sec*1000)
    ms = totalms%1000
    seconds = (totalms//1000)%60
    minutes = (totalms//60000)%60
    hours = totalms//3600000
    return (hours,minutes,seconds,ms)

for i, line in enumerate(sys.stdin):
    start, end, s = line.rstrip().split('\t')
    start = float(start)
    end = float(end)
    print(i+1)
    print("%02d:%02d:%02d,%03d --> "%secToHMSMS(start), end='')
    print("%02d:%02d:%02d,%03d"%secToHMSMS(end))
    print(s)
    print()

