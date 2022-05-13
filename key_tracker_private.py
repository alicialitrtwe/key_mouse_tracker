import os
import threading
import time
from datetime import datetime

from pynput.keyboard import Key, Listener
from typing import Dict

import CONFIG
import KEY_DICT

SECONDS_IN_HOUR = 3600


class KeyTrackerPrivate:
    """
    A key tracker which identifies 'backspace' and 'delete' keys and groups
    other keys into 'left_alphanum', 'right_alphanum', or 'other special' keys. The tracker outputs
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
    cron_new_session()
        End current session and start a new one. To be used as a cron job.
    """

    def __init__(self):
        # create output directory
        self.listener = None
        self._meta_file = None
        if CONFIG.SAVE_DIR is not None:
            save_dir = CONFIG.SAVE_DIR
        else:
            save_dir =os.getcwd()
        self.output_dir = os.path.join(save_dir, 'outputs')
        self.metadata_dir = os.path.join(save_dir, 'metadata')
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
        if not os.path.exists(self.metadata_dir):
            os.mkdir(self.metadata_dir)
        self._lock = threading.Lock()

    def _start_session(self):
        """
        Start a new session with appropriate attribute values.
        """
        self.start_time = time.time()
        self.start_datetime = datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d_%H-%M-%S')
        self.start_date = self.start_datetime.split('_')[0]

        if not os.path.exists(os.path.join(self.output_dir, self.start_date)):
            os.mkdir(os.path.join(self.output_dir, self.start_date))
        log_file_path = os.path.join(self.output_dir, self.start_date, f'key_logger_{self.start_datetime}.csv')
        self._log_file = open(log_file_path, 'w+')
        self._log_file.write('key_type, key_name, press_time, press_duration\n')
        self._is_last_action_release = True
        self._last_pressed_time: Dict[Key, float] = {}

    def _end_session(self):
        """
        Finish logging and close the log files.
        """

        self._log_file.close()
        self.end_time = time.time()
        self.end_datetime = datetime.fromtimestamp(self.end_time).strftime('%Y-%m-%d_%H-%M-%S')
        self.end_date = self.end_datetime.split('_')[0]

        # start writing session summary
        self._meta_file.write(
            f'{self.start_datetime}, {self.end_datetime}, {self.end_time - self.start_time}\n')

        self._upload_logs()

    def _on_press(self, key: Key):
        """
        Gets called when a key is pressed (hidden function).

        Parameters
        ----------
        key : pynput.keyboard.Key
            The key pressed
        """

        self._lock.acquire()  # guarantee ongoing press/release actions complete

        if self.stopped:
            return False
        try:
            # Only update last_pressed_time[key] if following a release action
            # or if the last key pressed is not the current key pressed. In other
            # words, in the event where the current key was pressed last and not
            # released, do not update its last pressed time value and instead
            # count it as a continued key press.
            if self._is_last_action_release or self._last_pressed_key != key:
                self._last_pressed_time[key] = time.time()
            self._last_pressed_key = key

            for key_type, is_key_type in KEY_DICT.KEY_DICT.items():
                if is_key_type(key):
                    try:
                        # print for debugging purpose, not logged
                        print(f'{key_type} key: {key.char} pressed')
                    except AttributeError:
                        print(f'{key_type} key: {key} pressed')
                    break

            self._is_last_action_release = False
        except Exception as e:
            print('Exception on press:', e)

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

        self._lock.acquire()  # guarantee ongoing press/release actions complete

        try:
            now = time.time()
            key_press_span = now - self._last_pressed_time[key]

            for key_type, is_key_type in KEY_DICT.KEY_DICT.items():
                if is_key_type(key):
                    try:
                        print(f'{key_type} key: {key.char} released')
                        self._log_file.write(
                            f'{key_type}, {key.char}, {now}, {key_press_span}\n')
                    except AttributeError:
                        print(f'{key_type} key: {key} released')
                        self._log_file.write(
                            f'{key_type}, {key}, {now}, {key_press_span}\n')

            self._is_last_action_release = True

        except Exception as e:
            print('Exception on release:', e)

        finally:
            self._lock.release()

    def _upload_logs(self):
        """
        Upload the log files to designated cloud storage.
        """
        # subprocess.run(f'rclone copy {source} {target}')

        return NotImplementedError

    def start(self):
        """
        Starts a session, which can be terminated by keyboard interrupt.
        """

        # time.sleep(1)
        print('\n###############')
        print('KEY TRACKING STARTS')
        print('###############\n')
        self.stopped = False
        self._start_session()
        meta_file_path = os.path.join(self.metadata_dir, f'key_meta_{self.start_datetime}.csv')
        self._meta_file = open(meta_file_path, 'w+')
        self._meta_file.write('session_start, session_end, session_duration\n')
        self.listener = Listener(
            on_press=self._on_press,
            on_release=self._on_release)
        self.listener.start()
        self.listener.join()

    def stop(self):
        self._end_session()
        self._meta_file.close()
        self.listener.stop()
        self.stopped = True

    def renew_session(self):
        """
        End current session and start a new one. To be used as a cron job.
        """

        print('\n###################')
        print('NEW KEY LOGGER SESSION ENTERED')
        print('###################\n')

        self._lock.acquire()  # to avoid collision with a key press or release

        try:
            self._end_session()
            self._start_session()

        finally:
            self._lock.release()


def run_tracker(tracker: KeyTrackerPrivate):
    """
    Start the tracker.
    """

    print('starting tracker thread')
    tracker.start()
    print('ending tracker thread')


def run_cron(tracker: KeyTrackerPrivate):
    """
    Start timer for renewing sessions.
    """

    print('starting cron thread')

    # Using second as unit for counter here because we want to check frequently
    # whether the main thread for tracking has exited.
    counter_seconds = CONFIG.SESSION_LENGTH_IN_HOURS * SECONDS_IN_HOUR
    while counter_seconds:
        time.sleep(1)
        counter_seconds -= 1
        print('stopped', tracker.stopped)
        if tracker.stopped:
            # exit while loop to exit thread
            break

        if not counter_seconds:
            # start new session and reset counter
            tracker.renew_session()
            counter_seconds = CONFIG.SESSION_LENGTH_IN_HOURS * SECONDS_IN_HOUR

    print('ending cron thread')

if __name__ == '__main__':
    tracker = KeyTrackerPrivate()  # create a new tracker

    tracker_thread = threading.Thread(target=(lambda: run_tracker(tracker)), name='t1')
    cron_thread = threading.Thread(target=(lambda: run_cron(tracker)), name='t2')

    try:
        tracker_thread.start()
        cron_thread.start()

        # wait for both threads to finish
        tracker_thread.join()
        cron_thread.join()

    except KeyboardInterrupt:
        tracker.stop()

        print('\n#############')
        print('KEY TRACKING ENDS')
        print('#############\n')
