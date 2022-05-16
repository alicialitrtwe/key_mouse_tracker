from typing import Callable, Dict

from pynput.keyboard import Key

LEFT_ALPHANUM = ['`', '1', '2', '3', '4', '5', '6', '~', '!', '@', '#', '$', '%', '^',
                 'q', 'w', 'e', 'r', 't',
                 'a', 's', 'd', 'f', 'g',
                 'z', 'x', 'c', 'v', 'b', ]

RIGHT_ALPHANUM = ['7', '8', '9', '0', '&', '*', '(', ')', '-', '=', '_', '+',
                  'y', 'u', 'i', 'o', 'p', '[', ']', '{', '}', '|', '\\',
                  'h', 'j', 'k', 'l', ';', ':', "'", '"',
                  'n', 'm', ',', '.', '/', '<', '>', '?']

# Key types of interest along with their differentiator function.
KEY_DICT: Dict[str, Callable[[Key], bool]] = {
    'left_alphanum': lambda key: (hasattr(key, 'char')
                                  and key.char.lower() in LEFT_ALPHANUM),
    'right_alphanum': lambda key: (hasattr(key, 'char')
                                   and key.char.lower() in RIGHT_ALPHANUM),
    'backspace': lambda key: key == Key.backspace,
    'delete': lambda key: key == Key.delete,
    'special': lambda key: (not hasattr(key, 'char')
                            and key != Key.backspace
                            and key != Key.delete)
}
