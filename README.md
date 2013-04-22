Datum
=====

Utility for organizing an input directory into an output directory of images
organized by year, month and day subdirectories based on EXIF data. Duplicates
are also detected in this process based on a qualitative hash of the image
data.

Usage
-----
`datum /path/to/input /path/to/output | tee errors.txt`

Installation
------------

To install to a local virtualenv, simply `pip install datum`. To install
globally, `sudo pip install datum`. 

Datum only has one dependency, PIL, which is used for extracting EXIF data.
This will likely change in favor of something more lightweight.
