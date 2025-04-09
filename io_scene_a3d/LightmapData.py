'''
Copyright (c) 2025 Pyogenics <https://github.com/Pyogenics>

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

from .IOTools import unpackStream
from . import AlternativaProtocol

class LightmapData:
    def __init__(self):
        self.lightColour = (0.0, 0.0, 0.0)
        self.ambientLightColour = (0.0, 0.0, 0.0)
        self.lightAngle = (0.0, 0.0) # (x, z)
        self.lightmaps = []
        self.mapObjects = []

    def read(self, stream):
        print("Reading LightmapData")

        # There is no signature so just start reading data and hope this is actually a lightmap data file
        version, = unpackStream("<I", stream)
        print(f"Reading LightmapData version {version}")

        if version == 1:
            self.read1(stream)
        elif version == 2:
            self.read2(stream)
        else:
            raise RuntimeError(f"Unknown LightmapData version: {version}")
    
    '''
    Version specific readers
    '''
    def read1(self, stream):
        raise RuntimeError("Version 1 LightmapData is not implemented yet")

    def read2(self, stream):
        # Light info
        self.lightColour, self.ambientLightColour = unpackStream("<2I", stream)
        self.lightAngle = unpackStream("<2f", stream)

        # Lightmaps
        lightmapCount, = unpackStream("<I", stream)
        print(f"Reading {lightmapCount} lightmaps")
        for _ in range(lightmapCount):
            lightmap = AlternativaProtocol.readString(stream)
            self.lightmaps.append(lightmap)

        # Map objects
        mapObjectCount, = unpackStream("<I", stream)
        print(f"Reading {mapObjectCount} map objects")
        for _ in range(mapObjectCount):
            mapObject = MapObject()
            mapObject.read(stream)
            self.mapObjects.append(mapObject)
        
        #XXX: there is more data but do we actually care about it?

        print(f"[LightmapData2 lightColour: {hex(self.lightColour)} ambientLightColour: {hex(self.ambientLightColour)} lightAngle: {self.lightAngle}]")

'''
Objects
'''
class MapObject:
    def __init__(self):
        self.index = 0
        self.lightmapIndex = 0
        self.lightmapScaleOffset = (0.0, 0.0, 0.0, 0.0)
        self.UV1 = []
        self.UV2 = []
        self.castShadows = False
        self.recieveShadows = False
    
    def read(self, stream):
        self.index, self.lightmapIndex = unpackStream("<2i", stream)

        # Read lightmap data
        if self.lightmapIndex >= 0:
            self.lightmapScaleOffset = unpackStream("<4f", stream)

            # Check if we have UVs and read them
            hasUVs, = unpackStream("b", stream)
            if hasUVs > 0:
                vertexCount, = unpackStream("<I", stream)
                for _ in range(vertexCount//2):
                    UV1 = unpackStream("<2f", stream)
                    self.UV1.append(UV1)
                    UV2 = unpackStream("<2f", stream)
                    self.UV2.append(UV2)
        
        # Light settings
        castShadows, recieveShadows = unpackStream("2b", stream)
        self.castShadows = castShadows > 0
        self.recieveShadows = recieveShadows > 0

        print(f"[MapObject index: {self.index} lightmapIndex: {self.lightmapIndex} lightmapScaleOffset: {self.lightmapScaleOffset} UV1: {len(self.UV1)} UV2: {len(self.UV2)} castShadows: {self.castShadows} recieveShadows: {self.recieveShadows}]")