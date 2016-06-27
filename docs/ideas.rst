.. coding=utf-8

Design Goals
============

 * Python and Gtk3-based reimplementation of Shotwell with more features.
 * Separate databases and folders for storage of files.
 * File groups for multi-image sets / scans.

Implementation Details
======================

* Left hand column
  * Right-clicking should bring up a menu to select between views:
     * Views
       * Just tags (Default)
       * Tags by library - drag and drop enabled
     * Filters
       * Display only one library
       * Display only one tag
  * Right-clicking a specific tag in the column should also bring up new, rename, delete.
    * Renaming to an existing name should ask about a merge.

* Status bar
  * Image details (Title, size, file group)

* Edit/Preferences menu to select currently displayed DBs.
* Shotwell DB import function
