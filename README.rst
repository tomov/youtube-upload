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

Once the script has finished, go to your Flickr account photo stream and make sure everything is there. Check the photo count at the top of the photo stream and make sure it looks right. I also recommend checking the sets and collections in the `organizer <http://www.flickr.com/photos/organize/>`_ to make sure the photos are neatly organized like they were in your photos directory.


Step 4. Re-running the script
-------------------

To back up the same folder to the same Flickr account, simply run::

	python uploadr.py --dir=[photos directory]

And the upload should start immediately. You won't have to re-enter your API key and secret since the app saves them in your photos directory. The app also saves a history of all previously uploaded photos and unless you move stuff around or rename your files or directories, it will avoid uploading duplicate photos or creating duplicate sets and collections.


Step 5. Automate the script
-------------------

The best part about a command-line script like this is that you can easily automate it. You can do this by creating a cron job through the command line::

	crontab -e

This will open the crontab file. Simply add the line::

	0  *  *  *  *  /full/path/to/uploadr.py/uploadr/uploadr.py --dir=[photos directory] --no-prompt > /dev/null 2>&1

Which will run the script in the background every hour. For example, for me the line would be::

	0  *  *  *  * /Users/tomov90/Dev/uploadr.py/uploadr/uploadr.py --dir="/Users/tomov90/Downloads/My Photos/" --no-prompt > /dev/null 2>&1

Alternatively, you can use the Mac Automator by following `this <http://arstechnica.com/apple/2011/03/howto-build-mac-os-x-services-with-automator-and-shell-scripting/>`_ or `this <http://lifehacker.com/5668648/automate-just-about-anything-on-your-mac-no-coding-required>`_ tutorial.


Advanced
===================

The script works with relative paths, so if you move your photos directory to a different location or even if you upload it from a different computer, it should still work. Those relative paths are stored in the descriptions of the photos, sets, and collections in your Flickr account, so please avoid changing them. The script also never deletes uploaded photos.


Files
-------------------

You will notice that the script creates a bunch of files with the prefix ``uploadr.*``  in your photos directory. Some of them will be hidden, namely::

	.uploadr.flickrToken
	.uploadr.apiKey
	.uploadr.apiSecret

Those contain your Flickr account access information so you don't have to enter it every time. However, this also means that anyone who has access to those files can access your precious photos, so make sure to avoid sending them to random people. If you ever delete them, you will have to pass the API key and secret as command-line parameters as discussed in Step 2.

In addition, the script saves a history of all uploaded photos, sets, and collections in these files::

	uploadr.uploaded_images.db
	uploadr.created_sets.db
	uploadr.created_collections.db

This helps the script avoid duplicate uploads. If you delete them, the script will still avoid duplicate uploads by first fetching a list of all images, sets, and collections from the Flickr account. In fact, if for some reason you upload photos to the same account from different directories, it might make sense to delete those files and let the script "refresh" them with the latest data in the Flickr account.

Finally, the script creates a log of failed uploads and ignored files::

	uploadr.failed_uploads.log
	uploadr.ignored_files.log

This is for debugging purposes and to make sure none of your important files were ignored or failed to upload for some reason.


Future work
-----------------

The script is far from perfect and there is plenty of room for improvement. Feel free to fork, change, improve, and distribute as you see fit! Some suggestions for improvements:

1. Windows and Linux compatibility

It would be awesome if someone tried to see if this works on other platforms. It will surely need some help to get it going under Windows since I've hardcoded a bunch of forward slashes here and there (sorry about that).

2. ``--dry-run`` option

It would be great to have the option to run the script without actually uploading or changing anything, just to see what will happen (which files will be uploaded, how many of them, etc)

3. Pause/resume script

Currently you can interrupt the script with ``Cmd+C`` and restart it. It would be nice if you could only pause it.

4. Subcollections

Currently the Flickr collections API is unofficial and I could not figure out how to create a collection within a collection. So if you have lots of nested directories, e.g. ``/path/to/some/album/``, the script will create collections ``/path``, ``/path/to``, and ``/path/to/some``, and a set ``album`` nested inside the last collection. Ideally, once Flickr releases their collections API, we would like instead to create a collection ``path`` and inside it a collection ``to`` and inside it a collection ``some`` and finally inside it a set ``album``.


License
==============

Uploadr.py consists of code by Cameron Mallory, Martin Kleppmann, Aaron Swartz and
others. See ``COPYRIGHT`` for details. Latest modifications (integration with the sets and collections API) by Momchil Tomov.
