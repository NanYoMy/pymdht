# Released under GNU LGPL 2.1
# See LICENSE.txt for more information

"""
This module provides the Id object and necessary tools.

"""

#binascii.hexlify() bin>hex
#int(a, 16) hex>int
#hex() int>hex

import sys
import random
import base64

import logging

logger = logging.getLogger('dht')


BITS_PER_BYTE = 8
ID_SIZE_BYTES = 20
ID_SIZE_BITS = ID_SIZE_BYTES * BITS_PER_BYTE


def _bin_to_hex(bin_str):
    """Convert a binary string to a hex string."""
    return base64.b16encode(bin_str)

def _hex_to_bin(hex_str):
    try:
        return base64.b16decode(hex_str, True)
    except:
        raise IdError

def _byte_xor(byte1, byte2):
    """Xor two characters as if they were bytes."""
    return chr(ord(byte1) ^ ord(byte2))
               
def _first_different_byte(str1, str2):
    """Return the position of the first different byte in the strings.
    Raise IndexError when no difference was found (str1 == str2).
    """
    for i in range(len(str1)):
        if str1[i] != str2[i]:
            return i
    raise IndexError

def _first_different_bit(byte1, byte2):
    """Return the position of the first different bit in the bytes.
    The bytes must not be equal.

    """
    assert byte1 != byte2
    byte = ord(byte1) ^ ord(byte2)
    i = 0
    while byte >> (BITS_PER_BYTE - 1) == 0:
        byte <<= 1
        i += 1
    return i


class IdError(Exception):
    pass


class Id(object):

    """Convert a string to an Id object.
    The bin_id string's lenght must be ID_SIZE bytes (characters).

    You can use both binary and hexadecimal strings. Example:
    
    >>> Id(chr(0) * ID_SIZE_BYTES) == Id('0' * ID_SIZE_BYTES * 2)
    True
    
    >>> Id(chr(255) * ID_SIZE_BYTES) == Id('f' * ID_SIZE_BYTES * 2)
    True
    """

    def __init__(self, hex_or_bin_id):
        self._bin_id = None
        self._bin = None
        self._hex = None
        self._int = None
        if isinstance(hex_or_bin_id, str):
            if len(hex_or_bin_id) == ID_SIZE_BYTES:
                self._bin_id = hex_or_bin_id
            elif len(hex_or_bin_id) == ID_SIZE_BYTES*2:
                self._hex = hex_or_bin_id
                self._bin_id = _hex_to_bin(hex_or_bin_id)
        elif isinstance(hex_or_bin_id, long) or isinstance(hex_or_bin_id, int):
            self._int = hex_or_bin_id
            self._hex = '%040x' % self._int
            self._bin_id = base64.b16decode(self._hex)
        if not self._bin_id:
            raise IdError, 'input: %r' % hex_or_bin_id
        self._bin = self._bin_id

    def __hash__(self):
        return self.bin_id.__hash__()

    @property
    def bin_id(self):
        """bin_id is read-only."""
        return self._bin
 
    @property
    def bin(self):
        return self._bin

    @property
    def hex(self):
        if not self._hex:
            self._hex = _bin_to_hex(self._bin)
        return self._hex

    @property
    def int(self):
        if not self._int:
            self._int = int(self.hex, 16)
        return self._int
    
    def __eq__(self, other):
        return self.bin_id == other.bin_id

    def __ne__(self, other):
        return not self == other
        
    def __str__(self):
        return self.bin_id

    def __repr__(self):
        return '%s' % self.hex

    def distance(self, other):
        """
        Do XOR distance between two Id objects and return it as Id
        object.

        """
        return Id(self.int ^ other.int)
    
    def log_distance(self, other):
        """Return log (base 2) of the XOR distance between two Id
        objects. Return -1 when the XOR distance is 0.

        That is, this function returns 'n' when the distance between
        the two objects is [2^n, 2^(n+1)).
        When the two identifiers are equal, the distance is 0. Therefore
        log_distance is -infinity. In this case, -1 is returned.
        Example:

        >>> z = Id(chr(0) * ID_SIZE_BYTES)

        >>> # distance = 0 [-inf, 1) -> log(0) = -infinity
        >>> z.log_distance(z) 
        -1
        >>> # distance = 1 [1, 2) -> log(1) = 0
        >>> z.log_distance(Id(chr(0)*(ID_SIZE_BYTES-1)+chr(1)))
        0
        >>> # distance = 2 [2, 4) -> log(2) = 1
        >>> z.log_distance(Id(chr(0)*(ID_SIZE_BYTES-1)+chr(2)))
        1
        >>> # distance = 3 [2, 4) -> log(3) = 
        >>> z.log_distance(Id(chr(0)*(ID_SIZE_BYTES-1)+chr(3)))
        1
        >>> # distance = 4 [4, 8) -> log(2^2) = 2
        >>> z.log_distance(Id(chr(0)*(ID_SIZE_BYTES-1)+chr(4)))
        2
        >>> # distance = 5 [4, 8) -> log(5) = 2
        >>> z.log_distance(Id(chr(0)*(ID_SIZE_BYTES-1)+chr(5)))
        2
        >>> # distance = 6  [4, 8) -> log(6) = 2
        >>> z.log_distance(Id(chr(0)*(ID_SIZE_BYTES-1)+chr(6)))
        2
        >>> # distance = 7  [4, 8) -> log(7) = 2
        >>> z.log_distance(Id(chr(0)*(ID_SIZE_BYTES-1)+chr(7)))
        2
        >>> # distance = 128 = 2^(8*0+7)  [128, 256) -> log(7^2) = 7
        >>> z.log_distance(Id(chr(0)*(ID_SIZE_BYTES-1)+chr(128)))
        7
        >>> # distance = 2^(8*18+8) = 2^148+8 -> log(1) = 152
        >>> z.log_distance(Id(chr(1)+chr(0)*(ID_SIZE_BYTES-1)))
        152
        >>> # distance = 2^(8*19+1) = 2^159 -> log(1) = 159
        >>> z.log_distance(Id(chr(128)+chr(0)*(ID_SIZE_BYTES-1)))
        159

        """
        try:
            byte_i = _first_different_byte(self.bin_id, other.bin_id)
        except IndexError:
            # _first_different_byte did't find differences, thus the
            # distance is 0 and log_distance is -1 
            return -1
        unmatching_bytes = ID_SIZE_BYTES - byte_i - 1
        byte1 = self.bin_id[byte_i]
        byte2 = other.bin_id[byte_i]
        bit_i = _first_different_bit(byte1, byte2)
        # unmatching_bits (in byte: from least significant bit)
        unmatching_bits = BITS_PER_BYTE - bit_i - 1
        return unmatching_bytes * BITS_PER_BYTE + unmatching_bits
    
            
    def order_closest(self, id_list):
        """Return a list with the Id objects in 'id_list' ordered
        according to the distance to self. The closest id first.
        
        The original list is not modified.

        """
        id_list_copy = id_list[:]
        max_distance = ID_SIZE_BITS + 1
        log_distance_list = [] 
        for element in id_list:
            log_distance_list.append(self.log_distance(element))

        result = []
        for _ in range(len(id_list)):
            lowest_index = None
            lowest_distance = max_distance
            for j in range(len(id_list_copy)):
                if log_distance_list[j] < lowest_distance:
                    lowest_index = j
                    lowest_distance = log_distance_list[j]
            result.append(id_list_copy[lowest_index])
            del log_distance_list[lowest_index]
            del id_list_copy[lowest_index]
        return result
    
    def generate_close_id(self, log_distance):
        assert log_distance < ID_SIZE_BITS
        if log_distance < 0:
            return self
        byte_num, bit_num = divmod(log_distance, BITS_PER_BYTE)
        byte_index = len(self.bin_id) - byte_num - 1 # -1 correction
        int_byte = ord(self.bin_id[byte_index])
        import sys
        # Flip bit
        int_byte = int_byte ^ (1 << bit_num)
        for i in range(bit_num):
            # Put bit to 0
            int_byte = int_byte & (255 - (1 << i))
            # Replace bit for random bit
            int_byte = int_byte + (random.randint(0, 1) << i)
        id_byte = chr(int_byte)
        # Produce random ending bytes
        end_bytes = ''.join([chr(random.randint(0, 255)) \
                                      for _ in xrange(byte_index + 1, ID_SIZE_BYTES)])
        bin_id = self.bin_id[:byte_index] +\
            id_byte + end_bytes
        result = Id(bin_id)
        return result 

    
class RandomId(Id):

    """Create a random Id object."""
    def __init__(self):
        random_str = ''.join([chr(random.randint(0, 255)) \
                                      for _ in xrange(ID_SIZE_BYTES)])
        Id.__init__(self, random_str)
