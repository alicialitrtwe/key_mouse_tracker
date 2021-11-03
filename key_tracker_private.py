from pynput.keyboard import Key, Listener
import time
from datetime import datetime
import numpy as np
from itertools import chain
import os
import threading

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
    log_file : TextIOWrapper
        The file of designated log output, opened with overwrite permission
    summary_file : TextIOWrapper
        The file of designated summary output, opened with overwrite permission
    lock : threading.Lock
        The lock which prevents press and release actions from interleaving
    is_last_action_release : bool
        Whether the last action is release or not
    last_pressed_key : pynput.keyboard.Key
        The last key pressed
    last_pressed_time : float
        The timestamp at which the last key was pressed at any given time 
during session
    key_press_spans : dict[str, list[float]]
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

        self.start_time = time.time()
        self.start_datetime = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        log_filename = 'log_' + self.start_datetime
        summary_filename = 'summary_' + self.start_datetime
        self.log_file = open('outputs/' + log_filename, 'w+')
        self.summary_file = open('outputs/' + summary_filename, 'w+')
        
        self.lock = threading.Lock()
        self.is_last_action_release = True
        self.last_pressed_time: dict[Key, float] = {}
        self.key_press_spans: dict[str, list[float]] = {
            'alphanumeric': [],
            'backspace': [],
            'delete': [],
            'other special': []
        }

    def __on_press(self, key: Key):
        """
        The callback function when a key is pressed (hidden function)

        Parameters
        ----------
        key : pynput.keyboard.Key
            The key pressed
        """

        self.lock.acquire() # making sure ongoing press and release actions complete

        try:
            # Only update last_pressed_time[key] if following a release action or if
            # last key pressed is not the current key pressed. In other words, in 
            # the event where the current key was pressed last and not released, do 
            # not update its last pressed time value and instead count it as a 
            # continued key press. 
            if self.is_last_action_release or self.last_pressed_key != key:
                self.last_pressed_time[key] = time.time()
            self.last_pressed_key = key

            try:
                # Do NOT output this value, in order to preserve user privacy
                _x = key.char    
                print('alphanumeric key pressed')
            except AttributeError:
                if key == Key.backspace:
                    print('backspace key pressed')
                elif key == Key.delete:
                    print('delete key pressed')
                else:
                    print('special key pressed')

            self.is_last_action_release = False

        finally:
            self.lock.release()

    def __on_release(self, key: Key):
        """
        The callback function when a key is released (hidden function)

        Parameters
        ----------
        key : pynput.keyboard.Key
            The key released
        """

        self.lock.acquire() # making sure ongoing press and release actions complete
        try:
            key_press_span = time.time() - self.last_pressed_time[key]

            try:
                # Do NOT output this value, in order to preserve user privacy
                _x = key.char    
                print('alphanumeric key released')
                self.key_press_spans['alphanumeric'].append(key_press_span)
                self.log_file.write('some alphanumeric, %f\n' % key_press_span)
            except AttributeError:
                if key == Key.backspace:
                    print('backspace key released')
                    self.key_press_spans['backspace'].append(key_press_span)
                    self.log_file.write('backspace, %f\n' % key_press_span)
                elif key == Key.delete:
                    print('delete key released')
                    self.key_press_spans['delete'].append(key_press_span)
                    self.log_file.write('delete, %f\n' % key_press_span)
                else:
                    print('special key released')
                    self.key_press_spans['other special'].append(key_press_span)
                    self.log_file.write('some other special, %f\n' % key_press_span)
            
            self.is_last_action_release = True

            if key == Key.esc:
                # close log file
                self.log_file.close()

                self.end_time = time.time()
                count_alphanumeric = len(self.key_press_spans['alphanumeric'])
                count_backspace = len(self.key_press_spans['backspace'])
                count_delete = len(self.key_press_spans['delete'])
                count_other_special = len(self.key_press_spans['other special'])
                count_total = count_alphanumeric + count_backspace + count_delete + count_other_special
                ratio_error_to_total = (count_backspace + count_delete) / count_total

                # join press spans for all types of keys, then compute average
                mean_key_press_span: float = np.average(list(chain.from_iterable(self.key_press_spans.values())))

                # write summary of session
                self.summary_file.write('session started at %s\n' % self.start_datetime)
                self.summary_file.write('session length is %f seconds\n' % (self.end_time - self.start_time))
                self.summary_file.write('alphanumeric keys pressed %d times\n' % count_alphanumeric)
                self.summary_file.write('backspace key pressed %d times\n' % count_backspace)
                self.summary_file.write('delete key pressed %d times\n' % count_delete)
                self.summary_file.write('other special keys pressed %d times\n' % count_other_special)
                self.summary_file.write('total keys pressed %d times\n' % count_total)
                self.summary_file.write('error to total ratio is %f\n' % ratio_error_to_total)
                self.summary_file.write('average key press span is %f seconds\n' % mean_key_press_span)

                self.summary_file.close()

                # stop listener
                return False
        finally:
            self.lock.release()
    
    def start(self):
        """
        Starts the tracker, which can be terminated with 'esc' key
        """

        self.listener = Listener(
            on_press=self.__on_press,
            on_release=self.__on_release)
        
        self.listener.start()
        self.listener.join()

tracker = PrivateKeyTracker()
tracker.start()