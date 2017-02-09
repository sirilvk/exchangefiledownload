##########################################################################
                  Download Script Information
##########################################################################

1. Setup:

Get pip installed on the host.
Just run the python get-pip.py (file available in the project).

Get the encryption libraries for the python sftp to work using yum

yum install gcc libffi-devel python-devel openssl-devel glibc-devel

Now run the pip install -r dev-requirements.txt

This will setup the environment with all the required libraries.

2. Setup Config script:

The config script (a json file) is required for the download script to run.
A sample config script is as given below:

{
    "instance_name": "cmegroup",
    "download_url" : [
        "sftp://167.204.41.33/cme/ftp/SBEFix/Production/StrTemplates/streamlinemktdata.xml",
        "sftp://167.204.41.33/cme/ftp/SBEFix/Production/StrTemplates/streamlinemktdata.xml"
    ],
    "username"     : "ftpdwnld",
    "password"     : "ZnRwZHdubGQ=",
    "timeout"      : 3,
    "retain_con"   : 1,
    "download_file" : [
        "/tmp/exchange.download",
        "/tmp/exchange.download2"        
    ],
    "poll_freq"    : 5,
    "num_retries"  : 3
}

The download script needs all of these json fields to be set. Each of these
fields is explained as follows:
1. instance_name : defines the download script instance (you can run multiple instances of
these download script for various venues). Just name it based on the venue so it will be
easier to identify.
2. download_url : These are the grouping of download urls you wish to download using this
script. Group all the url's which need the same authentication (username and password).
Url's with different authentication wouldn't work in a single instance.
3. username and password : obviously the requirements for authentication.
4. timeout : The file request timeout. Specify it accordingly.
5. retain_con : This is important if you wish to use the same connection for the entire
timespan of the script. If set to 1 it will reuse the same connection and if not it will
close and start a new connection all the time.
6. download_file : This is the grouping of the target file names for the download_url's 
to be stored.
7. poll_freq : This is the frequency at which the script will be polling for the file
at the server. Any file modifications will only be picked up in this frequency.
8. num_retries : These are the connection retries you wish to make before skipping that 
particular download_url.

3. Start the script:

You can start the script from command line as 

       python downloadFromUrl.py -c config.json

for a one time connection and download.

If you wish to run it as a service run it as 

       python downloadFromUrl.py -c config.json -d

In case if you wish to debug (have more debug messages)

       python downloadFromUrl.py -c config.json -d -l DEBUG

