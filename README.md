Author: Yijia Chen, Alicia Zeng

# privacy-key-tracker

Key and mouse tracker, privacy guaranteed.

# Instructions

First make sure `Python3` is installed on your machine, and so is the following package:

- `pynput`

The packages can be installed using `pip3 install <package-name>`.

Then, in the `key_mouse_tracker` directory, run `python3 run_trackers.py` to start tracking.

End tracking with keyboard exception in the terminal any time.

`python3 run_trackers.py --log debug` for debug mode. Will output in the terminal the key press/release time and
duration, mouse move/scroll/click time and coordinate and button info.

`python3 run_trackers.py --dev mouse` or `python3 run_trackers.py --dev key` if only wants to track one of the devices.
Default is 'both'.

# Setup

- First, specify a save directory in config.py. Otherwise, results will be stored in '{device}/outputs' and '
  {device}/metadata' folders in the project directory.

- Please modify the LEFT_ALPHANUM and RIGHT_ALPHANUM dictionaries in KEY_DICT.py to align with your typing preferences.
  You can also add dictionaries in KEY_DICT.py if you are interested in tracking additional typing patterns.

- Debug: on first use, run `python3 key_tracker_private.py --log debug`, press every key on the keyboard and mouse and
  check the terminal debug output to make sure the trackers are performing as expected.
    - Make sure all the common keys are corrected recorded.
    - Make sure the logging sessions renew correctly. In the debug mode, the log file will be renewed every 30 seconds.
      In the default mode, the log file will be renewed every hour. Change the session length by changing '
      SESSION_LENGTH_IN_HOURS'
  
- Privacy: in the log output .csv files, you will find all the alphanumeric keys are masked as `NaN`.

- Known problem with some key combinations: i.e. press shift + c and release shift first, and then c. pynput will pick 
  up 'C' press and 'c' release. Might cause key error exception if 'c' has not been added to the '_first_pressed_time' 
  dictionary. We ignore errors like this since it's rare. The key causing error will not be logged.
