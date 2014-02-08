YouTube Uploader
==========

Youploader.py is a simple Python script for uploading your videos to YouTube. It also arranges them into 
playlists according to the directory structure of your videos directory.

The script is superior to other YouTube uploaders in several ways:

1. It preserves the layout of your videos directory by organizing the uploads playlists.

2. It can be safely interrupted and restarted and will avoid making duplicate uploads.

3. It can be automated to regularly back up your videos directory.


Instructions
==========

The script in its current version is only tested on Mac OS X so all instructions are targeted to Mac users.


Step 0. Prerequisites
--------------

1. Python

Mac OS X 10.8 comes with Python preinstalled. To verfiy that, open a terminal and type ``python -V``. If you don't have it, get it from `here <http://www.python.org/getit/>`_.

2. Git

To see if you have Git installed, open a terminal and type ``git --version``. If you don’t have it, you can get the latest version from `here <https://code.google.com/p/git-osx-installer/downloads/list>`_.

Step 1. Download the script
---------------

Go to your favorite hacking directory and clone the repo::

	git clone https://github.com/tomov/youtube-upload.git

Then go to the script directory::

	cd youtube-upload
	
Step 2. Run the script
---------------

Make sure to have your YouTube credentials JSON file saved in your videos directory (if you don't, should issue a new set of credentials by following the instructions `here <https://developers.google.com/youtube/registering_an_application>`_). Then run the script::

	python uploadr.py --dir=[videos directory]

Here is what this would look like for an example directory::

	python uploadr.py --dir="/Users/tomov90/Downloads/My Videos/"

You will be forwarded to a YouTube confirmation page in your browser. Click ``Accept`` and go back to the terminal. You will get another prompt asking you if you are sure you want to continue. Type ``Y`` and let python do the rest of the work! Note that for this example directory, your JSON credentials file would have to be "/Users/tomov90/Downloads/My Videos/client_secrets.json".


Step 3. Check if everything is fine
-------------------

Once the script has finished, go to your YouTube account `video manager <http://www.youtube.com/my_videos>`_ and make sure everything is there. Check the Uploads count at the top of the page and make sure it looks right. I also recommend checking the playlists by clicking "Playlists" in the Video Manager left sidebar to make sure the videos are organized according to the directory layout.


Step 4. Re-running the script
-------------------

To back up the same folder to the same YouTube account, simply run::

	python youpload.py --dir=[videos directory]

And the upload should start immediately. The app also saves a history of all previously uploaded videos and unless you move stuff around or rename your files or directories, it will avoid uploading duplicate videos or creating duplicate playlists.


Step 5. Automate the script
-------------------

The best part about a command-line script like this is that you can easily automate it. You can do this by creating a cron job through the command line::

	crontab -e

This will open the crontab file. Simply add the line::

	0  *  *  *  *  /full/path/to/youtube-upload/youpload.py --dir=[videos directory] --no-prompt > /dev/null 2>&1

Which will run the script in the background every hour. For example, for me the line would be::

	0  *  *  *  * /Users/tomov90/Dev/youtube-upload/youpload.py --dir="/Users/tomov90/Downloads/My Videos/" --no-prompt > /dev/null 2>&1

Alternatively, you can use the Mac Automator by following `this <http://arstechnica.com/apple/2011/03/howto-build-mac-os-x-services-with-automator-and-shell-scripting/>`_ or `this <http://lifehacker.com/5668648/automate-just-about-anything-on-your-mac-no-coding-required>`_ tutorial.


Advanced
===================

The script works with relative paths, so if you move your videos directory to a different location or even if you upload it from a different computer, it should still work. Those relative paths are stored in the descriptions of the videos and playlists in your YouTube account, so please avoid changing them. The script also never deletes uploaded videos.


Files
-------------------

You will notice that the script creates a bunch of files with the prefix ``youploader.*``  in your photos directory. One of them will be hidden, namely::

	.youploader.oauth2.json

This file contains your YouTube account access information so you don't have to enter it every time. However, this also means that anyone who has access to this file can access your precious videos, so make sure to avoid sending it to random people. If you ever delete it, you will have to re-approve the script for your account.

In addition, the script saves a history of all uploaded videos and playlists in these files::

	youploader.uploaded_videos.db
	youploader.created_playlists.db

This helps the script avoid duplicate uploads. If you delete them, the script will still avoid duplicate uploads by first fetching a list of all videos and playlists from the YouTube account. In fact, if for some reason you upload videos to the same account from different directories, it might make sense to delete those files and let the script "refresh" them with the latest data in the YouTube account.

Finally, the script creates a log of failed uploads and ignored files::

	youploader.failed_uploads.log
	youploader.ignored_files.log

This is for debugging purposes and to make sure none of your important files were ignored or failed to upload for some reason. Feel free to remove them.


Future work
-----------------

The script is far from perfect and there is plenty of room for improvement. Feel free to fork, change, improve, and distribute as you see fit! Some suggestions for improvements:

1. Splitting videos

Unfortunatley YouTube does not allow uploading videos longer than 10 minutes. Currently the script will try and fail to upload those so you will simply have to split them manually. It would be great if someone adds a video splitting tool that automatically does that before attempting to upload.

2. Windows and Linux compatibility

It would be awesome if someone tried to see if this works on other platforms. It will surely need some help to get it going under Windows since I've hardcoded a bunch of forward slashes here and there (sorry about that).

3. ``--dry-run`` option

It would be great to have the option to run the script without actually uploading or changing anything, just to see what will happen (which files will be uploaded, how many of them, etc)

4. Pause/resume script

Currently you can interrupt the script with ``Cmd+C`` and restart it. It would be nice if you could only pause it.


License
==============

Youpload.py consists of code by Momchil Tomov and from the Google API sample code page. Feel free to modify, distribute, and use as you see fit!
