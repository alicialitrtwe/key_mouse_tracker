from pynput.keyboard import Key, Listener
import time
from datetime import datetime
import numpy as np
from itertools import chain
import os
import threading
import schedule



class PrivateKeyTracker:
    """
    A key tracker which identifies 'backspace' and 'delete' keys only and groups 
    other keys into 'alphanumeric' or 'special' keys. The tracker outputs the 
    log and summary of tracking sessions in a directory named 'outputs'.
    
    ...

    Attributes
    ----------
    start_datetime : str
        The date and time at which the current session starts
    start_time : float
        The timestamp at which the current session starts
    end_time : float
        The timestamp at which the current session ends
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
    """

    def __init__(self):
        # create output directory
        output_dir = os.path.join(os.getcwd(), r'outputs')
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        self._lock = threading.Lock()

        self._start_session()

        schedule.every().minute.at(':17').do(self.cron_new_session)

        # FIXME: this is blocking right now - change to non-blocking
        while True:
            time.sleep(1)
            schedule.run_pending()
            


    def _start_session(self):
        """
        Start a new session with appropriate attribute values.
        """

        self.start_time = time.time()
        self.start_datetime = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        log_filename = 'log_' + self.start_datetime
        summary_filename = 'summary_' + self.start_datetime
        self._log_file = open('outputs/' + log_filename, 'w+')
        self._summary_file = open('outputs/' + summary_filename, 'w+')

        self._is_last_action_release = True
        self._last_pressed_time: dict[Key, float] = {}
        self._key_press_spans: dict[str, list[float]] = {
            'alphanumeric': [],
            'backspace': [],
            'delete': [],
            'other special': []
        }


    def _end_session(self):
        """
        Finish logging and close the log files.
        """

        self._log_file.close()

        self.end_time = time.time()
        count_alphanumeric = len(self._key_press_spans['alphanumeric'])
        count_backspace = len(self._key_press_spans['backspace'])
        count_delete = len(self._key_press_spans['delete'])
        count_other_special = len(self._key_press_spans['other special'])
        count_total = (
            count_alphanumeric + 
            count_backspace + 
            count_delete + 
            count_other_special)
        if count_total:
            ratio_error_to_total = (
                (count_backspace + count_delete) / count_total)
        else:
            ratio_error_to_total = float('nan')

        # join press spans for all types of keys, then compute average
        mean_key_press_span: float = np.average(
            list(chain.from_iterable(self._key_press_spans.values())))

        # write summary of session
        self._summary_file.write(
            'session started at %s\n' % self.start_datetime)
        self._summary_file.write(
            'session length is %f seconds\n' 
            % (self.end_time - self.start_time))
        self._summary_file.write(
            'alphanumeric keys pressed %d times\n' % count_alphanumeric)
        self._summary_file.write(
            'backspace key pressed %d times\n' % count_backspace)
        self._summary_file.write(
            'delete key pressed %d times\n' % count_delete)
        self._summary_file.write(
            'other special keys pressed %d times\n' % count_other_special)
        self._summary_file.write(
            'total keys pressed %d times\n' % count_total)
        self._summary_file.write(
            'error to total ratio is %f\n' % ratio_error_to_total)
        self._summary_file.write(
            'average key press span is %f seconds\n' % mean_key_press_span)

        self._summary_file.close()


    def _on_press(self, key: Key):
        """
        Gets called when a key is pressed (hidden function).

        Parameters
        ----------
        key : pynput.keyboard.Key
            The key pressed
        """

        self._lock.acquire() # guarantee ongoing press and release actions complete

        try:
            # Only update last_pressed_time[key] if following a release action or if
            # last key pressed is not the current key pressed. In other words, in 
            # the event where the current key was pressed last and not released, do 
            # not update its last pressed time value and instead count it as a 
            # continued key press. 
            if self._is_last_action_release or self.last_pressed_key != key:
                self._last_pressed_time[key] = time.time()
            self.last_pressed_key = key

            try:
                # Do NOT output this value, in order to preserve user privacy
                _x = key.char    
                print('alphanumeric key pressed')
            except AttributeError: # special key, no char value
                if key == Key.backspace:
                    print('backspace key pressed')
                elif key == Key.delete:
                    print('delete key pressed')
                else:
                    print('special key pressed')

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

        self._lock.acquire() # guarantee ongoing press and release actions complete

        try:
            key_press_span = time.time() - self._last_pressed_time[key]

            try:
                # Do NOT output this value, in order to preserve user privacy
                _x = key.char    
                print('alphanumeric key released')
                self._key_press_spans['alphanumeric'].append(key_press_span)
                self._log_file.write('some alphanumeric, %f\n' % key_press_span)
            except AttributeError: # special key, no char value
                if key == Key.backspace:
                    print('backspace key released')
                    self._key_press_spans['backspace'].append(key_press_span)
                    self._log_file.write('backspace, %f\n' % key_press_span)
                elif key == Key.delete:
                    print('delete key released')
                    self._key_press_spans['delete'].append(key_press_span)
                    self._log_file.write('delete, %f\n' % key_press_span)
                else:
                    print('special key released')
                    self._key_press_spans['other special'].append(key_press_span)
                    self._log_file.write('some other special, %f\n' % key_press_span)
            
            self._is_last_action_release = True

            if key == Key.esc:
                self._end_session()

                # stop listener
                return False

        except KeyError:
            # overlapped keys, so we pass
            pass

        finally:
            self._lock.release()
    

    def start(self):
        """
        Starts a session, which can be terminated with 'esc' key.
        """

        self.listener = Listener(
            on_press=self._on_press,
            on_release=self._on_release)
        
        self.listener.start()
        self.listener.join()
    
    
    def cron_new_session(self):
        """
        End current session and start a new one. To be used as a cron job.
        """

        print('entered cron new session')
        self._lock.acquire() # to not collide with a key press or release

        try:
            self._end_session()
            self._start_session()

        finally:
            self._lock.release()



tracker = PrivateKeyTracker()
tracker.start()