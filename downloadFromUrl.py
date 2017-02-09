############################################################################
# Download script to download the file mentioned in the config.json file   #
#                     Developed on Python 2.6.6                            #
############################################################################

import sys, time
import getopt
import urllib, urllib2
import json
import os
import hashlib
from threading import Thread
import logging
from urlparse import urlparse
from ftplib import FTP
import subprocess
import proc_helpers
import base64
import pysftp
import signal
from archive_helper import archive_helper

confFile = ''
confJson = {}
connList = []

def loadConfFile():
    global confJson
    with open(confFile) as data_file:
        confJson = json.load(data_file)

def enableLogging(logLevel):
    numeric_level = getattr(logging, logLevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % logLevel)
    logging.basicConfig(level=numeric_level)

def getOptions(scriptName, argv):
    global confFile
    global confJson
    runAsDaemon = False
    logLevel = "ERROR"
    outFile = ''
    try:
        opts, args = getopt.getopt(argv,"hc:dl:",["confFile=", "runAsDaemon", "log="])
    except getopt.GetoptError:
        print scriptName + ' -c <confFile> -d -l <loglevel>'
        sys.exit(1)
    for opt, arg in opts:
        if opt == '-h':
            print scriptName + ' -c <confFile> -d -l <loglevel>'
            sys.exit(0)
        elif opt in ("-c", "--confFile"):
            confFile = arg
        elif opt in ("-d", "--runAsDaemon"):
            runAsDaemon = True
        elif opt in ("-l", "--log"):
            logLevel = arg

    if (confFile == ""):
        print 'Error:' + scriptName + ' needs a config file. Try -h for more details.'
        sys.exit(0)

    loadConfFile()
    enableLogging(logLevel)
    return runAsDaemon
        
def getHashOfFile(download_file):
    hash = hashlib.md5()
    try:
        with open(download_file, 'r') as output_file:
            hash.update(output_file.read())
        return hash.hexdigest()
    except IOError as ioex:
        if (ioex.errno == 2):
            # incase of no file .. create one
            open(download_file, 'w').close()
            return getHashOfFile(download_file)
        else:
            raise

def checkAndWriteToFile(downloaddata, downloadfile):
    hash = hashlib.md5()
    hash.update(downloaddata)
    
    if (hash.hexdigest() != getHashOfFile(downloadfile)):
        logging.info("File changed on server. Updating local copy ...")
        with open(downloadfile, 'w') as output_file:
            output_file.write(downloaddata)
    
def updateFile(scheme, connection, downloadfile, path):
    if (scheme == "ftp"):
        download_data = []
        connection.retrlines("RETR " + path, lambda s, w = download_data: w.append(s))
        download_data = '\n'.join(download_data)
        checkAndWriteToFile(download_data, downloadfile)
    elif (scheme == "sftp"):
        # below lines of code for curl download 
        # just use the global sftpDownloadData here
        #checkAndWriteToFile(sftpDownloadData, downloadfile)
        download_data = ""
        with connection.open(path, 'r') as remote_file:
            download_data += remote_file.read()
        checkAndWriteToFile(download_data, downloadfile)
    else:
        # download from http
        download_data = connection.read()
        checkAndWriteToFile(download_data, downloadfile)

def getConnectionListKey(scheme, completeUrl, hostUrl):
    global confJson
    if (scheme == "ftp" or scheme == "sftp"):
        return hostUrl
    else:
        # for urllib2 the connection needs to reset everytime and so lets make it to not retain conn
        # until we use some better libraries
        if (confJson['retain_con'] == 1):
            confJson['retain_con'] = 0
        return completeUrl

def downloadFromCurl(download_url, downloadfile):
    # use curl to get the file and store it in /tmp directory
    # change the actual file only if there is a change
    # connection = "sftp"
    global sftpDownloadData
    curlBin = ['/usr/bin/curl']
    auth = str(confJson['username']) + ':' + base64.b64decode(str(confJson['password']))
    params = ['-u', auth, '--connect-timeout', str(confJson['timeout']), download_url]
    try:
        sftpDownloadData = subprocess.check_output(
            curlBin + params)
    except subprocess.CalledProcessError as e:
        logging.error("Error at calling curl [" + e.output + "]")
        raise

def connect_with_retry(download_url, nTries, callback, downloadfile):
    global connList
    urlparseresult = urlparse(download_url)
    
    connLookupKey = getConnectionListKey(urlparseresult.scheme, download_url, urlparseresult.netloc)
    if connLookupKey not in connList:
        connList[connLookupKey] = ""
    connection = connList[connLookupKey]

    if (confJson['retain_con'] != 1 or connection == ""):
        if (connection != ""):
            # close existing open connection to trigger new one
            logging.info("closing open connection")
            logging.info(str(connection))
            connection.close()
            connection = ""

        try:
            if (urlparseresult.scheme == "ftp"):
                # use ftplib here
                connection = FTP(urlparseresult.netloc, timeout=confJson['timeout'])
                connection.login(user=confJson['username'], passwd=base64.b64decode(str(confJson['password'])))
                logging.debug("New FTP connection " + str(connection))
            elif (urlparseresult.scheme == "sftp"):
                # curl is our backup .. lets try pysftp now
                #downloadFromCurl(download_url, downloadfile)
                connection = pysftp.Connection(urlparseresult.netloc, username=confJson['username'], password=base64.b64decode(str(confJson['password'])))
                connection.timeout = confJson['timeout']
                logging.info("created new connection")
                logging.info(str(connection))
            else:
                connection = urllib2.urlopen(download_url, timeout=confJson['timeout'])
                logging.debug("New HTTP connection " + str(connection))
        except:
            if (nTries > 0):
                logging.warning("Trying : " + str(nTries))
                connect_with_retry(download_url, (nTries - 1), callback, downloadfile)
            else:
                raise

        connList[connLookupKey] = connection
            
    callback(urlparseresult.scheme, connection, downloadfile, urlparseresult.path)


def downloadFile():
    global confJson
    global connList
    try:
        for url, downloadfile in zip(confJson['download_url'], confJson['download_file']):
            download_url = url.encode('utf-8')
            try:
                connect_with_retry(download_url, confJson['num_retries'], updateFile, str(downloadfile))
            except Exception as errMsg:
                # completed all tries ... download next file if exists
                logging.error("Error in downloading from url [" + download_url + "] : " + str(errMsg))
                continue
    except Exception as errMsg:
        logging.critical("Error in downloading file : " + str(errMsg))
        sys.exit(1)

        
def downloadFileInInterval(runAsDaemon):
    global connList
    connList = {}
    if not runAsDaemon:
        downloadFile()
    else:
        logging.debug("Running as a daemon")
        while runAsDaemon:
            loadConfFile()
            poll_freq = confJson['poll_freq']
            logging.debug("Polling at interval [" + str(poll_freq) + "] seconds")
            downloadFile()
            time.sleep(poll_freq)

def runDownload(runAsDaemon):
    downloadFileInInterval(runAsDaemon)
    # download_thread = Thread(target=downloadFileInInterval, args=(runAsDaemon,))
    # download_thread.daemon = runAsDaemon
    # download_thread.start()

def main(argv):
    isSystemExit = False
    try:
        runAsDaemon = getOptions(str(argv[0]), argv[1:])
        arc_helper = archive_helper(confJson['archive_dir'], confJson['archive_days'])

        arc_helper.fetch_files(confJson['download_file'])

        runDownload(runAsDaemon)
        while runAsDaemon:
            pass
    except SystemExit:
        logging.debug("Got a system exit.. exiting")
        isSystemExit = True
    except Exception as e:
        logging.critical("Got an exception ..." + str(e) + " Shutting down")
    finally:
        if not isSystemExit:
            logging.debug("Shutting down the download script for instance [" + confJson['instance_name'] + "]")
        # call file archival before we leave
        arc_helper.archive_files(confJson['download_file'])
        
if __name__ == "__main__":
    main(sys.argv)
                

