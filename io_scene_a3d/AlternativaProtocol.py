'''
Copyright (c) 2025 Pyogenics

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

from zlib import decompress
from io import BytesIO

from .IOTools import unpackStream

def unwrapPacket(stream):
    print("Unwrapping packet")

    # Determine size and compression
    packetFlags = int.from_bytes(stream.read(1))
    compressedPacket = (packetFlags & 0b01000000) > 0

    packetLength = 0
    packetLengthType = packetFlags & 0b10000000
    if packetLengthType == 0:
        # This is a short packet
        packetLength = int.from_bytes(stream.read(1))
        packetLength += (packetFlags & 0b00111111) << 8 # Part of the length is embedded in the flags field
    else:
        # This is a long packet
        packetLength = int.from_bytes(stream.read(3), "big")
        packetLength += (packetFlags & 0b00111111) << 24
    
    # Decompress the packet if needed
    packetData = stream.read(packetLength)
    if compressedPacket:
        print("Decompressing packet")
        packetData = decompress(packetData)

    return BytesIO(packetData)

def readOptionalMask(stream):
    print("Reading optional mask")

    optionalMask = []

    # Determine mask type (there are multiple length types)
    maskFlags = int.from_bytes(stream.read(1))
    maskLengthType = maskFlags & 0b10000000
    if maskLengthType == 0:
        # Short mask: 5 optional bits + upto 3 extra bytes
        # First read the integrated optional bits
        integratedOptionalBits = maskFlags << 3 # Trim flag bits so we're left with the optionals and some padding bits
        for bitI in range(7, 2, -1): #0b11111000 left to right
            optional = (integratedOptionalBits & 2**bitI) == 0
            optionalMask.append(optional)

        # Now read the external bytes
        externalByteCount = (maskFlags & 0b01100000) >> 5
        externalBytes = stream.read(externalByteCount)
        for externalByte in externalBytes:
            for bitI in range(7, -1, -1): #0b11111111 left to right
                optional = (externalByte & 2**bitI) == 0
                optionalMask.append(optional)
    else:
        # This type of mask encodes an extra length/count field to increase the number of possible optionals significantly
        maskLengthType = maskFlags & 0b01000000
        externalByteCount = 0
        if maskLengthType == 0:
            # Medium mask: stores number of bytes used for the optional mask in the last 6 bits of the flags
            externalByteCount = maskFlags & 0b00111111
        else:
            # Long mask: # Medium mask: stores number of bytes used for the optional mask in the last 6 bits of the flags + 2 extra bytes
            externalByteCount = (maskFlags & 0b00111111) << 16
            externalByteCount += int.from_bytes(stream.read(2), "big")
        
        # Read the external bytes
        externalBytes = stream.read(externalByteCount)
        for externalByte in externalBytes:
            for bitI in range(7, -1, -1): #0b11111111 left to right
                optional = (externalByte & 2**bitI) == 0
                optionalMask.append(optional)

    optionalMask.reverse()
    return optionalMask

'''
Array type readers
'''
def readArrayLength(packet):
    arrayLength = 0

    arrayFlags = int.from_bytes(packet.read(1))
    arrayLengthType = arrayFlags & 0b10000000
    if arrayLengthType == 0:
        # Short array
        arrayLength = arrayFlags & 0b01111111
    else:
        # Long array
        arrayLengthType = arrayFlags & 0b01000000
        if arrayLengthType == 0:
            # Length in last 6 bits of flags + next byte
            arrayLength = (arrayFlags & 0b00111111) << 8
            arrayLength += int.from_bytes(packet.read(1))
        else:
            # Length in last 6 bits of flags + next 2 byte
            arrayLength = (arrayFlags & 0b00111111) << 16
            arrayLength += int.from_bytes(packet.read(2), "big")

    return arrayLength

def readObjectArray(packet, objReader, optionalMask):
    arrayLength = readArrayLength(packet)
    objects = []
    for _ in range(arrayLength):
        obj = objReader()
        obj.read(packet, optionalMask)
        objects.append(obj)

    return objects

def readString(packet):
    stringLength = readArrayLength(packet)
    string = packet.read(stringLength)
    string = string.decode("utf-8")

    return string

def readInt16Array(packet):
    arrayLength = readArrayLength(packet)
    integers = unpackStream(f"{arrayLength}h", packet)

    return list(integers)

def readIntArray(packet):
    arrayLength = readArrayLength(packet)
    integers = unpackStream(f"{arrayLength}i", packet)

    return list(integers)

def readInt64Array(packet):
    arrayLength = readArrayLength(packet)
    integers = unpackStream(f"{arrayLength}q", packet)

    return list(integers)

def readFloatArray(packet):
    arrayLength = readArrayLength(packet)
    floats = unpackStream(f">{arrayLength}f", packet)

    return list(floats)
