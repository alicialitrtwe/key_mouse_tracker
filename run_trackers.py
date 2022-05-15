import threading
from KeyTracker import KeyTrackerPrivate
import CONFIG
import time

SECONDS_IN_HOUR = 3600


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
        if tracker.stopped:
            # exit while loop to exit thread
            break

        if not counter_seconds:
            # start new session and reset counter
            tracker.renew_session()
            counter_seconds = CONFIG.SESSION_LENGTH_IN_HOURS * SECONDS_IN_HOUR

    print('ending cron thread')

if __name__ == '__main__':
    key_tracker = KeyTrackerPrivate()  # create a new tracker

    tracker_thread = threading.Thread(target=(lambda: run_tracker(key_tracker)), name='t1')
    cron_thread = threading.Thread(target=(lambda: run_cron(key_tracker)), name='t2')

    try:
        tracker_thread.start()
        cron_thread.start()

        print('\n###############')
        print('TRACKING STARTS')
        print('###############\n')

        # wait for both threads to finish
        tracker_thread.join()
        cron_thread.join()

    except KeyboardInterrupt:
        key_tracker.stop()

        print('\n#############')
        print('TRACKING ENDS')
        print('#############\n')
