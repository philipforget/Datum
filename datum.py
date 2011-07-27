#!/usr/bin/python

import errno
import hashlib
import os
import shutil
import sys
import datetime

from PIL import Image
from PIL.ExifTags import TAGS


class Datum():
    def sort_by_exif_date(self, input_dir, output_dir):
        """Given an input directory, organize all pictures inside into date seperated folders

        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.directory_md5_dictionary = {}
        self.no_date_folder = os.path.join(output_dir, 'no date information')

        for dirpath, dirnames, filenames in os.walk(self.input_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                exif_data = self.get_image_exif_or_None(filepath)
                if exif_data is not None and exif_data.get('DateTimeOriginal') is not None:
                    exif_datetime = datetime.datetime.strptime(exif_data['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
                    try:
                        self.write_date_file(original_directory=dirpath, original_filename=filename, datetime_object=exif_datetime)
                    except Exception as date_write_exception:
                        try:
                            self.write_no_date_file(original_directory=dirpath, original_filename=filename, exception=date_write_exception)
                        except Exception as final_excption:
                            sys.stdout.write("FAILED TO WRITE FILE %s - %s"  % (os.path.join(dirpath, filename), final_excption.__str__()))

                else:
                    self.write_no_date_file(original_directory=dirpath, original_filename=filename)
                    continue

    def get_image_exif_or_None(self, filepath):
        """Returns a dictionary of an images EXIF data

        """
        try:
            return_dictionary = {}
            image = Image.open(filepath)
            info = image._getexif()
            for tag, value in info.items():
                return_dictionary[TAGS.get(tag, tag)] = value
            return return_dictionary

        except Exception:
            return None

    def write_date_file(self, original_directory, original_filename, datetime_object ):
        date_path = os.path.join(self.output_dir, datetime_object.strftime('%Y/%m/%d'))
        self._copy_file(original_directory, date_path, original_filename)

    def write_no_date_file(self, original_directory, original_filename, exception=None):
        if exception:
            sys.stdout.write("Copying %s to no-date folder - %s\n" % (os.path.join(original_directory, original_filename), exception.__str__()))
        # Get the path structure relative to the input directory to be able to mirror it
        relative_path_from_input = os.path.join(self.no_date_folder, os.path.relpath(original_directory, self.input_dir))
        # Copy the file to it's proper folder
        self._copy_file(original_directory, relative_path_from_input, original_filename)

    def _copy_file(self, original_directory, target_directory, original_filename, target_filename=None, is_duplicate=False):
        mkdir_p(target_directory)
        # If we dont provide a target filename, use the original filename
        target_filename = original_filename if target_filename is None else target_filename
        original_filepath = os.path.join(original_directory, original_filename)
        target_filepath = os.path.join(target_directory, target_filename)

        # Get or create the array of md5's that have been copied to this directory to sort duplicates
        directory_md5_array = self.directory_md5_dictionary.get(target_directory, [])

        # Suss out any duplicates
        with open(original_filepath, 'rb') as original_file:
            original_md5 = hashlib.md5(original_file.read()).hexdigest()

        # If we know this is a duplicate, put it in the target_directory as is but with a unique filename
        if is_duplicate:
            new_target_filename = target_filename
            # If the file already exists in this directory, enumerate the filename
            if os.path.isfile(os.path.join(target_directory, new_target_filename)):
                file_number = 0
                while os.path.isfile(os.path.join(target_directory, new_target_filename)):
                    new_target_filename = '{filename}-{filenumber}.{ext}'.format(
                        filename = '.'.join(target_filename.split('.')[0:-1]), 
                        filenumber = file_number,
                        ext = target_filename.split('.')[-1]
                    )
                    file_number += 1

            # The new target filepath based on the new target filename
            target_filepath = os.path.join(target_directory, new_target_filename)

        else:
            # If we have a duplicate hash
            if original_md5 in directory_md5_array:
                new_target_directory = os.path.join(target_directory, 'duplicate - %s' % original_md5)
                return self._copy_file(original_directory, new_target_directory, original_filename, is_duplicate=True)

            # If the filename already exists
            if os.path.isfile(target_filepath):
                # Calculate the file that exists in the target file's place
                with open(target_filepath, 'rb') as target_file:
                    target_md5 = hashlib.md5(target_file.read()).hexdigest()

                # If the target and the new target match, copy it to a duplicates directory
                if original_md5 == target_md5:
                    new_target_directory = os.path.join(target_directory, 'duplicate - %s' % original_md5)
                    return self._copy_file(original_directory, new_target_directory, original_filename, is_duplicate=True)


                # If this is just a file name collision, rename this file to be it's md5 and extension
                else:
                    new_target_filename = '{filename}.{ext}'.format(
                        filename = target_md5,
                        ext = original_filename.split('.')[-1]
                    )
                    return self._copy_file(original_directory, original_filepath, original_filename, new_target_filename)

        try:
            shutil.copy(original_filepath, target_filepath)
            directory_md5_array.append(original_md5)
            self.directory_md5_dictionary[target_directory] = directory_md5_array

        except IOError as e:
            sys.stdout.write("Unable to copy %s - %s\n" % (original_filepath, e))
            return




def mkdir_p(path):
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
