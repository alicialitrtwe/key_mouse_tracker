Author: Yijia Chen, Alicia Zeng

# privacy-key-tracker

Key and mouse tracker, privacy guaranteed.

# Instructions

First make sure `Python3` is installed on your machine, and so are the following packages:

- `pynput`
- `numpy`

If they are not yet installed, install them using `pip3 install <package-name>`.

Then, in the project directory, run `python3 key_tracker_private.py`, which runs the program in debug mode.

run `python3 -O key_tracker_private.py` to supress debug outputs.

End tracking with keyboard exception in the terminal any time.

# Setup

- Specify a save directory in CONFIG.py. Otherwise, results will be stored in '{device}/outputs' and '{device}/metadata' folders in the project directory.
- Please modify the LEFT_ALPHANUM and RIGHT_ALPHANUM dictionaries in KEY_DICT.py to align with your typing preferences. Also add dictionaries in KEY_DICT.py 
  to track additional typing patterns.
- Debug: on first use, run `python3 key_tracker_private.py`, press every key on the keyboard and mouse and check the terminal output to make sure the trackers 
  are performing as expected. Make sure the logging sessions renew correctly. Then run `python3 -O key_tracker_private.py`.