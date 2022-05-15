import os
import threading
import time
from datetime import datetime
from pynput import keyboard
from pynput.keyboard import Key
from typing import Dict
import CONFIG
import KEY_DICT


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
        self.dev = 'key'
        self.listener = None
        self._meta_file = None
        self._lock = threading.Lock()

        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release)

        if CONFIG.SAVE_DIR is not None:
            save_dir = CONFIG.SAVE_DIR
        else:
            save_dir = os.getcwd()
        self.output_dir = os.path.join(save_dir, f'{self.dev}/outputs')
        self.metadata_dir = os.path.join(save_dir, f'{self.dev}/metadata')
        if not os.path.exists(save_dir):
            os.mkdir(save_dir)
        if not os.path.exists(os.path.join(save_dir, self.dev)):
            os.mkdir(os.path.join(save_dir, self.dev))
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
        if not os.path.exists(self.metadata_dir):
            os.mkdir(self.metadata_dir)


    def _start_session(self):
        """
        Start a new session with appropriate attribute values.
        """
        self.start_time = time.time()
        self.start_datetime = datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d_%H-%M-%S')
        self.start_date = self.start_datetime.split('_')[0]

        if not os.path.exists(os.path.join(self.output_dir, self.start_date)):
            os.mkdir(os.path.join(self.output_dir, self.start_date))
        log_file_path = os.path.join(self.output_dir, self.start_date, f'{self.dev}_logger_{self.start_datetime}.csv')
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

    def _on_press(self, key: Key):
        """
        Gets called when a key is pressed (hidden function).

        Parameters
        ----------
        key : pynput.keyboard.Key
            The key pressed
        """

        self._lock.acquire()  # guarantee ongoing press/release actions complete

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

        raise NotImplementedError

    def start(self):
        """
        Starts a session, which can be terminated by keyboard interrupt.
        """

        # time.sleep(1)
        self.stopped = False
        self._start_session()
        if not os.path.exists(os.path.join(self.metadata_dir, self.start_date)):
            os.mkdir(os.path.join(self.metadata_dir, self.start_date))
        meta_file_path = os.path.join(self.metadata_dir, self.start_date, f'{self.dev}_meta_{self.start_datetime}.csv')
        self._meta_file = open(meta_file_path, 'w+')
        self._meta_file.write('session_start, session_end, session_duration\n')
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