import csv, os, sys
import eyed3

from unicodedata import normalize

from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from pydub.utils import mediainfo
from pydub.exceptions import CouldntDecodeError

def bpm(seg):
    l_seg = seg.low_pass_filter(120.0)
    beat_loudness = l_seg.dBFS
    minimum_silence = int(60000/240.0)
    nonsilent_times = detect_nonsilent(l_seg, minimum_silence, beat_loudness)
    spaces_between_beats = []
    last_t = nonsilent_times[0][0]
    for peak_start, _ in nonsilent_times[1:]:
        spaces_between_beats.append(peak_start - last_t)
        last_t = peak_start

    spaces_between_beats = sorted(spaces_between_beats)
    space = spaces_between_beats[len(spaces_between_beats) / 2]
    bpm = 60000 / space
    return bpm

def bpm_from_files(files):
  count = 0
  for f in files:
      print(f['name'])
      print(str(len(files) - count) + "/" + str(len(files))) 
      #f['metadata'] = eyed3.load(f['path'])
      f['seg'] = AudioSegment.from_file(f['path'])
      f['bpm'] = bpm(f['seg'])
  
      count += 1
  return files

def detect_leading_silence(sound, silence_threshold=-50.0, chunk_size=10):
    trim_ms = 0
    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold:
        trim_ms += chunk_size
    return trim_ms

def detect_trailing_silence(sound, silence_threshold=-50.0, chunk_size=10):
    return detect_leading_silence(sound.reverse(), silence_threshold, chunk_size)

def trim_leading_silence(sound):
    leading_silence = detect_leading_silence(sound)
    return sound[leading_silence:]

def trim_trailing_silence(sound):
    trailing_silence = detect_trailing_silence(sound)
    return sound[:-trailing_silence]

if __name__ == "__main__":
  files = [{'path':sys.argv[1]+name, 
            'metadata':mediainfo(sys.argv[1]+name),
            'name':name} for name in os.listdir(sys.argv[1])]

  show = []
  count = 0
  for f in files:
      if len(show) > 0:
          duration = reduce(lambda a,b: a+b, [x['seg'].duration_seconds for x in show])
          if duration >= 60 ** 2 * 2 + (60 * 5):
              first_file = show[0]

              start = 0
              start_time = (0, 0)
              track_num = 0
              track_info = []

              merged = None

              for f in show:
                if f is show[0]:
                  f['seg'] = trim_trailing_silence(f['seg'])
                elif f is show[-1]:
                  f['seg'] = trim_leading_silence(f['seg'])
                else:
                  f['seg'] = trim_trailing_silence(trim_leading_silence(f['seg']))

                if merged is None:
                  merged = f['seg']
                else:
                  merged = merged.append(f['seg'], crossfade=750)

                length_track = f['seg'].duration_seconds
                
                length_show = merged.duration_seconds
                
                start = length_show * 1.0
                duration = length_track * 1.0
             
                track = {}

                track['start time'] = "%i:%02i" % start_time
                track['track number'] = track_num
                track['track runtime'] = "%i:%02i" % divmod(duration, 60)
                track['title'] = normalize('NFKD', f['metadata']['title']).encode('ASCII', 'ignore') if f['metadata'].get('title') and len(f['metadata']['title']) > 5 else f['name']
                track['artist'] = normalize('NFKD', f['metadata'].get('artist', u'unknown')).encode('ASCII', 'ignore')
                track['album'] = normalize('NFKD', f['metadata'].get('album', u'unknown')).encode('ASCII', 'ignore')
           
                track_info.append(track)

                start_time = divmod(start, 60)

                track_num += 1

              print(track_info)

              with open('papi_chulo_tracks_%i.csv' % count, 'wb') as outfile:
                dict_writer = csv.DictWriter(outfile, ['start time','track number', 'track runtime', 'title', 'artist', 'album'])
                dict_writer.writeheader()
                dict_writer.writerows(track_info)

    
              with open('papi_chulo_%i.mp3' % count, 'wb') as outfile:
                merged.export(outfile, format='mp3')

              count+=1
              show = []
      try:
        print(f['name'])
        z = f
        z['seg'] = AudioSegment.from_file(f['path'])
        show.append(z)
      except CouldntDecodeError as e:
        print e

