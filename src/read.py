from typing import List
import re

from config import ENCODED_FILE_PATH, ZERO, ONE


REGEX_HAS_MORE_THAN_0_AND_1 = rf"[^{ZERO}{ONE}]"
COMPILED_REGEX_HAS_MORE_THAN_0_AND_1 = re.compile(REGEX_HAS_MORE_THAN_0_AND_1)

def read_encoded_file_content() -> List[str]: 
    with open(ENCODED_FILE_PATH, "r") as f:
        content = f.read()
        binary_letters = content.split()
    bits_needed = max(map(len, binary_letters))
    zero_padded_chars = [binary_letter.rjust(bits_needed, ZERO) for binary_letter in binary_letters]
    
    if any(filter(COMPILED_REGEX_HAS_MORE_THAN_0_AND_1.search, zero_padded_chars)):
        print("input is not binary")

    return zero_padded_chars