import argparse
import logging
import sys
import threading
import time

from .Trackers import KeyTrackerPrivate, TrackerBase, MouseTracker

SECONDS_IN_HOUR = 3600


def run_tracker(tracker: TrackerBase):
    tracker.start()


def run_renew_session(tracker: TrackerBase, session_length_in_hours):
    """
    Start cron job for renewing sessions.
    """
    # Using second as unit for counter here because we want to check frequently
    # whether the main thread for tracking has exited.
    counter_seconds = session_length_in_hours * SECONDS_IN_HOUR
    logging.debug(f'{tracker.dev}: start renewing session')
    while not tracker.stopped:
        time.sleep(1)
        counter_seconds -= 1

        if counter_seconds <= 0:
            # start new session and reset counter
            tracker.renew_session()
            counter_seconds = session_length_in_hours * SECONDS_IN_HOUR
    logging.debug(f'{tracker.dev}: end renewing session')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-log',
                        '--loglevel',
                        default='warning',
                        help='Provide logging level. Example --loglevel debug, default=warning')
    parser.add_argument('-dev',
                        '--device',
                        choices=['both', 'key', 'mouse'],
                        default='both',
                        help='Device to track. Example -dev key, default=both')
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel.upper())
    # Number of hours for each session's length.
    # set to be 30 sec for debugging; change to 1 hr when tracking
    if args.loglevel.upper() == 'DEBUG':
        SESSION_LENGTH_IN_HOURS = 1 / 120
    else:
        SESSION_LENGTH_IN_HOURS = 1

    key_tracker = None
    mouse_tracker = None
    if args.device in ['key', 'both']:
        key_tracker = KeyTrackerPrivate()
        key_tracker_thread = threading.Thread(target=(lambda: run_tracker(key_tracker)), name='key_tracker')
        key_session_thread = threading.Thread(target=(lambda: run_renew_session(key_tracker, SESSION_LENGTH_IN_HOURS)),
                                              name='key_session')

    if args.device in ['mouse', 'both']:
        mouse_tracker = MouseTracker()
        mouse_tracker_thread = threading.Thread(target=(lambda: run_tracker(mouse_tracker)), name='mouse_tracker')
        mouse_session_thread = threading.Thread(
            target=(lambda: run_renew_session(mouse_tracker, SESSION_LENGTH_IN_HOURS)), name='mouse_session')
    try:
        if key_tracker is not None:
            key_tracker_thread.start()
            key_session_thread.start()
        if mouse_tracker is not None:
            mouse_tracker_thread.start()
            mouse_session_thread.start()

        print('\n###############')
        print('TRACKING STARTS')
        print('###############\n')

        if key_tracker is not None:
            # wait for threads to finish
            key_tracker_thread.join()
            key_session_thread.join()
        if mouse_tracker is not None:
            # wait for threads to finish
            mouse_tracker_thread.join()
            mouse_session_thread.join()

    except KeyboardInterrupt:
        print('exiting loggers...')
        if key_tracker is not None:
            key_tracker.stop()
        if mouse_tracker is not None:
            mouse_tracker.stop()

    print('\n#############')
    print('TRACKING ENDS')
    print('#############\n')


if __name__ == '__main__':
    sys.exit(main())
