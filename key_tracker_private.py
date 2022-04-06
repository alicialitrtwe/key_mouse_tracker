import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Callable, Dict
from pynput.keyboard import Key, Listener

# Number of hours for each session's length.
DELAY_HOURS = 1 / 120

SECONDS_IN_HOUR = 3600

LEFT_ALPHANUM = ['`', '1', '2', '3', '4', '5', '6', '~', '!', '@', '#', '$', '%', '^',
                 'q', 'w', 'e', 'r', 't', 'Q', 'W', 'E', 'R', 'T',
                 'a', 's', 'd', 'f', 'g', 'A', 'S', 'D', 'F', 'G',
                 'z', 'x', 'c', 'v', 'b', 'Z', 'X', 'C', 'V', 'B']

RIGHT_ALPHANUM = ['7', '8', '9', '0', '-', '=', '_', '+',
                  'y', 'u', 'i', 'o', 'p', 'Y', 'U', 'I', 'O', 'P', '[', ']', '{', '}', '|', '\\',
                  'h', 'j', 'k', 'l', 'H', 'J', 'K', 'L', ';', ':', "'", '"',
                  'n', 'm', 'N', 'M', ',', '.', '/', '<', '>', '?']

# Key types of interest along with their differentiator function.
KEY_TYPE_CONDS: Dict[str, Callable[[Key], bool]] = {
    'left_alphanum': lambda key: (hasattr(key, 'char')
                                  and key.char in LEFT_ALPHANUM),
    'right_alphanum': lambda key: (hasattr(key, 'char')
                                   and key.char in RIGHT_ALPHANUM),
    'backspace': lambda key: key == Key.backspace,
    'delete': lambda key: key == Key.delete,
    'special': lambda key: (not hasattr(key, 'char')
                            and key != Key.backspace
                            and key != Key.delete)
}


class KeyTrackerPrivate:
    """
    A key tracker which identifies 'backspace' and 'delete' keys only and groups 
    other keys into 'alphanumeric' or 'other special' keys. The tracker outputs 
    the log and summary of tracking sessions in a directory named 'outputs'.
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
        The file of designated summary output, opened with overwrite permission
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
        self.output_dir = os.path.join(os.getcwd(), 'outputs')
        self.metadata_dir = os.path.join(self.output_dir, 'metadata')
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
        if not os.path.exists(self.metadata_dir):
            os.mkdir(self.metadata_dir)
        self._lock = threading.Lock()

    def _start_session(self):
        """
        Start a new session with appropriate attribute values.
        """
        self.stopped = False
        self.start_time = time.time()
        self.start_datetime = datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d_%H-%M-%S')
        self.start_date = self.start_datetime.split('_')[0]

        if not os.path.exists(os.path.join(self.output_dir, self.start_date)):
            os.mkdir(os.path.join(self.output_dir, self.start_date))
        log_file_path = os.path.join(self.output_dir, self.start_date, f'key_{self.start_datetime}.csv')
        self._log_file = open(log_file_path, 'w+')
        self._is_last_action_release = True
        self._last_pressed_time: dict[Key, float] = {}

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
            f'session_start, {self.start_datetime}, '
            f'session_end, {self.end_datetime}, '
            f'session_duration, {self.end_time - self.start_time}\n')

        self._upload_logs()
        # stop listener
        self.stopped = True

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
            # or if last key pressed is not the current key pressed. In other
            # words, in the event where the current key was pressed last and not
            # released, do not update its last pressed time value and instead
            # count it as a continued key press.
            if self._is_last_action_release or self.last_pressed_key != key:
                self._last_pressed_time[key] = time.time()
            self.last_pressed_key = key

            for key_type, is_key_type in KEY_TYPE_CONDS.items():
                if is_key_type(key):
                    try:
                        print(f'{key_type} key: {key.char} released')
                    except AttributeError:
                        print(f'{key_type} key: {key} pressed')
                    break

            self._is_last_action_release = False

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

            for key_type, is_key_type in KEY_TYPE_CONDS.items():
                if is_key_type(key):
                    try:
                        print(f'{key_type} key: {key.char} released')
                        self._log_file.write(
                            f'{key_type} {key.char} {now} {key_press_span}\n')
                    except AttributeError:
                        print(f'{key_type} key: {key} released')
                        self._log_file.write(
                            f'{key_type} {key} {now} {key_press_span}\n')

            self._is_last_action_release = True

        except Exception as e:
            if e is KeyError:
                # overlapped keys, so we pass
                pass
            elif e is IOError:
                pass

        finally:
            self._lock.release()

    def _upload_logs(self):
        """
        Upload the log files to designated cloud storage.
        """
        # subprocess.run(f'rclone copy {source} {target}')

        pass

    def start(self):
        """
        Starts a session, which can be terminated by keyboard interrupt.
        """

        # time.sleep(1)
        print('\n###############')
        print('TRACKING STARTS')
        print('###############\n')
        self._start_session()
        meta_file_path = os.path.join(self.output_dir, 'metadata', f'key_meta_{self.start_datetime}.csv')
        self._meta_file = open(meta_file_path, 'w+')
        self.listener = Listener(
            on_press=self._on_press,
            on_release=self._on_release)
        self.listener.start()
        self.listener.join()

    def stop(self):
        self._end_session()
        self._meta_file.close()
        self.listener.stop()

    def cron_renew_session(self):
        """
        End current session and start a new one. To be used as a cron job.
        """

        print('\n###################')
        print('NEW SESSION ENTERED')
        print('###################\n')

        self._lock.acquire()  # to avoid collision with a key press or release

        try:
            self._end_session()
            self._start_session()

        finally:
            self._lock.release()


def run_main(tracker: KeyTrackerPrivate):
    """
    Start the tracker.
    """

    print('starting main thread')
    tracker.start()
    print('ending main thread')


def run_cron(tracker: KeyTrackerPrivate):
    """
    Start timer for renewing sessions.
    """

    print('starting cron thread')

    # Using second as unit for counter here because we want to check frequently
    # whether the main thread for tracking has exited.
    counter_seconds = DELAY_HOURS * SECONDS_IN_HOUR
    while counter_seconds:
        time.sleep(1)
        counter_seconds -= 1

        if tracker.stopped:
            # exit while loop to exit thread
            break

        if not counter_seconds:
            # start new session and reset counter
            tracker.cron_renew_session()
            counter_seconds = DELAY_HOURS * SECONDS_IN_HOUR

    print('ending cron thread')


tracker = KeyTrackerPrivate()  # create a new tracker

main_thread = threading.Thread(target=(lambda: run_main(tracker)), name='t1')
cron_thread = threading.Thread(target=(lambda: run_cron(tracker)), name='t2')

try:
    main_thread.start()
    cron_thread.start()

    # wait for both threads to finish
    main_thread.join()
    cron_thread.join()

except KeyboardInterrupt:
    tracker.stop()

    print('\n#############')
    print('TRACKING ENDS')
    print('#############\n')
