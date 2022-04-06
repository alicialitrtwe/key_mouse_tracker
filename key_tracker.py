from pynput.keyboard import Key, Listener

"""
WARNING: THIS FILE IS DEPRECATED, AS IT DOES NOT PROTECT USER PRIVACY.
"""


def on_press(key):
    try:
        print('alphanumeric key {0} pressed'.format(key.char))
        print(key.char)
    except AttributeError:
        print('special key {0} pressed'.format(key))
        print(key)


def on_release(key):
    print('{0} released'.format(key))
    if key == Key.esc: d
    return False


#
# # Collect events until released
# with Listener(
#         on_press=on_pjjk
#
#
#
#
#         ress,
#         on_release=on_release) as listener:
#     listener.join()

# ...or, in a non-blocking fashion:
listener = Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()
# listener.stop()
