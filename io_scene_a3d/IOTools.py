'''
Copyright (c) 2024 Pyogenics <https://github.com/Pyogenics>

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

from struct import unpack, pack, calcsize

def unpackStream(format, stream):
    size = calcsize(format)
    data = stream.read(size)
    return unpack(format, data)

def packStream(format, stream, *data):
    packedData = pack(format, *data)
    stream.write(packedData)

def readNullTerminatedString(stream):
    string = b""
    char = stream.read(1)
    while char != b"\x00":
        string += char
        char = stream.read(1)
    return string.decode("utf-8", errors="ignore")

def writeNullTerminatedString(stream, string):
    string = string.encode("utf-8")
    stream.write(string)
    stream.write(b"\x00")

def calculatePadding(length):
    # (it basically works with rounding)
    paddingSize = (((length + 3) // 4) * 4) - length
    return paddingSize

def readLengthPrefixedString(stream):
    length, = unpackStream("<I", stream)
    string = stream.read(length)

    paddingSize = calculatePadding(length)
    stream.read(paddingSize)

    return string.decode("utf8", errors="ignore")

def writeLengthPrefixedString(stream, string):
    string = string.encode("utf-8")

    packStream("<I", stream, len(string))
    stream.write(string)

    paddingSize = calculatePadding(len(string))
    stream.write(b"\x00" * paddingSize)