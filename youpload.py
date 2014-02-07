#!/usr/bin/python

import argparse
import httplib
import httplib2
import os
import random
import sys
import time

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow


VIDEO_EXTS = ['3gp', 'avi', 'mov', 'mpg', 'mpeg', 'mp4', 'flv', 'mts', 'wmv', 'm4v']
VIDEOS_PER_PAGE = 50

MOVIES_DIRECTORY_MAC = 'Movies'

# playlists that are not backed up folders... like normal playlists
NON_BACKUP_PLAYLISTS = ['Classics']

video_fails = []
playlist_fails = []

playlists = dict()  # relative path -> id
uploaded_videos = dict()  # relative path -> id


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

"""
    Crawler
"""

def prompt(videos_dir, username, realname):
    print "\n---------------------------------------------------------------------------\n"
    print "    This script will examine all files and directories in: " + videos_dir + ""
    print "    and upload them to YouTube account: " + username + " (" + realname + ")"
    print "\n---------------------------------------------------------------------------\n"
    return query_yes_no("Are you sure you want to continue?")

def crawl(youtube, start_path):
    foo = os.walk(start_path)
    for data in foo:
        (dirpath, dirnames, filenames) = data
        for f in filenames :
            ext = f.lower().split(".")[-1]
            if ext in VIDEO_EXTS: 
                fullpath = dirpath + "/" + f
                relpath = fullpath[len(start_path):]

                video_id = upload_video(youtube, fullpath, f, relpath)
                if video_id:
                    playlist_id = get_playlist(youtube, relpath)
                    if playlist_id:
                        add_to_playlist(youtube, video_id, playlist_id)

    print 'FAILED VIDEOS = ' + str(video_fails)
    print 'FAILED PLAYLISTS = ' + str(playlist_fails)


"""
      API Calls
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
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


class RunFlowDefaultArgs:
  # hack b/c the argparser used by google's library messes up our argparser
  auth_host_name = 'localhost'
  noauth_local_webserver = False
  auth_host_port = [8080, 8090]
  logging_level = 'ERROR'


def get_authenticated_service():
  args = RunFlowDefaultArgs()
  flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
    scope=YOUTUBE_SCOPE,
    message=MISSING_CLIENT_SECRETS_MESSAGE)

  storage = Storage("%s-oauth2.json" % sys.argv[0])
  credentials = storage.get()

  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage, args)

  return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    http=credentials.authorize(httplib2.Http()))


def getUserInfo(youtube):
  user_id = None
  username = None
  try:
    res = youtube.channels().list(part="id,snippet", mine=True).execute()
    user_id = str(res['items'][0]['id'])
    username = res['items'][0]['snippet']['title']
  except:
    print(str(sys.exc_info()))
    sys.exit()
  return [user_id, username]


def get_playlist(youtube, fullpath):
    p = fullpath.split('/')
    playlist_path = '/'.join(p[:-1])
    if not playlist_path in playlists:
        if len(p) == 1:
            playlists[playlist_path] = None
        else:
            playlist_id = create_playlist(youtube, playlist_path, playlist_path)
            playlists[playlist_path] = playlist_id

        print 'Playist ' + str(playlist_path)
    return playlists[playlist_path]


def get_playlists(youtube):
    print 'Getting all playlists and videos....'
    pageToken = None
    while True:
        try:
            playlists_response = youtube.playlists().list(
             part="id,snippet",
             mine=True,
             maxResults=VIDEOS_PER_PAGE,
             pageToken=pageToken
            ).execute()
            for playlist in playlists_response['items']:
                title = playlist['snippet']['title']
                playlist_path = playlist['snippet']['description']
                playlist_id = playlist['id']
                if title in NON_BACKUP_PLAYLISTS:
                    continue
                playlists[playlist_path] = playlist_id
                print 'Existing playlist ' + playlist_path + ' ---> ' + str(playlist_id)
            if not 'nextPageToken' in playlists_response:
                break
            pageToken = playlists_response['nextPageToken']
        except:
            print(str(sys.exc_info()))
            break

def get_videos_in_playlist(youtube, playlist_id):
    print 'Getting videos in playlist ' + str(playlist_id)
    pageToken = None
    while True:
        try:
            playlistitems_list_request = youtube.playlistItems().list(
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
                uploaded_videos[video_path] = video_id
                print 'Uploaded video ' + video_path + ' --> ' + str(video_id)
            if not 'nextPageToken' in playlistitems_list_response:
                break
            pageToken = playlistitems_list_response['nextPageToken']
        except:
            print(str(sys.exc_info()))
            break

def get_videos(youtube, playlists):
    for p_path in playlists:
        p_id = playlists[p_path]
        get_videos_in_playlist(youtube, p_id)

def upload_video(youtube, filepath, title, description, keywords = None, category = 22, privacyStatus = VALID_PRIVACY_STATUSES[1]):
  print 'Adding video ' + filepath + ' as ' + title
  if description in uploaded_videos:
      print '              VIDEO ALREADY UPLOADED...'
      return None
  try:
      tags = None
      if keywords:
        tags = keywords.split(",")

      body=dict(
        snippet=dict(
          title=title,
          description=description,
          tags=tags,
          categoryId=category
        ),
        status=dict(
          privacyStatus=privacyStatus
        )
      )

      # Call the API's videos.insert method to create and upload the video.
      insert_request = youtube.videos().insert(
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

      video_id = resumable_upload(insert_request)
      if video_id:
          print '       Success!!! video id = ' + str(video_id)
      else:
          video_fails.append(description)
          print '              Fail........asdlfklsdafklsadf'
      return video_id
  except:
      video_fails.append(description)
      print '              Epic Fail........'  
      return None


def create_playlist(youtube, playlist_name, playlist_description):
    print 'Creating playlist ' + playlist_name
    try:
        playlists_insert_response = youtube.playlists().insert(
          part="snippet,status",
          body=dict(
            snippet=dict(
              title=playlist_name,
              description=playlist_description
            ),
            status=dict(
              privacyStatus="private"
            )
          )
        ).execute()
        playlist_id = playlists_insert_response["id"]
        print '     Success! playlist id = ' + str(playlist_id)
        return playlist_id 
    except:
        print '     Fail.......'
        playlist_fails.append(playlist_description)
        return None

def add_to_playlist(youtube, video_id, playlist_id):
    print 'Adding ' + str(video_id) + ' to playlist ' + str(playlist_id)
    try:
        add_video_request=youtube.playlistItems().insert(
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
        print '      Success!!'
    except:
        print '                Fail..........'

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
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

    if args.dir:
        videos_dir = args.dir
    else:
        videos_dir = os.path.join(os.path.expanduser('~'), MOVIES_DIRECTORY_MAC)

    youtube = get_authenticated_service()
    [user_id, username] = getUserInfo(youtube)

    if args.no_prompt or prompt(videos_dir, user_id, username):
      print 'YES'
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
