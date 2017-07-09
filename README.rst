MyArchive
---------

MyArchive is a tool for interacting with a multitude of social networks and sites online via established APIs. It downloads and archives posts, images, favorites, etc, allowing you to maintain a central repository of your online activity on your own machine.

Tricks
++++++

* DA collections are handled as just another set of tags! In this case, we make four tags to cover all possible bases.

  * collection_name
  * da.user.(username).(favorites|gallery)
  * da.user.(username).(favorites|gallery).(collection_name)
  * da.author.(author_username)

* The Twitter API does not permit downloading of GIFs/videos. (No path returned in the API call.) We can only pull thumbnails.

Requirements
++++++++++++

* python3-lj
* python3-twitter
* python3-chardet
* python3-feedparser
* python3-deviantart-0.1.4
