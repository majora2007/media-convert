# This file is to find and convert all avi/mkv/etc to m4v

from collections import defaultdict
import os
import logging
from pymediainfo import MediaInfo
import subprocess
import psutil
import time
from progressbar import (update_progress, restart_line)


#######################################################################
#                       PROGRESS BAR

#######################################################################

def setup_logger(dir, filename, debug_lvl):
    log_file = filename
    log_directory = os.path.abspath(dir)

    if not os.path.exists(log_directory):
        os.mkdir(log_directory)

    log_filePath = os.path.join(log_directory, log_file)

    if not os.path.isfile(log_filePath):
        with open(log_filePath, "w") as emptylog_file:
            emptylog_file.write('');

    logging.basicConfig(filename=log_filePath,level=debug_lvl, format='%(asctime)s %(message)s')

valid_extensions = ['rmvb', 'mkv', 'avi']
def needs_convert(file):
    return file.endswith('mkv') or file.endswith('avi')

def normalize_path(path):
    return path.replace('\\', '/')

def create_cmd(cmd, source):
    parts = source.split('.')
    parts[len(parts)-1] = EXT
    output_path = '.'.join(parts)

    return cmd.replace('{{source}}', source).replace('{{destination}}', output_path)

def convert(path):
    '''
    Converts a normalized path of video file into normalized handbrake file.
    '''
    logger = logging.getLogger(__name__)
    logger.info('Converting ' + path)

    cmd = create_cmd(handbrake_cli, path)

    logger.debug('Using command: ' + cmd)
    p =subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    for line in p.stdout.readlines():
        logger.debug(line)
    retval = p.wait()
    logger.debug('Convert returned: ' + str(retval))
    print 'Convert finished'

    return retval

def remux(path):
    '''
    Calls ffmpeg to perform container swap
    '''
    logger = logging.getLogger(__name__)
    logger.info('Remuxing ' + path)

    cmd = create_cmd(ffmpeg_cli, path)

    logger.debug('Using command: ' + cmd)
    p =subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    for line in p.stdout.readlines():
        logger.debug(line)
    retval = p.wait()
    logger.debug('Remux returned: ' + str(retval))
    print 'Remux finished'

    return retval

def delete(path):
    logger = logging.getLogger(__name__)
    logger.info('Deleting ' + path)
    os.remove(path)


def process(video_list):
    i = 0
    while(i < len(video_list)):
        restart_line()
        update_progress((i*1.0)/float(len(video_list)))
        media = video_list[i]

        cpu_perc = psutil.cpu_percent(interval=1)
        if cpu_perc < MAX_CPU_THRESHOLD:
            print 'Processing ' + str(media.tracks[0].complete_name)
            if convert(media.tracks[0].complete_name) is 0:
                if DELETE:
                    try:
                        delete(media.tracks[0].complete_name)
                    except OSError:
                        logger.exception('There was an issue deleting ' + str(media.tracks[0].complete_name))
                        # Idea: Delete the byproduct instead, we can attempt delete on next run
                print media.tracks[0].complete_name + ' Fully processed'
            else:
                logger.info('Failed to convert ' + media.tracks[0].complete_name)
                print ('Failed to convert ' + media.tracks[0].complete_name)
            i = i + 1
        else:
            logger.info('CPU utilization is ' + str(cpu_perc) + ' which is greater than ' + str(MAX_CPU_THRESHOLD) + '. Sleeping for 15 secs')
            print('CPU utilization is ' + str(cpu_perc) + ' which is greater than ' + str(MAX_CPU_THRESHOLD) + '. Sleeping for 15 secs')
            time.sleep(15)

handbrake_cli = 'HandBrakeCLI -i "{{source}}" -o "{{destination}}" --preset="Plex-CC"'
ffmpeg_cli = 'ffmpeg -i "{{source}}" -vcodec copy -acodec copy "{{destination}}"'

# A list of directories to scan
watched_folders = ['K:/Series', 'K:/Movies']
exclude = []

# Paths to all valid files
paths = []
# Just need container changed
remuxes = []
# Need Re-encodes
handbrakes = []

# Max CPU Percentage that a encoding job can be ran at (30 if plex, 45 if RS)
MAX_CPU_THRESHOLD = 50 #30

# Flag to denote whether to delete source files after successfull encode
DELETE = True

# Flag to denote whether to just run MediaInfo on files
JUST_CHECK = False

# Memory chunks before a processing session should be kicked off (if JUST_CHECK then we just free memory)
MEMORY_CHUNK = 10 # This is 200 MediaInfo objects

# EXT should be either mp4 or m4v. m4v should be chosen if you have multi-track audio and Apple TV users
global EXT
EXT = 'mp4'


if __name__ == '__main__':
    setup_logger('.', 'media-convert.log', logging.DEBUG)
    logger = logging.getLogger(__name__)

    logger.info("######### Script Executed at " + time.asctime(time.localtime(time.time())))

    for base_path in watched_folders:
        base_path = normalize_path(base_path)
        print 'Searching for files in ' + base_path
        logger.info('Searching for files in ' + base_path)
        t0 = time.time()
        for root, dirs, files in os.walk(base_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in exclude]
            for file in files:
                if needs_convert(file):
                    path = os.path.join(root, file)
                    paths.append(normalize_path(path))
        t1 = time.time()
        print '[Directory Scan] Execution took %s ms' % str(t1-t0)



    logger.info('=====Scan Complete=====')
    logger.info('Total files scanned: ' + str(len(paths)))
    print('Total files scanned: ' + str(len(paths)))
    print('Calculating conversions...')
    t0 = time.time()
    count = 0.0
    for path in paths:
        count += 1.0
        restart_line()
        update_progress(float(count/len(paths)))

        logger.debug('Calculating MediaInfo for: ' + normalize_path(path))
        media_info = MediaInfo.parse(normalize_path(path))
        for track in media_info.tracks:
            if track.track_type == 'Video':
                if track.codec.startswith('V_MPEG4'):
                    remuxes.append(media_info)
                else:
                    handbrakes.append(media_info)
    t1 = time.time()

    logger.info('Total Remuxes needed: ' + str(len(remuxes)))
    logger.info('Total Re-encodes needed: ' + str(len(handbrakes)))
    print('Total Remuxes needed: ' + str(len(remuxes)))
    print('Total Re-encodes needed: ' + str(len(handbrakes)))
    print '\n\n'
    print '[Media Check] Execution took %s ms' % str(t1-t0)

    if JUST_CHECK:
        sys.exit()


    # Start batch processing Re-encodes
    #process_transcodes(handbrakes)
    #process(handbrakes)

    # Start batch processing Re-encodes
    #process_remux(remuxes)
    process(remuxes)


