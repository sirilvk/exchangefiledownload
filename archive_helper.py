import os, time, sys
import re, ntpath
import shutil
import logging

class archive_helper:
    days_ = 0
    archive_dir_ = ""

    def __init__(self, archive_dir, archive_days):
        self.archive_dir_ = archive_dir
        self.days_ = archive_days
        if not os.path.exists(self.archive_dir_):
            os.makedirs(self.archive_dir_)


    def archive_files(self, file_list = []):
        # anything older than the said days will be cleaned up first
        logging.info("Archiving files to directory : " + self.archive_dir_)
        now = time.time()
        for downloadfile in file_list:
            dfile = ntpath.basename(downloadfile)
            existingfiles = [ f for f in os.listdir(self.archive_dir_) if re.match(dfile + '\..*', f)]
            for ef in existingfiles:
                if (os.stat(os.path.join(self.archive_dir_, ef)).st_mtime < now - self.days_ * 86400):
                    os.remove(os.path.join(self.archive_dir_, ef))

            # now save the existing files with the current timestamp
            shutil.copyfile(downloadfile, os.path.join(self.archive_dir_, dfile) + '.' + time.strftime("%m-%d-%Y"))

    def fetch_files(self, file_list = []):
        logging.info("Fetching files from directory : " + self.archive_dir_)
        for downloadfile in file_list:
            dfile = ntpath.basename(downloadfile)
            arcfilelist = map(str(self.archive_dir_+'/{0}').format, [f for f in os.listdir(self.archive_dir_) if re.match(dfile + '\..*', f)])
            if not arcfilelist:
                logging.info("No files exists in archive directory : " + self.archive_dir_)
            else:
                latestfile =  max(arcfilelist, key=os.path.getctime)
                shutil.copyfile(latestfile, downloadfile)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    arc_helper = archive_helper("/root/exchangeFileDownload/archive", 2)
    arc_helper.fetch_files(['/tmp/exchange.download', '/tmp/exchange.download2'])
    arc_helper.archive_files(['/tmp/exchange.download', '/tmp/exchange.download2'])
