'''
Copyright (c) 2024 Pyogenics

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from io import BytesIO
from struct import unpack
from array import array
from zlib import decompress

class OptionalMask:
    def __init__(self):
        self.optionalMask = []

    def read(self, stream):
        print("Read optional mask")
        # Read "Null-mask" field
        nullMask = b""
        nullMaskOffset = 0

        nullMaskField = int.from_bytes(stream.read(1), "little")
        nullMaskType = nullMaskField & 0b10000000
        if nullMaskType == 0:
            # Short null-mask: 5-29 bits
            nullMaskLength = nullMaskField & 0b01100000
            
            nullMask += bytes(nullMaskField & 0b00011111)
            nullMask += stream.read(nullMaskLength) # 1,2 or 3 bytes
            nullMaskOffset = 3
        else:
            # Long null-mask: 64 - 4194304 bytes
            nullMaskLengthSize = nullMaskField & 0b01000000
            nullMaskLength = nullMaskField & 0b00111111
            if nullMaskLengthSize > 0:
                # Long length: 22 bits
                nullMaskLength = nullMaskLength << 16
                nullMaskLength += int.from_bytes(stream.read(2), "big")
            else:
                # Short length: 6 bits
                pass
            
            nullMask += stream.read(nullMaskLength)
            nullMaskOffset = 0

        nullMask = BytesIO(nullMask)
        # Process first byte (the first byte is missing some bits on some nullmask configs)
        maskByte = int.from_bytes(nullMask.read(1))
        for bitI in range(7 - nullMaskOffset, -1, -1):
            self.optionalMask.append(
                not bool(maskByte & (2**bitI))
            )

        # Process the rest of the bytes
        for maskByte in nullMask.read():
            for bitI in range(7, -1, -1):
                self.optionalMask.append(
                    not bool(maskByte & (2**bitI))
                )

        print(f"Optional mask flags: {len(self.optionalMask)}")

    def getOptional(self):
        optional = self.optionalMask.pop(0)
        return optional

    def getOptionals(self, count):
        optionals = ()
        for _ in range(count):
            optionals += (self.optionalMask.pop(0),)
        return optionals

    def getLength(self):
        return len(self.optionalMask)

def readPacket(stream):
    print("Reading packet")

    # Read "Package Length" field
    packageLength = 0
    packageGzip = False

    packageLengthField = int.from_bytes(stream.read(1), "little")
    packageLengthSize = packageLengthField & 0b10000000
    if packageLengthSize == 0:
        # Short package: 14 bits
        packageLength += (packageLengthField & 0b00111111) << 8
        packageLength += int.from_bytes(stream.read(1), "little")

        packageGzip = packageLengthField & 0b01000000
    else:
        # Long package: 31 bits
        packageLength += (packageLengthField & 0b00111111) << 24
        packageLength += int.from_bytes(stream.read(3), "little")

        packageGzip = packageLengthField & 0b01000000

    # Decompress gzip data
    package = stream.read()
    if packageGzip:
        print("Decompressing packet")
        package = decompress(package)
    package = BytesIO(package)
    
    return package

'''
Array
'''
def readArrayLength(package):
    arrayLength = 0

    arrayField = int.from_bytes(package.read(1), "little")
    arrayLengthType = arrayField & 0b10000000
    # Short array length
    if arrayLengthType == 0:
        # Length of the array is contained in the last 7 bits of this byte
        arrayLength = arrayField & 0b01111111
    else: # Must be large array length
        longArrayLengthType = arrayField & 0b01000000
        # Length in last 6 bits + next byte
        if longArrayLengthType == 0:
            lengthByte = int.from_bytes(package.read(1), "little")
            arrayLength = (arrayField & 0b00111111) << 8
            arrayLength += lengthByte
        else: # Length in last 6 bits + next 2 bytes
            lengthBytes = int.from_bytes(package.read(2), "big")
            arrayLength = (arrayField & 0b00111111) << 16
            arrayLength += lengthBytes

    return arrayLength

def readObjectArray(package, objReader, optionalMask):
    length = readArrayLength(package)
    objects = []
    for _ in range(length):
        obj = objReader()
        obj.read(package, optionalMask)
        objects.append(obj)

    return objects

def readString(package):
    stringLength = readArrayLength(package)
    string = package.read(stringLength)
    string = string.decode("utf-8")

    return string

def readInt16Array(package):
    length = readArrayLength(package)
    integers = unpack(f"{length}h", package.read(length*2))
    integers = array("h", integers)

    return integers

def readIntArray(package):
    length = readArrayLength(package)
    integers = unpack(f"{length}i", package.read(length*4))
    integers = array("i", integers)

    return integers

def readInt64Array(package):
    length = readArrayLength(package)
    integers = unpack(f"{length}q", package.read(length*8))
    integers = array("q", integers)

    return integers

def readFloatArray(package):
    length = readArrayLength(package)
    floats = unpack(f">{length}f", package.read(length*4))
    floats = array("f", floats)

    return floats