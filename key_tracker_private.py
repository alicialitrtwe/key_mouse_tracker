from typing import Callable, Dict
from pynput.keyboard import Key, Listener
import time
from datetime import datetime
import numpy as np
from itertools import chain
import os
import threading



DELAY_HOURS = 6
"""
Number of hours for each session's length.
"""

SECONDS_IN_HOUR = 3600
"""
Number of seconds in an hour.
"""

ERROR_KEY_TYPES = [
    'backspace',
    'delete'
]
"""
Key types associated with making a typo/error.
"""

KEY_TYPE_CONDS: Dict[str, Callable[[Key], bool]] = {
    'alphanumeric': lambda key: hasattr(key, 'char'),
    'backspace': lambda key: key == Key.backspace,
    'delete': lambda key: key == Key.delete,
    'other special': lambda key: (not hasattr(key, 'char') 
                                        and key != Key.backspace 
                                        and key != Key.delete)
}
"""
Key types of interest along with their differentiator function.
"""



class KeyTrackerPrivate:
    """
    A key tracker which identifies 'backspace' and 'delete' keys only and groups 
    other keys into 'alphanumeric' or 'other special' keys. The tracker outputs 
    the log and summary of tracking sessions in a directory named 'outputs'.
    
    ...

    Attributes
    ----------
    start_datetime : str
        The date and time at which the current session starts
    start_time : float
        The timestamp at which the current session starts
    end_time : float
        The timestamp at which the current session ends
    stopped : bool
        Whether the tracker has been stopped
    _log_file : TextIOWrapper
        The file of designated log output, opened with overwrite permission
    _summary_file : TextIOWrapper
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
    _key_press_spans : dict[str, list[float]]
        The key press spans of corresponding types of keys

    Methods
    -------
    start()
        Starts the tracker, which can be terminated with 'esc' key
    cron_new_session()
        End current session and start a new one. To be used as a cron job.
    """


    def __init__(self):
        # create output directory
        output_dir = os.path.join(os.getcwd(), r'outputs')
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        self._lock = threading.Lock()

        self._start_session()
            

    def _start_session(self):
        """
        Start a new session with appropriate attribute values.
        """

        self.start_time = time.time()
        self.start_datetime = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        log_filename = 'outputs/log_' + self.start_datetime
        summary_filename = 'outputs/summary_' + self.start_datetime
        self._log_file = open(log_filename, 'w+')
        self._summary_file = open(summary_filename, 'w+')

        self.stopped = False
        self._is_last_action_release = True
        self._last_pressed_time: dict[Key, float] = {}
        self._key_press_spans: dict[str, list[float]] = {
            key_type: [] for key_type in KEY_TYPE_CONDS
        }


    def _end_session(self):
        """
        Finish logging and close the log files.
        """

        self._log_file.close()
        self.end_time = time.time()

        # start writing session summary
        self._summary_file.write(
            'session started at %s\n' % self.start_datetime)
        self._summary_file.write(
            'session length is %f seconds\n' 
            % (self.end_time - self.start_time))

        # compute press counts of individual, total, and error key types
        count_total = count_error = 0
        for key_type in KEY_TYPE_CONDS:
            key_press_times = len(self._key_press_spans[key_type])

            count_total += key_press_times
            if key_type in ERROR_KEY_TYPES:
                count_error += key_press_times
            
            self._summary_file.write(
                '%s keys pressed %d times\n' % (key_type, key_press_times)) 
        
        if count_total:
            ratio_error_to_total = count_error / count_total
        else:
            # avoid zero division in case no keys pressed in session
            ratio_error_to_total = float('nan')

        # join press spans for all types of keys, then compute average
        mean_key_press_span: float = np.average(
            list(chain.from_iterable(self._key_press_spans.values())))

        self._summary_file.write(
            'total keys pressed %d times\n' % count_total)
        self._summary_file.write(
            'error to total ratio is %f\n' % ratio_error_to_total)
        self._summary_file.write(
            'average key press span is %f seconds\n' % mean_key_press_span)

        self._summary_file.close()

        # TODO
        self._upload_logs()


    def _on_press(self, key: Key):
        """
        Gets called when a key is pressed (hidden function).

        Parameters
        ----------
        key : pynput.keyboard.Key
            The key pressed
        """

        self._lock.acquire() # guarantee ongoing press/release actions complete

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
                    print("%s key pressed" % key_type)
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

        self._lock.acquire() # guarantee ongoing press/release actions complete

        try:
            now = time.time()
            key_press_span = now - self._last_pressed_time[key]

            for key_type, is_key_type in KEY_TYPE_CONDS.items():
                if is_key_type(key):
                    print('%s key released' % key_type)
                    self._key_press_spans[key_type].append(key_press_span)
                    self._log_file.write(
                        '%s, %f, %f\n' % (key_type, key_press_span, now))
            
            self._is_last_action_release = True

            if key == Key.esc:
                self._end_session()

                # stop listener
                self.stopped = True
                return False

        except KeyError:
            # overlapped keys, so we pass
            pass

        finally:
            self._lock.release()
    

    def _upload_logs(self):
        """
        Upload the log files to designated cloud storage.
        Currently not implemented. TODO
        """
        
        pass


    def start(self):
        """
        Starts a session, which can be terminated with 'esc' key.
        """

        print('\n###############')
        print('TRACKING STARTS')
        print('###############\n')

        self.listener = Listener(
            on_press=self._on_press,
            on_release=self._on_release)
        
        self.listener.start()
        self.listener.join()
    
    
    def cron_renew_session(self):
        """
        End current session and start a new one. To be used as a cron job.
        """

        print('\n###################')
        print('NEW SESSION ENTERED')
        print('###################\n')

        self._lock.acquire() # to avoid collision with a key press or release

        try:
            self._end_session()
            self._start_session()

        finally:
            self._lock.release()



tracker = KeyTrackerPrivate() # create a new tracker


def run_main():
    """
    Start the tracker.
    """

    print('starting main thread')
    tracker.start()
    print('ending main thread')


def run_cron():
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


main_thread = threading.Thread(target=run_main, name='t1')
cron_thread = threading.Thread(target=run_cron, name='t2')

main_thread.start()
cron_thread.start()

# wait for both threads to finish
main_thread.join()
cron_thread.join()

print('\n#############')
print('TRACKING ENDS')
print('#############\n')