# -*- coding: utf-8 -*-
#!/usr/bin/python

"""
   youpload.py

   Upload videos placed within a directory to your YouTube account.

   Requires:
       TODO google client
       YouTube account http://youtube.com

   Usage:

   Put the client_secrets.json file in the videos directory you are uploading.
   Run the script and pass the videos directory as a command-line parameter.

   The best way to use this is to just fire this up in the background and forget about it.
   If you find you have CPU/Process limits, then setup a cron job.

   cron entry (runs at the top of every hour)
   0  *  *   *  * /full/path/to/youpload.py > /dev/null 2>&1

   Februrary 2014
   Momchil Tomov     about.me/tomov

   You may use this code however you see fit in any form whatsoever.

"""


import argparse
import httplib
import httplib2
import os
import random
import sys
import time
import datetime
import shelve

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow


VIDEO_EXTS = ['3gp', 'avi', 'mov', 'mpg', 'mpeg', 'mp4', 'flv', 'mts', 'wmv', 'm4v']
VIDEOS_PER_PAGE = 50

MOVIES_DIRECTORY_MAC = 'Movies'

CREATED_PLAYLISTS_FILENAME = 'youploader.created_playlists'
UPLOADED_VIDEOS_FILENAME = 'youploader.uploaded_videos'
FAILED_UPLOADS_FILENAME = "youploader.failed_uploads.log"
IGNORED_FILES_FILENAME = "youploader.ignored_files.log"

""" API constants
"""

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google Cloud Console at
# https://cloud.google.com/console.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "client_secrets.json"
CLIENT_ACCESS_TOKEN_FILE = ".youploader.oauth2.json"

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

    %s

with information from the Cloud Console
https://cloud.google.com/console

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
"""

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


""" Helpers
"""

def str2key( ss ):
    if not isinstance(ss, unicode):
        s = ss.decode('utf-8')
    else:
        s = ss
    return s.encode("utf-8")

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":True,   "y":True,  "ye":True,
             "no":False,     "n":False}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")


class Youploader:
    """
        Youploader class
    """

    youtube = None
    videos_dir = None
    client_secrets_filepath = None

    # Logs
    playlists = None  # shelve dict, relative path -> id
    uploaded_videos = None  # shelve dict, relative path -> id
    failed_uploads = None # text log
    ignored_files = None # text log

    created_playlists_file = None
    uploaded_videos_file = None

    # Stats
    total_files = 0
    total_dirs = 0
    skipped_playlists = 0
    skipped_videos_count = 0
    ignored_files_count = 0
    failed_videos_count = 0
    failed_playlists = dict()
    new_videos_count = 0
    new_playlists_count = 0
    session_info = None
    user_id = None
    username = None


    def __init__(self, videos_dir):
      # set videos dir first
      self.videos_dir = videos_dir

      # authenticate
      self.youtube = self.get_authenticated_service()

      # get account info
      [self.user_id, self.username] = self.getUserInfo()

      # set session info
      now = datetime.datetime.utcnow().strftime("%m/%d%/%Y %H:%M");
      self.session_info = "New upload session started on " + now + \
              "\nDirectory: " + self.videos_dir + "" + \
              "\nAccount: " + self.user_id + " (" + self.username + ")"


    """
        Crawler
    """

    def prompt(self):
        print "\n---------------------------------------------------------------------------\n"
        print "    This script will examine all files and directories in: " + self.videos_dir + ""
        print "    and upload them to YouTube account: " + self.user_id + " (" + self.username + ")"
        print "\n---------------------------------------------------------------------------\n"
        return query_yes_no("Are you sure you want to continue?")

    def getHistory(self):
        self.get_playlists()
        self.get_videos()
        self.failed_uploads = open(os.path.join(self.videos_dir, FAILED_UPLOADS_FILENAME), 'a')
        self.ignored_files = open(os.path.join(self.videos_dir, IGNORED_FILES_FILENAME), 'a')

    def closeHistoryFiles(self):
        self.playlists.close()
        self.uploaded_videos.close()
        self.failed_uploads.close()
        self.ignored_files.close()

    def crawl(self):
        self.failed_uploads.write('\n' + self.session_info + '\n')
        self.ignored_files.write('\n' + self.session_info + '\n')
        self.skipped_playlists = len(self.playlists)

        start_path = self.videos_dir
        foo = os.walk(start_path)
        for data in foo:
            (dirpath, dirnames, filenames) = data
            self.total_dirs += 1
            for f in filenames :
                self.total_files += 1
                fullpath = dirpath + "/" + f
                relpath = fullpath[len(start_path):]
                ext = f.lower().split(".")[-1]
                if ext in VIDEO_EXTS: 
                  if not str2key(relpath) in self.uploaded_videos:
                    video_id = self.upload_video(fullpath, f, relpath)
                    if video_id:
                        playlist_id = self.get_playlist(relpath)
                        if playlist_id:
                            self.add_to_playlist(video_id, playlist_id)
                  else:
                    video_id = self.uploaded_videos[str2key(relpath)]
                    print "Skipping video " + relpath + ": already uploaded with id = " + str(video_id)
                    self.skipped_videos_count += 1
                else:
                  print 'Ignored file ' + relpath
                  self.ignored_files.write(fullpath + '\n')
                  self.ignored_files_count += 1

    def printStats(self):
        print "\n\nCrawling finished!"
        print "Examined " + str(self.total_files) + " files and " + str(self.total_dirs) + " directories"
        print "Uploaded " + str(self.new_videos_count) + " videos (" \
            + str(self.skipped_videos_count) + " videos were already uploaded, " \
            + str(self.failed_videos_count) + " uploads failed, " \
            + str(self.ignored_files_count) + " files were ignored)" 
        print "Created " + str(self.new_playlists_count) + " playlists (" \
            + str(self.skipped_playlists) + " sets were already created, " \
            + str(len(self.failed_playlists)) + " sets failed)"
        print ""


    """
          API Calls
    """

    class RunFlowDefaultArgs:
      # hack b/c the argparser used by google's library messes up our argparser
      auth_host_name = 'localhost'
      noauth_local_webserver = False
      auth_host_port = [8080, 8090]
      logging_level = 'ERROR'


    def get_authenticated_service(self):
      args = self.RunFlowDefaultArgs()
      self.client_secrets_filepath = os.path.join(self.videos_dir, CLIENT_SECRETS_FILE)
      flow = flow_from_clientsecrets(self.client_secrets_filepath,
        scope=YOUTUBE_SCOPE,
        message=MISSING_CLIENT_SECRETS_MESSAGE % self.client_secrets_filepath)

      self.client_access_token_filepath = os.path.join(self.videos_dir, CLIENT_ACCESS_TOKEN_FILE)
      storage = Storage(self.client_access_token_filepath)
      credentials = storage.get()

      if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

      return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))


    def getUserInfo(self):
      user_id = None
      username = None
      try:
        res = self.youtube.channels().list(part="id,snippet", mine=True).execute()
        user_id = str(res['items'][0]['id'])
        username = res['items'][0]['snippet']['title']
      except:
        print(str(sys.exc_info()))
        sys.exit()
      return [user_id, username]


    def get_playlist(self, relpath):
        p = relpath.split('/')
        playlist_path = '/'.join(p[:-1])
        if not str2key(playlist_path) in self.playlists:
          if not playlist_path:
            playlist_path = "/"
          playlist_id = self.create_playlist(playlist_path, playlist_path)
          self.playlists[str2key(playlist_path)] = playlist_id
          print 'Playlist ' + str(playlist_path)
        return self.playlists[str2key(playlist_path)]


    def get_playlists(self):
        self.created_playlists_file = os.path.join(self.videos_dir, CREATED_PLAYLISTS_FILENAME)
        self.playlists = shelve.open(self.created_playlists_file)
        if len(self.playlists) > 0:
          print("\n---------- Loading list of already created playlists from file " + self.created_playlists_file + " ----------\n")
        else:
          print("\n---------- Getting list of already created playlists from YouTube account ----------\n")
          pageToken = None
          while True:
              try:
                  playlists_response = self.youtube.playlists().list(
                   part="id,snippet",
                   mine=True,
                   maxResults=VIDEOS_PER_PAGE,
                   pageToken=pageToken
                  ).execute()
                  for playlist in playlists_response['items']:
                      title = playlist['snippet']['title']
                      playlist_path = playlist['snippet']['description']
                      playlist_id = playlist['id']
                      self.playlists[str2key(playlist_path)] = playlist_id
                      print 'Existing playlist ' + playlist_path + ' ---> ' + str(playlist_id)
                  if not 'nextPageToken' in playlists_response:
                      break
                  pageToken = playlists_response['nextPageToken']
              except:
                  print(str(sys.exc_info()))
                  # cleanup
                  self.playlists.close()
                  os.remove(self.created_playlists_file + ".db")
                  sys.exit()
        print '\nLoaded ' + str(len(self.playlists)) + ' playlists!\n\n'

    def get_videos_in_playlist(self, playlist_id, playlist_path):
        print '----- Getting videos in playlist ' + str(playlist_path) + ''
        pageToken = None
        while True:
            try:
                playlistitems_list_request = self.youtube.playlistItems().list(
                    playlistId=playlist_id,
                    part="id,snippet",
                    maxResults=VIDEOS_PER_PAGE,
                    pageToken=pageToken
                )
                playlistitems_list_response = playlistitems_list_request.execute()
                for playlist_item in playlistitems_list_response["items"]:
                    title = playlist_item["snippet"]["title"]
                    video_path = playlist_item["snippet"]["description"]
                    video_id = playlist_item["snippet"]["resourceId"]["videoId"]
                    self.uploaded_videos[str2key(video_path)] = video_id
                    print 'Uploaded video ' + video_path + ' --> ' + str(video_id)
                if not 'nextPageToken' in playlistitems_list_response:
                    break
                pageToken = playlistitems_list_response['nextPageToken']
            except:
                print(str(sys.exc_info()))
                # cleanup
                self.uploaded_videos.close()
                os.remove(self.uploaded_videos_file + ".db")
                sys.exit()

    def get_videos(self):
        self.uploaded_videos_file = os.path.join(self.videos_dir, UPLOADED_VIDEOS_FILENAME)
        self.uploaded_videos = shelve.open(self.uploaded_videos_file)
        try:
          if len(self.uploaded_videos) > 0:
            print("\n---------- Loading list of already uploaded videos from file " + self.uploaded_videos_file + " ----------\n")
          else:
            print("\n---------- Getting list of already uploaded videos from YouTube account ----------\n")
            for p_path in self.playlists:
                p_id = self.playlists[p_path]
                self.get_videos_in_playlist(p_id, p_path)
        except:
          print(str(sys.exc_info()))
          # cleanup
          self.uploaded_videos.close()
          os.remove(self.uploaded_videos_file + ".db")
          sys.exit()      
        print '\nLoaded ' + str(len(self.uploaded_videos)) + ' videos!\n\n'

    def upload_video(self, filepath, title, relpath, keywords = None, category = 22, privacyStatus = VALID_PRIVACY_STATUSES[1]): # careful when changing the privacy status
      video_id = None
      print 'Uploading video ' + relpath + '...'
      assert(not str2key(relpath) in self.uploaded_videos)
      try:
          tags = None
          if keywords:
            tags = keywords.split(",")
          body=dict(
            snippet=dict(
              title=title,
              description=relpath,
              tags=tags,
              categoryId=category
            ),
            status=dict(
              privacyStatus=privacyStatus
            )
          )
          # Call the API's videos.insert method to create and upload the video.
          insert_request = self.youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            # The chunksize parameter specifies the size of each chunk of data, in
            # bytes, that will be uploaded at a time. Set a higher value for
            # reliable connections as fewer chunks lead to faster uploads. Set a lower
            # value for better recovery on less reliable connections.
            #
            # Setting "chunksize" equal to -1 in the code below means that the entire
            # file will be uploaded in a single HTTP request. (If the upload fails,
            # it will still be retried where it left off.) This is usually a best
            # practice, but if you're using Python older than 2.6 or if you're
            # running on App Engine, you should set the chunksize to something like
            # 1024 * 1024 (1 megabyte).
            media_body=MediaFileUpload(filepath, chunksize=-1, resumable=True)
          )
          video_id = self.resumable_upload(insert_request)
          if video_id:
              self.uploaded_videos[str2key(relpath)] = video_id
              print '    Success. Video id = ' + str(video_id)
              self.new_videos_count += 1
          else:
              self.failed_uploads.write('Video: ' + relpath + '\n')
              self.failed_videos_count += 1
      except KeyboardInterrupt:
          self.printStats()
          print "\nUploading session interrupted by user..."
          sys.exit()
      except:
          print(str(sys.exc_info()))
          self.failed_uploads.write('Video: ' + relpath + '\n')
          self.failed_videos_count += 1
      return video_id


    def create_playlist(self, playlist_name, relpath):
        print 'Creating playlist ' + relpath
        playlist_id = None
        try:
            playlists_insert_response = self.youtube.playlists().insert(
              part="snippet,status",
              body=dict(
                snippet=dict(
                  title=playlist_name,
                  description=relpath
                ),
                status=dict(
                  privacyStatus="private"
                )
              )
            ).execute()
            playlist_id = playlists_insert_response["id"]
            self.playlists[str2key(relpath)] = playlist_id
            print '    Success. Playlist id = ' + str(playlist_id) 
            self.new_playlists_count += 1
        except KeyboardInterrupt:
          self.printStats()
          print "\nUploading session interrupted by user..."
          sys.exit()
        except:
          print(str(sys.exc_info()))
          self.failed_uploads.write('Playlist: ' + relpath + '\n')
          self.failed_playlists[str2key(relpath)] = 1
        return playlist_id

    def add_to_playlist(self, video_id, playlist_id):
        print 'Adding ' + str(video_id) + ' to playlist ' + str(playlist_id)
        try:
            add_video_request=self.youtube.playlistItems().insert(
              part="snippet",
              body={
                'snippet': {
                  'playlistId': playlist_id, 
                  'resourceId': {
                          'kind': 'youtube#video',
                      'videoId': video_id
                    }
                #'position': 0
                }
              }
            ).execute()
            print '    Success.'
        except:
            print '    Failed...'

    # This method implements an exponential backoff strategy to resume a
    # failed upload.
    def resumable_upload(self, insert_request):
      response = None
      error = None
      retry = 0
      while response is None:
        try:
          status, response = insert_request.next_chunk()
          if 'id' in response:
            #print "Video id '%s' was successfully uploaded." % response['id']
            return response['id']
          else:
            #exit("The upload failed with an unexpected response: %s" % response)
            return None
        except HttpError, e:
          if e.resp.status in RETRIABLE_STATUS_CODES:
            error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                 e.content)
          else:
            raise
        except RETRIABLE_EXCEPTIONS, e:
          error = "A retriable error occurred: %s" % e

        if error is not None:
          print error
          retry += 1
          if retry > MAX_RETRIES:
            exit("No longer attempting to retry.")

          max_sleep = 2 ** retry
          sleep_seconds = random.random() * max_sleep
          print "Sleeping %f seconds and then retrying..." % sleep_seconds
          time.sleep(sleep_seconds)

"""
    Main
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload directories to YouTube.')
    parser.add_argument('--dir', action='store', help='Directory with videos to upload')
    parser.add_argument('--no-prompt', action='store_true', help="Avoid prompt. Useful for automation.")
    args = parser.parse_args()

    # parse videos directory
    if args.dir:
        videos_dir = args.dir
    else:
        videos_dir = os.path.join(os.path.expanduser('~'), MOVIES_DIRECTORY_MAC)

    # create uploader object
    youploader = Youploader(videos_dir)

    # crawl files
    if args.no_prompt or youploader.prompt():
      print '\n' + youploader.session_info
      youploader.getHistory()
      youploader.crawl()
      youploader.printStats()
      youploader.closeHistoryFiles()
    else:
      print 'NO'

"""
    flick = Uploadr(args)
    if args.no-prompt or flick.prompt():
        print '\n' + flick.session_info
        flick.getHistory()
        flick.crawl()
        flick.printStats()
        flick.closeHistoryFiles()
    else:
        print "\nExiting..."
"""

  #get_playlists(youtube)
  #get_videos(youtube, playlists)
  
  #crawl(youtube, videos_dir)
