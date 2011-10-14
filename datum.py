#!/usr/bin/python

import datetime
import errno
import hashlib
import os
import shutil
import sys
sys.setrecursionlimit(2000)

from PIL import Image
from PIL.ExifTags import TAGS


class Datum():
    DUPLICATES_PREFIX = "datum_duplicates"

    def __init__(self):
        # Dictionary to hold all of the md5's we encounter
        self.directory_md5_dictionary = {}
        # md5 cache of all the files we calculate, since it may need to happen often
        self.md5_cache = {}

    def sort_by_exif_date(self, input_dir, output_dir):
        """Given an input directory, organize all pictures inside into date seperated folders

        """
        self.input_dir = input_dir
        self.output_dir = output_dir

        # The directory to place files without exif data
        self.no_date_folder = os.path.join(output_dir, 'no date information')

        for dirpath, dirnames, filenames in os.walk(self.input_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.islink(filepath):
                    sys.stdout.write("Skipping symlink %s\n" % filepath)
                    continue
                exif_data = self.get_image_exif_or_None(filepath)

                if exif_data is not None and exif_data.get('DateTimeOriginal') is not None:
                    exif_datetime = datetime.datetime.strptime(exif_data['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
                    self.write_date_file(original_directory=dirpath, original_filename=filename, datetime_object=exif_datetime)

                elif exif_data is not None and exif_data.get('DateTime') is not None:
                    exif_datetime = datetime.datetime.strptime(exif_data['DateTime'], '%Y:%m:%d %H:%M:%S')
                    self.write_date_file(original_directory=dirpath, original_filename=filename, datetime_object=exif_datetime)

                else:
                    self.write_no_date_file(original_directory=dirpath, original_filename=filename)

    def get_image_exif_or_None(self, filepath):
        """Returns a dictionary of an images EXIF data if it exists or None

        """
        try:
            exif_dictionary = {}
            image = Image.open(filepath)
            info = image._getexif()
            for tag, value in info.items():
                exif_dictionary[TAGS.get(tag, tag)] = value
            return exif_dictionary

        except Exception as exif_exception:
            return None

    def write_date_file(self, original_directory, original_filename, datetime_object, path_format='%Y/%m/%d'):
        """Copy an image to a folder based on it's exif date data.

        The folder structure can be defined by passing in the path_format
        argument.
        """
        date_path = os.path.join(self.output_dir, datetime_object.strftime(path_format))
        self._copy_file(original_directory, date_path, original_filename)

    def write_no_date_file(self, original_directory, original_filename, exception=None):
        if exception:
            sys.stdout.write("Copying %s to no-date folder - %s\n" % (os.path.join(original_directory, original_filename), exception.__str__()))

        # Get the path structure relative to the input directory to be able to mirror it
        relative_path_from_input = os.path.join(self.no_date_folder, os.path.relpath(original_directory, self.input_dir))

        try:
            self._copy_file(original_directory, relative_path_from_input, original_filename)
        except Exception as write_exception:
            sys.stdout.write("Unable to write no_date_file %s, exception was %s\n"  % (os.path.join(original_directory, original_filename), write_exception.__str__()))

    def get_file_md5(self, filepath):
        """Get a files md5 based on filepath and cache it

        """
        file_md5 = self.md5_cache.get(hash(filepath))
        if not file_md5:
            with open(filepath, 'rb') as file_to_md5:
                file_md5 = hashlib.md5(file_to_md5.read()).hexdigest()
                self.md5_cache[hash(filepath)] = file_md5

        return file_md5


    def _copy_file(self, original_directory, target_directory, original_filename, target_filename=None):
        """Copy a file from a directory into a target directory being aware of duplicates

        If the file already exists in the target directory, create a duplicates
        directory named after the files md5 to house the duplicate and any
        subsequent duplicates of the file.
        """

        # If we dont provide a target filename, use the original filename
        target_filename = original_filename if target_filename is None else target_filename

        original_filepath = os.path.join(original_directory, original_filename)
        target_filepath = os.path.join(target_directory, target_filename)

        # Get or create the array of md5's that have been copied to this directory to sort duplicates
        directory_md5_array = self.directory_md5_dictionary.get(target_directory, [])

        original_md5 = self.get_file_md5(original_filepath)

        # If we have a duplicate in a non-datum duplicates folder, copy this
        # file to a datum duplicates folder instead
        if (original_md5 in directory_md5_array and not Datum.is_duplicates_directory(target_directory)) or\
           os.path.isfile(target_filepath):
            new_target_directory = os.path.join(target_directory, Datum.get_duplicate_directory_name(original_md5))
            new_target_filename = Datum.get_enumerated_filename(new_target_directory, Datum.get_md5_filename(original_md5, target_filename))
            return self._copy_file(original_directory, new_target_directory, original_filename, new_target_filename)

        # All sorts of shit can go wrong when it comes time for disk IO, so be safe out there!
        try:
            # Be lazy about actually creating the output directory until we are
            # ready to copy the file
            mkdir_p(target_directory)
            shutil.copy(original_filepath, target_filepath)
        except IOError as e:
            sys.stdout.write("Unable to copy \n%s to\n %s - %s\n" % (original_filepath, target_filepath, e))
            return

        directory_md5_array.append(original_md5)
        self.directory_md5_dictionary[target_directory] = directory_md5_array

    @classmethod
    def get_md5_filename(cls, md5sum, target_filename):
        """Return an md5 formatted filename

        """
        file_root, file_ext = os.path.splitext(target_filename)
        return '{md5sum}{file_ext}'.format(
            md5sum = md5sum,
            file_ext = file_ext
        )

    @classmethod
    def get_enumerated_filename(cls, target_directory, target_filename):
        """Return an enumerated filename for a given directory and target filename

        """
        file_root, file_ext = os.path.splitext(target_filename)
        new_target_filename = target_filename
        # If the file already exists in this directory, enumerate the filename
        if os.path.isfile(os.path.join(target_directory, new_target_filename)):
            file_number = 0
            while os.path.isfile(os.path.join(target_directory, new_target_filename)):
                new_target_filename = '{file_root}-{file_number}{file_ext}'.format(
                    # The filename minus the extension if it's not a dotfile and it has one
                    file_root = file_root,
                    file_number = file_number,
                    file_ext = file_ext
                )
                file_number += 1

        return new_target_filename

    @classmethod
    def get_duplicate_directory_name(cls, md5sum):
        """Returns a properly formated name for the new directory based on md5 sum

        """
        return "%s %s" % (cls.DUPLICATES_PREFIX, md5sum)

    @classmethod
    def is_duplicates_directory(cls, directory_path):
        """ Returns True if the directory path is a datum duplicates folder

        """
        return directory_path.find(cls.DUPLICATES_PREFIX) >= 0



def mkdir_p(path):
    """mkdir -p functionality

    """
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise

def exit_with_error(message):
    sys.stderr.write(message)
    sys.stderr.write('\n')
    sys.exit(1)

if __name__ == '__main__':
    try:
        input_dir = os.path.abspath(os.path.expanduser(sys.argv[1]))
        output_dir = os.path.abspath(os.path.expanduser(sys.argv[2]))
    except IndexError:
        exit_with_error("No directory provided")
    if not os.path.isdir(input_dir) or not os.path.isdir(output_dir):
        exit_with_error("No directory provided")

    Datum().sort_by_exif_date(input_dir, output_dir)
