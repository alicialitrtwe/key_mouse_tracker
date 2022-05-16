import threading
import time

import CONFIG
from Trackers import KeyTrackerPrivate, TrackerBase, MouseTracker

SECONDS_IN_HOUR = 3600


def run_tracker(tracker: TrackerBase):
    tracker.start()


def run_cron(tracker: TrackerBase):
    """
    Start cron job for renewing sessions.
    """
    print('starting cron job')
    # Using second as unit for counter here because we want to check frequently
    # whether the main thread for tracking has exited.
    counter_seconds = CONFIG.SESSION_LENGTH_IN_HOURS * SECONDS_IN_HOUR
    while counter_seconds:
        time.sleep(1)
        counter_seconds -= 1
        if tracker.stopped:
            # exit while loop to exit thread
            print('ending cron job')
            break

        if not counter_seconds:
            # start new session and reset counter
            tracker.renew_session()
            counter_seconds = CONFIG.SESSION_LENGTH_IN_HOURS * SECONDS_IN_HOUR


if __name__ == '__main__':
    key_tracker = KeyTrackerPrivate()  # create a new tracker
    mouse_tracker = MouseTracker()

    key_tracker_thread = threading.Thread(target=(lambda: run_tracker(key_tracker)), name='key_tracker')
    key_cron_thread = threading.Thread(target=(lambda: run_cron(key_tracker)), name='key_cron')
    mouse_tracker_thread = threading.Thread(target=(lambda: run_tracker(mouse_tracker)), name='mouse_tracker')
    mouse_cron_thread = threading.Thread(target=(lambda: run_cron(mouse_tracker)), name='mouse_cron')
    try:
        key_tracker_thread.start()
        key_cron_thread.start()
        mouse_tracker_thread.start()
        mouse_cron_thread.start()

        print('\n###############')
        print('TRACKING STARTS')
        print('###############\n')

        # wait for both threads to finish
        key_tracker_thread.join()
        key_cron_thread.join()
        mouse_tracker_thread.join()
        mouse_cron_thread.join()

    except KeyboardInterrupt:
        key_tracker.stop()
        mouse_tracker.stop()

        print('\n#############')
        print('TRACKING ENDS')
        print('#############\n')
