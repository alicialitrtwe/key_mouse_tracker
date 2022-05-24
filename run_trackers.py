import argparse
import logging
import threading
import time

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
    counter_seconds = SESSION_LENGTH_IN_HOURS * SECONDS_IN_HOUR
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
            counter_seconds = SESSION_LENGTH_IN_HOURS * SECONDS_IN_HOUR


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-log',
                        '--loglevel',
                        default='info',
                        help='Provide logging level. Example --loglevel debug, default=info')
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

    if args.device == 'key' or args.device == 'both':
        key_tracker = KeyTrackerPrivate()
        key_tracker_thread = threading.Thread(target=(lambda: run_tracker(key_tracker)), name='key_tracker')
        key_cron_thread = threading.Thread(target=(lambda: run_cron(key_tracker)), name='key_cron')

    if args.device == 'mouse' or args.device == 'both':
        mouse_tracker = MouseTracker()
        mouse_tracker_thread = threading.Thread(target=(lambda: run_tracker(mouse_tracker)), name='mouse_tracker')
        mouse_cron_thread = threading.Thread(target=(lambda: run_cron(mouse_tracker)), name='mouse_cron')
    try:
        if args.device == 'key' or args.device == 'both':
            key_tracker_thread.start()
            key_cron_thread.start()

        if args.device == 'mouse' or args.device == 'both':
            mouse_tracker_thread.start()
            mouse_cron_thread.start()

        print('\n###############')
        print('TRACKING STARTS')
        print('###############\n')

        if args.device == 'key' or args.device == 'both':
            # wait for threads to finish
            key_tracker_thread.join()
            key_cron_thread.join()

        if args.device == 'mouse' or args.device == 'both':
            # wait for threads to finish
            mouse_tracker_thread.join()
            mouse_cron_thread.join()

    except KeyboardInterrupt:
        if args.device == 'key' or args.device == 'both':
            key_tracker.stop()
        if args.device == 'mouse' or args.device == 'both':
            mouse_tracker.stop()

        print('\n#############')
        print('TRACKING ENDS')
        print('#############\n')
