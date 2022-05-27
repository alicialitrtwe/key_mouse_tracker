import logging
import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict
from abc import ABC, abstractmethod

from pynput import keyboard, mouse
from pynput.keyboard import Key

import config
from key_mouse_tracker import KEY_DICT

logger = logging.getLogger(__name__)


class TrackerBase(ABC):
    """
    A base class for key tracker and mouse tracker. Not to be used alone. The tracker outputs
    the log and meta info of tracking sessions in a directory named 'outputs'. The logs are stored
    in sub-folders for different dates
    ...
    Attributes
    ----------
    dev: str
        'mouse' or 'keyboard'
    _start_time : str
        The time at which the current session starts
    _end_time : str
        The time at which the current session ends
    _start_date : str
        The date at which the current session starts
    _start_datetime : str
        The date and time at which the current session starts
    _end_datetime : str
        The date and time at which the current session ends
    stopped : bool
        Whether the tracker has been stopped
    save_dir: str
        current directory or use specified in config.py
    logger_dir : str
        dir to store output logger files
    metadata_dir : str
        dir to store meta files
    _log_file : TextIOWrapper
        The file of designated log output, opened with overwrite permission
    _meta_file : TextIOWrapper
        The file of designated meta info output, opened with overwrite permission
    _lock : threading.Lock
        The lock which prevents press and release actions from interleaving
    listener:
        listener for mouse or keyboard

    Methods
    -------
    start()
        Starts the tracker
    stop()
        Stops the tracker
    renew_session()
        End current session and start a new one. To be used as a cron job.
    """

    def __init__(self, dev=None, listener=None):
        # create output directory
        self.dev = dev
        self.listener = listener
        self.stopped = None
        self._lock = threading.Lock()
        self._meta_file = None
        self._log_file = None
        self.metadata_dir = None
        self.logger_dir = None

        if config.SAVE_DIR is None:
            raise ValueError('The save directory has not been specified in config.py')
        else:
            self.save_dir = config.SAVE_DIR

    def _get_paths(self):
        """
        get the paths for saving outputs and meta info. create directories if they don't already exist
        """
        self.logger_dir = os.path.join(self.save_dir, f'{self.dev}/outputs')
        self.metadata_dir = os.path.join(self.save_dir, f'{self.dev}/metadata')
        if not os.path.exists(os.path.join(self.save_dir, self.dev)):
            os.makedirs(os.path.join(self.save_dir, self.dev), exist_ok=False)
        if not os.path.exists(self.logger_dir):
            os.mkdir(self.logger_dir)
        if not os.path.exists(self.metadata_dir):
            os.mkdir(self.metadata_dir)

    def _start_session(self):
        """
        Start a new session for logging: create new log file, write the column names
        """

        self._start_time = time.time()
        self._start_datetime = datetime.fromtimestamp(self._start_time).strftime('%Y-%m-%d_%H-%M-%S')
        self._start_date = self._start_datetime.split('_')[0]

        if not os.path.exists(os.path.join(self.logger_dir, self._start_date)):
            os.mkdir(os.path.join(self.logger_dir, self._start_date))
        log_file_path = os.path.join(self.logger_dir, self._start_date, f'{self.dev}_logger_{self._start_datetime}.csv')
        self._log_file = open(log_file_path, 'w+')
        self._init_log_file()

    def _end_session(self):
        """
        write meta info and close the log files.
        """

        self._log_file.close()
        self._end_time = time.time()
        self._end_datetime = datetime.fromtimestamp(self._end_time).strftime('%Y-%m-%d_%H-%M-%S')

        # write session summary
        self._meta_file.write(
            f'{self._start_datetime},{self._end_datetime},{self._end_time - self._start_time}\n')

    @abstractmethod
    def _init_log_file(self):
        """
        To be overwritten
        """
        pass

    def start(self):
        """
        Starts tracking: open a meta info file and write down the column names. start the listener.
        """

        self.stopped = False
        self._get_paths()
        self._start_session()
        if not os.path.exists(os.path.join(self.metadata_dir, self._start_date)):
            os.mkdir(os.path.join(self.metadata_dir, self._start_date))
        meta_file_path = os.path.join(self.metadata_dir, self._start_date,
                                      f'{self.dev}_meta_{self._start_datetime}.csv')
        self._meta_file = open(meta_file_path, 'w+')

        def get_git_revision_short_hash() -> str:
            return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                           cwd=os.path.dirname(os.path.abspath(__file__))).decode('ascii').strip()

        self._meta_file.write(f'git_hash\n{get_git_revision_short_hash()}\n')
        self._meta_file.write('session_start,session_end,session_duration\n')
        self.listener.start()
        self.listener.join()

    def stop(self):
        """
        Stops tracking: close the meta info file and stop the listener.
        """
        self._end_session()
        self._meta_file.close()
        self.listener.stop()
        self.stopped = True

    def renew_session(self):
        """
        End current session and start a new one. To be used as a cron job.
        """

        print('\n###################')
        print(f'NEW {self.dev} LOGGER SESSION ENTERED')
        print('###################\n')

        self._lock.acquire()  # to avoid collision with a key press or release

        try:
            self._end_session()
            self._start_session()

        finally:
            self._lock.release()


class KeyTrackerPrivate(TrackerBase):
    """
    A key tracker which identifies 'backspace' and 'delete' keys and groups
    other keys into 'left_alphanum', 'right_alphanum', or 'other special' keys.
    Does not log the name of the 'left_alphanum', 'right_alphanum' keys, only log key categories.
    Note that the timestamp in the log file corresponds to release time.
    Attributes
    ----------
    dev : string
        'mouse'
    listener:
        a listener based on pynput.mouse.Listener
    _is_last_action_release : bool
        Whether the last action is release or not
    _last_pressed_key : pynput.keyboard.Key
        The last key pressed
    _first_pressed_time : float
        The timestamp at which the last key was pressed at any given time
        during session
    """

    def __init__(self):
        _listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release)
        # create output directory
        super(KeyTrackerPrivate, self).__init__(dev='key', listener=_listener)
        self._last_pressed_key = None
        self._first_pressed_time: Dict[Key, float] = {}
        self._is_last_action_release = True

    def _init_log_file(self):
        self._log_file.write('key_type,key_name,timestamp,duration\n')

    def _on_press(self, key: Key):
        """
        Gets called when a key is pressed (hidden function). The key parameter passed to callbacks
        is a pynput.keyboard.Key, for special keys, a pynput.keyboard.KeyCode for normal alphanumeric keys,
        or just None for unknown keys. see pynput documentation.

        Parameters
        ----------
        key : pynput.keyboard.Key
            The key pressed
        """
        self._lock.acquire()  # guarantee ongoing actions complete
        now = time.time()
        try:
            # Only update _first_pressed_time[key] if following a release action
            # or if the last key pressed is not the current key pressed. In other
            # words, in the event where the current key was pressed last and not
            # released, do not update its first pressed time value and instead
            # count it as a continued key press.
            if self._is_last_action_release or self._last_pressed_key != key:
                self._first_pressed_time[key] = now
            self._last_pressed_key = key
            self._is_last_action_release = False
            for key_type, is_key_type in KEY_DICT.KEY_DICT.items():
                if is_key_type(key):
                    try:
                        # print for debugging purpose, not logged
                        logging.debug(f'{key_type} key: {key.char} pressed , time: {now}')
                    except AttributeError:
                        logging.debug(f'{key_type} key: {key} pressed, time: {now}')
        except Exception:
            logging.exception('Exception on press:')

        finally:
            self._lock.release()

    def _on_release(self, key: Key):
        """
        Gets called when a key is released (hidden function).

        Parameters
        ----------
        key : pynput.keyboard.Key
            The key released
        """

        self._lock.acquire()  # guarantee ongoing actions complete
        now = time.time()
        try:
            # problem with some key combinations: i.e. press shift + c and then release shift first. Will record 'C' press
            # and 'c' release. Might cause key error exception if 'c' has not been added to the '_first_pressed_time'
            # dictionary. ignore errors like this since it's rare. the key causing error will not be logged.

            key_press_span = now - self._first_pressed_time[key]
            self._is_last_action_release = True
            # remove key from dictionary once released. only keys currently pressed will stay
            self._first_pressed_time.pop(key)
            for key_type, is_key_type in KEY_DICT.KEY_DICT.items():
                if is_key_type(key):
                    try:
                        logging.debug(f'{key_type} key: {key.char} released, time: {now}, duration: {key_press_span}')
                        self._log_file.write(
                            f'{key_type},NaN,{now},{key_press_span}\n')
                    except AttributeError:
                        logging.debug(f'{key_type} key: {key} released, time: {now}, duration: {key_press_span}')
                        self._log_file.write(
                            f'{key_type},{key},{now},{key_press_span}\n')

        except Exception:
            logging.exception(f'Exception on release:', exc_info=True)

        finally:
            self._lock.release()


class MouseTracker(TrackerBase):
    """
    A mouse tracker that listens for mouse moves, scrolls and clicks.
    ...
    Attributes
    ----------
    dev : string
        'mouse'
    listener:
        a listener based on pynput.mouse.Listener
    """

    def __init__(self):
        _listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll)
        super(MouseTracker, self).__init__(dev='mouse', listener=_listener)
        self.dev = 'mouse'

    def _init_log_file(self):
        self._log_file.write('mouse_type,timestamp,x,y,button,press,dx,dy\n')

    def _on_move(self, x, y):
        now = time.time()
        self._lock.acquire()  # guarantee ongoing actions complete
        try:
            logging.debug(f'move, time: {now}, coordinate: ({x}, {y})')
            self._log_file.write(f'move,{now},{x},{y},NaN,NaN,NaN,NaN\n')
        except Exception:
            logging.exception('Exception on move:')
        finally:
            self._lock.release()

    def _on_click(self, x, y, button, pressed):
        now = time.time()
        self._lock.acquire()  # guarantee ongoing actions complete
        try:
            logging.debug(f'click, time: {now}, coordinate: ({x}, {y}), button: {button}, press: {pressed}')
            self._log_file.write(f'click,{now},{x},{y},{button},{pressed},NaN,NaN\n')
        except Exception:
            logging.exception('Exception on click:')
        finally:
            self._lock.release()

    def _on_scroll(self, x, y, dx, dy):
        now = time.time()
        self._lock.acquire()  # guarantee ongoing actions complete
        try:
            logging.debug(f'scroll, time: {now}, coordinate: ({x}, {y}), direction: ({dx},{dy})')
            self._log_file.write(f'scroll,{now},{x},{y},NaN,NaN,{dx},{dy}\n')
        except Exception:
            logging.exception('Exception on scroll:')
        finally:
            self._lock.release()
