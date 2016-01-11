# This file is to find and convert all avi/mkv/etc to m4v

from collections import defaultdict
import os
import logging
from pymediainfo import MediaInfo
import subprocess
import psutil
import time


#######################################################################
#                       PROGRESS BAR
import time, sys
def restart_line():
    sys.stdout.write('\r')
    sys.stdout.flush()

def update_progress(progress):
    '''
        update_progress() : Displays or updates a console progress bar
        Accepts a float between 0 and 1. Any int will be converted to a float.
        A value under 0 represents a 'halt'.
        A value at 1 or bigger represents 100%
    '''
    barLength = 10 # Modify this to change the length of the progress bar
    status = ""
    if isinstance(progress, int):
        progress = float(progress)
    if not isinstance(progress, float):
        progress = 0
        status = "error: progress var must be float\r\n"
    if progress < 0:
        progress = 0
        status = "Halt...\r\n"
    if progress >= 1:
        progress = 1
        status = "Done...\r\n"
    block = int(round(barLength*progress))
    text = "\rPercent: [{0}] {1}% {2}".format( ">"*block + "-"*(barLength-block), progress*100, status)
    sys.stdout.write(text)
    sys.stdout.flush()
#######################################################################


def needs_convert(file):
    if file.endswith('mkv') or file.endswith('avi'):
        return True
    return False

def normalize_path(path):
    return path.replace('\\', '/')

def convert(path):
    '''
    Converts a normalized path of video file into normalized handbrake file.
    '''
    logger = logging.getLogger(__name__)
    logger.info('Converting ' + path)
    parts = path.split('.')
    parts[len(parts)-1] = 'mp4'
    output_path = '.'.join(parts)

    cmd = handbrake_cli.replace('{{source}}', path).replace('{{destination}}', output_path)

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

    parts = path.split('.')
    parts[len(parts)-1] = 'mp4'
    output_path = '.'.join(parts)

    cmd = ffmpeg_cli.replace('{{source}}', path).replace('{{destination}}', output_path)

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


handbrake_cli = 'HandBrakeCLI -i "{{source}}" -o "{{destination}}" --preset="Plex-CC"'
ffmpeg_cli = 'ffmpeg -i "{{source}}" -vcodec copy -acodec copy "{{destination}}"'

paths = defaultdict(str)

watched_folders = ['E:/']
exclude = []

paths = []

# Max CPU Percentage that a encoding job can be ran at
MAX_CPU_THRESHOLD = 30

# Flag to denote whether to delete source files after successfull encode
DELETE = True


if __name__ == '__main__':
    log_file = 'media-convert.log'
    log_directory = os.path.abspath('.')

    if not os.path.exists(log_directory):
        os.mkdir(log_directory)

    log_filePath = os.path.join(log_directory, log_file)

    if not os.path.isfile(log_filePath):
        with open(log_filePath, "w") as emptylog_file:
            emptylog_file.write('');

    logging.basicConfig(filename=log_filePath,level=logging.DEBUG, format='%(asctime)s %(message)s')
    logger = logging.getLogger(__name__)

    logger.info("######### Script Executed at " + time.asctime(time.localtime(time.time())))

    for base_path in watched_folders:
        print 'Searching for files in ' + base_path
        logger.info('Searching for files in ' + base_path)
        for root, dirs, files in os.walk(base_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in exclude]
            for file in files:
                if needs_convert(file):
                    path = os.path.join(root, file)
                    paths.append(normalize_path(path))


    remuxes = [] # Just need container changed
    handbrakes = [] # Need Re-encodes
    logger.info('=====Scan Complete=====')
    logger.info('Total files scanned: ' + str(len(paths)))
    print('Calculating Remuxes...')
    count = 0.0
    for path in paths:
        count += 1.0
        restart_line()
        update_progress(float(count/len(paths)))

        media_info = MediaInfo.parse(normalize_path(path))
        for track in media_info.tracks:
            if track.track_type == 'Video':
                if track.codec.startswith('V_MPEG4'):
                    remuxes.append(media_info)
                else:
                    handbrakes.append(media_info)

    print '\nRemuxes calculated...'
    logger.info('Total Remuxes needed: ' + str(len(remuxes)))
    logger.info('Total Re-encodes needed: ' + str(len(handbrakes)))
    print('Total Remuxes needed: ' + str(len(remuxes)))
    print('Total Re-encodes needed: ' + str(len(handbrakes)))


    # Start batch processing Re-encodes
    i = 0
    while(i < len(handbrakes)):
        media = handbrakes[i]
        cpu_perc = psutil.cpu_percent(interval=1)
        if cpu_perc < MAX_CPU_THRESHOLD:
            print 'Processing ' + media.tracks[0].complete_name
            if convert(media.tracks[0].complete_name) is 0:
                if DELETE:
                    delete(media.tracks[0].complete_name)
                print media.tracks[0].complete_name + ' Fully processed'
            else:
                logger.info('Failed to convert ' + media.tracks[0].complete_name)
                print ('Failed to convert ' + media.tracks[0].complete_name)
            i = i + 1
        else:
            logger.info('CPU utilization is ' + str(cpu_perc) + ' which is greater than ' + str(MAX_CPU_THRESHOLD) + '. Sleeping for 15 secs')
            print('CPU utilization is ' + str(cpu_perc) + ' which is greater than ' + str(MAX_CPU_THRESHOLD) + '. Sleeping for 15 secs')
            time.sleep(15)


    # Start batch processing Re-encodes
    i = 0
    for i in range(0, len(remuxes)):
        media = remuxes[i]
        cpu_perc = psutil.cpu_percent(interval=1)
        if cpu_perc < MAX_CPU_THRESHOLD:
            print 'Processing ' + media.tracks[0].complete_name
            if remux(media.tracks[0].complete_name) is 0:
                if DELETE:
                    delete(media.tracks[0].complete_name)
                print media.tracks[0].complete_name + ' Fully processed'
            else:
                logger.info('Failed to remux ' + media.tracks[0].complete_name)
                print('Failed to remux ' + media.tracks[0].complete_name)
            i = i + 1
        else:
            logger.info('CPU utilization is ' + str(cpu_perc) + ' which is greater than ' + str(MAX_CPU_THRESHOLD) + '. Sleeping for 15 secs')
            print('CPU utilization is ' + str(cpu_perc) + ' which is greater than ' + str(MAX_CPU_THRESHOLD) + '. Sleeping for 15 secs')
            time.sleep(15)

