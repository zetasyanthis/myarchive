MyArchive
---------

MyArchive is a tool for interacting with a multitude of social networks and sites online via established APIs. It downloads and archives posts, images, favorites, etc, allowing you to maintain a central repository of your online activity on your own machine.

Supported Data Import Sources
+++++++++++++++++++++++++++++

 * Shotwell databases/files
 * Raw folders and files on your filesystem
 * Deviantart
 * Twitter
 * Planned, or in work.

   * Dreamwidth
   * Flickr
   * Github Gist (and probably repo mirroring)
   * Goodreads
   * Instagram
   * LibraryThing
   * LiveJournal
   * Mastodon
   * Medium
   * Reddit
   * SoFurry
   * Tumblr
   * Weasyl
   * Youtube playlists
   * Generic RSS feeds


Deviantart
==========

* DA collections are handled as just another set of tags! In this case, we make four tags to cover all possible bases.

  * collection_name
  * da.user.(username).(favorite|gallery)
  * da.user.(username).(favorite|gallery).(collection_name)
  * da.author.(author_username)

Twitter
=======

* The Twitter API does not permit downloading of GIFs/videos. (No path returned in the API call.) We can only pull thumbnails.

* Tweets (and their files) are tagged in the following manner.

  * twitter.(username).tweet
  * twitter.(username).favorite [If the tweet is favorited by the user data is being imported for.]
  * Any hashtags on the tweet.

Requirements
++++++++++++

 * Python packages from pip3.

  * lj
  * twitter
  * chardet
  * feedparser
  * deviantart-0.1.4
  * youtube-dl
