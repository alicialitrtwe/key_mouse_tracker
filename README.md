2020/06/29 new feature: upload to a remote location using rclone. Dependent on existing rclone setup. 
Please specify the remote save location in config.py, along with the local save directory. When tracking stops, 
the program will first save all files for the tracking period in the local directory, and then upload them to the remote save location.
Use keyboard interruption `ctrl + c` once to stop tracking and start uploading. Please wait until 'upload complete' to exit terminal.


# key_mouse_tracker

Keyboard and mouse trackers that log keyboard/mouse type and time information for the purpose of data analysis.

The trackers log `key_type, key_name, timestamp, duration` for the keyboard and `mouse_type, timestamp, x, y, button, press, dx, dy` for the mouse.
Privacy guaranteed since all the alphanumeric keys are masked as `NaN`. 

The logs and metadata about the sessions are saved in csv files in a user-specified directory. Logging sessions will be renewed every hour by default.

# Instructions

First make sure `Python3` is installed. Then install `key_mouse_tracker` in editable mode:
```
git clone https://github.com/alicialitrtwe/key_mouse_tracker
cd key_mouse_tracker
pip install --editable .
```

After installation, run `track` in the terminal in any directory to start tracking. 
End tracking with keyboard exception in the terminal any time. Without installation, `python3 run_trackers.py` in the 
`key_mouse_tracker` directory will start tracking.

Use `track --log debug` or `python3 run_trackers.py --log debug` for debug mode. Will output in the terminal the key press/release time and
duration, mouse move/scroll/click time, coordinate and button info.

`track --dev mouse` or `track --dev key` if only wants to track one of the devices.
Default to `both`.

# Initial Setup

- First, specify local and remote save directories for the output logs in config.py.


- Please modify the LEFT_ALPHANUM and RIGHT_ALPHANUM dictionaries in KEY_DICT.py to align with your typing preferences.
  You can also add dictionaries in KEY_DICT.py if you are interested in tracking additional typing patterns.


- Debug: on first use, run `track --log debug`, press every key on the keyboard and mouse and
  check the terminal debug output to make sure the trackers are performing as expected.
    - Make sure all the common keys are correctly recorded.
    - Make sure the logging sessions renew correctly. In the debug mode, the log file will be renewed every 30 seconds.
      In the default mode, the log file will be renewed every hour. If you want to change the session length, you can edit 
      `SESSION_LENGTH_IN_HOURS` in `key_mouse_tracker/run_trackers.py`.
  

- Privacy: in the log output .csv files, you will find all the alphanumeric keys are masked as `NaN`.


- Known problem with some key combinations: i.e. pressing shift + c and releasing shift first, and then c. pynput will pick 
  up 'C' press and 'c' release. This might cause key error exception if 'c' has not been added to the 'KeyTrackerPrivate._first_pressed_time' 
  dictionary. We ignore errors like this since it's rare. The keys causing error will not be logged.
