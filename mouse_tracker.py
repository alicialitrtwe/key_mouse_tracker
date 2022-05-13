from pynput import mouse


import os
import threading
import time
from datetime import datetime

from typing import Dict

import CONFIG
import KEY_DICT


class MouseTracker:
    """
    A mouse tracker The tracker outputs
    the log and meta info of tracking sessions in a directory named 'outputs'. The logs are stored
    in sub-folders for different dates
    ...
    Attributes
    ----------
    start_time : str
        The time at which the current session starts
    end_time : str
        The time at which the current session ends
    start_datetime : str
        The date and time at which the current session starts
    end_datetime : str
        The date and time at which the current session ends
    stopped : bool
        Whether the tracker has been stopped
    _log_file : TextIOWrapper
        The file of designated log output, opened with overwrite permission
    _meta_file : TextIOWrapper
        The file of designated meta info output, opened with overwrite permission
    _lock : threading.Lock
        The lock which prevents press and release actions from interleaving
    _is_last_action_release : bool
        Whether the last action is release or not
    _last_pressed_key : pynput.keyboard.Key
        The last key pressed
    _last_pressed_time : float
        The timestamp at which the last key was pressed at any given time
        during session

    Methods
    -------
    start()
        Starts the tracker, which can be terminated by keyboard interrupt
    stop()
        Stops the tracker
    renew_session()
        End current session and start a new one. To be used as a cron job.
    """

    def __init__(self):
        self.stopped = None
        self.listener = None

    def _on_move(self, x, y):
        print('Pointer moved to {0}'.format(
            (x, y)))

    def _on_click(self, x, y, button, pressed):
        print('{0} at {1}'.format(
            'Pressed' if pressed else 'Released',
            (x, y)))

    def _on_scroll(self, x, y, dx, dy):
        print('Scrolled {0} at {1}'.format(
            'down' if dy < 0 else 'up',
            (x, y)))

    def start(self):
        self.listener = mouse.Listener(
             on_move=self._on_move,
             on_click=self._on_click,
             on_scroll=self._on_scroll)
        self.listener.start()
        self.listener.join()

    def stop(self):
        self.listener.stop()
        self.stopped = True

tracker = MouseTracker()
tracker.start()