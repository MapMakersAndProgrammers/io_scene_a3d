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

from .IOTools import unpackStream
from . import AlternativaProtocol

'''
Objects
'''
class AtlasRect:
    def __init__(self):
        self.height = 0
        self.libraryName = ""
        self.name = ""
        self.width = 0
        self.x = 0
        self.y = 0

    def read(self, stream, optionalMask):
        print("Read AtlasRect")
        self.height, = unpackStream(">I", stream)
        self.libraryName = AlternativaProtocol.readString(stream)
        self.name = AlternativaProtocol.readString(stream)
        self.width, self.x, self.y = unpackStream(">3I", stream)

class CollisionBox:
    def __init__(self):
        self.position = (0.0, 0.0, 0.0)
        self.rotation = (0.0, 0.0, 0.0)
        self.size = (0.0, 0.0, 0.0)

    def read(self, stream, optionalMask):
        print("Read CollisionBox")
        self.position = unpackStream(">3f", stream)
        self.rotation = unpackStream(">3f", stream)
        self.size = unpackStream(">3f", stream)

class CollisionPlane:
    def __init__(self):
        self.length = 0.0
        self.position = (0.0, 0.0, 0.0)
        self.rotation = (0.0, 0.0, 0.0)
        self.width = 0.0

    def read(self, stream, optionalMask):
        print("Read CollisionPlane")
        self.length, = unpackStream(">d", stream)
        self.position = unpackStream(">3f", stream)
        self.rotation = unpackStream(">3f", stream)
        self.width, = unpackStream(">d", stream)

class CollisionTriangle:
    def __init__(self):
        self.length = 0.0
        self.position = (0.0, 0.0, 0.0)
        self.rotation = (0.0, 0.0, 0.0)
        self.v0 = (0.0, 0.0, 0.0)
        self.v1 = (0.0, 0.0, 0.0)
        self.v2 = (0.0, 0.0, 0.0)

    def read(self, stream, optionalMask):
        print("Read CollisionTriangle")
        self.length, = unpackStream(">d", stream)
        self.position = unpackStream(">3f", stream)
        self.rotation = unpackStream(">3f", stream)
        self.v0 = unpackStream(">3f", stream)
        self.v1 = unpackStream(">3f", stream)
        self.v2 = unpackStream(">3f", stream)

class ScalarParameter:
    def __init__(self):
        self.name = ""
        self.value = 0.0

    def read(self, stream, optionalMask):
        print("Read ScalarParameters")
        self.name = AlternativaProtocol.readString(stream)
        self.value, = unpackStream(">f", stream)

class TextureParameter:
    def __init__(self):
        self.name = ""
        self.textureName = ""

        # Optional
        self.libraryName = None

    def read(self, stream, optionalMask):
        print("Read TextureParameter")
        if optionalMask.getOptional():
            self.libraryName = AlternativaProtocol.readString(stream)
        self.name = AlternativaProtocol.readString(stream)
        self.textureName = AlternativaProtocol.readString(stream)

class Vector2Parameter:
    def __init__(self):
        self.name = ""
        self.value = (0.0, 0.0)
    
    def __init__(self, stream, optionalMask):
        print("Read Vector2Parameters")
        self.name = AlternativaProtocol.readString(stream)
        self.value = unpackStream(">2f", stream)

class Vector3Parameter:
    def __init__(self):
        self.name = ""
        self.value = (0.0, 0.0, 0.0)
    
    def __init__(self, stream, optionalMask):
        print("Read Vector3Parameters")
        self.name = AlternativaProtocol.readString(stream)
        self.value = unpackStream(">3f", stream)

class Vector4Parameter:
    def __init__(self):
        self.name = ""
        self.value = (0.0, 0.0, 0.0, 0.0)
    
    def read(self, stream, optionalMask):
        print("Read Vector4Parameters")
        self.name = AlternativaProtocol.readString(stream)
        self.value = unpackStream(">4f", stream)

'''
Main objects
'''
class Atlas:
    def __init__(self):
        self.height = 0
        self.name = ""
        self.padding = 0
        self.rects = []
        self.width = 0

    # Get the rect's texture from an atlas
    # XXX: Handle padding?
    def resolveRectImage(self, rectName, atlasImage):
        rect = None
        for childRect in self.rects:
            if childRect.name == rectName:
                rect = childRect
        if rect == None:
            raise RuntimeError(f"Couldn't find rect with name: {rectName}")
        
        # Cut the texture out
        rectTexture = atlasImage.crop(
            (rect.x, rect.y, rect.x+rect.width, rect.y+rect.height)
        )
        return rectTexture

    def read(self, stream, optionalMask):
        print("Read Atlas")
        self.height, unpackStream(">i", stream)
        self.name = AlternativaProtocol.readString(stream)
        self.padding = unpackStream(">I", stream)
        self.rects = AlternativaProtocol.readObjectArray(stream, AtlasRect, optionalMask)
        self.width, = unpackStream(">I", stream)

class Batch:
    def __init__(self):
        self.materialID = 0
        self.name = ""
        self.position = (0.0, 0.0, 0.0)
        self.propIDs = ""

    def read(self, stream, optionalMask):
        print("Read Batch")
        self.materialID, = unpackStream(">I", stream)
        self.name = AlternativaProtocol.readString(stream)
        self.position = unpackStream(">3f", stream)
        self.propIDs = AlternativaProtocol.readString(stream)

class CollisionGeometry:
    def __init__(self):
        self.boxes = []
        self.planes = []
        self.triangles = []

    def read(self, stream, optionalMask):
        print("Read CollisionGeometry")
        self.boxes = AlternativaProtocol.readObjectArray(stream, CollisionBox, optionalMask)
        self.planes = AlternativaProtocol.readObjectArray(stream, CollisionPlane, optionalMask)
        self.triangles = AlternativaProtocol.readObjectArray(stream, CollisionTriangle, optionalMask)

class Material:
    def __init__(self):
        self.ID = 0
        self.name = ""
        self.shader = ""
        self.textureParameters = None

        # Optional
        self.scalarParameters = None
        self.vector2Parameters = None
        self.vector3Parameters = None
        self.vector4Parameters = None

    def getTextureParameterByName(self, name):
        for textureParameter in self.textureParameters:
            if textureParameter.name == name: return textureParameter

        raise RuntimeError(f"Couldn't find texture parameter with name: {name}")

    def read(self, stream, optionalMask):
        print(f"Read Material")
        self.ID, = unpackStream(">I", stream)
        self.name = AlternativaProtocol.readString(stream)
        if optionalMask.getOptional():
            self.scalarParameters = AlternativaProtocol.readObjectArray(stream, ScalarParameter, optionalMask)
        self.shader = AlternativaProtocol.readString(stream)
        self.textureParameters = AlternativaProtocol.readObjectArray(stream, TextureParameter, optionalMask)
        if optionalMask.getOptional():
            self.vector2Parameters = AlternativaProtocol.readObjectArray(stream, Vector2Parameter, optionalMask)
        if optionalMask.getOptional():
            self.vector3Parameters = AlternativaProtocol.readObjectArray(stream, Vector3Parameter, optionalMask)
        if optionalMask.getOptional():
            self.vector4Parameters = AlternativaProtocol.readObjectArray(stream, Vector4Parameter, optionalMask)

class SpawnPoint:
    def __init__(self):
        self.position = (0.0, 0.0, 0.0)
        self.rotation = (0.0, 0.0, 0.0)
        self.type = 0

    def read(self, stream, optionalMask):
        print("Read SpawnPoint")
        self.position = unpackStream(">3f", stream)
        self.rotation = unpackStream(">3f", stream)
        self.type, = unpackStream(">I", stream)

class Prop:
    def __init__(self):
        self.ID = 0
        self.libraryName = ""
        self.materialID = 0
        self.name = ""
        self.position = (0.0, 0.0, 0.0)

        # Optional
        self.groupName = ""
        self.rotation = (0.0, 0.0, 0.0)
        self.scale = (0.0, 0.0, 0.0)

    def read(self, stream, optionalMask):
        print(f"Read Prop")
        if optionalMask.getOptional():
            self.groupName = AlternativaProtocol.readString(stream)
        self.ID, = unpackStream(">I", stream)
        self.libraryName = AlternativaProtocol.readString(stream)
        self.materialID, = unpackStream(">I", stream)
        self.name = AlternativaProtocol.readString(stream)
        self.position = unpackStream(">3f", stream)
        if optionalMask.getOptional():
            self.rotation = unpackStream(">3f", stream)
        if optionalMask.getOptional():
            self.scale = unpackStream(">3f", stream)

'''
Main
'''
class BattleMap:
    def __init__(self):
        self.atlases = []
        self.batches = []
        self.collisionGeometry = []
        self.collisionGeometryOutsideGamingZone = []
        self.materials = []
        self.spawnPoints = []
        self.staticGeometry = []

    '''
    Getters
    '''
    def getMaterialByID(self, materialID):
        for material in self.materials:
            if material.ID == materialID: return material
        
        raise RuntimeError(f"Couldn't find material with ID: {materialID}")

    '''
    IO
    '''
    def read(self, stream):
        print("Reading BIN map")

        # Read packet
        packet = AlternativaProtocol.readPacket(stream)
        with open("packet.bin", "wb") as packetFile:
            packetFile.write(
                packet.read()
            )
            packet.seek(0)
        optionalMask = AlternativaProtocol.OptionalMask()
        optionalMask.read(packet)

        # Read data
        if optionalMask.getOptional():
            self.atlases = AlternativaProtocol.readObjectArray(packet, Atlas, optionalMask)
        if optionalMask.getOptional():
            self.batches = AlternativaProtocol.readObjectArray(packet, Batch, optionalMask)
        self.collisionGeometry = CollisionGeometry()
        self.collisionGeometry.read(packet, optionalMask)
        self.collisionGeometryOutsideGamingZone = CollisionGeometry()
        self.collisionGeometryOutsideGamingZone.read(packet, optionalMask)
        self.materials = AlternativaProtocol.readObjectArray(packet, Material, optionalMask)
        if optionalMask.getOptional():
            self.spawnPoints = AlternativaProtocol.readObjectArray(packet, SpawnPoint, optionalMask)
        self.staticGeometry = AlternativaProtocol.readObjectArray(packet, Prop, optionalMask)