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

from .IOTools import unpackStream, readNullTerminatedString, calculatePadding
from . import A3DObjects

'''
A3D constants
'''
A3D_SIGNATURE = b"A3D\0"
A3D_ROOTBLOCK_SIGNATURE = 1
A3D_MATERIALBLOCK_SIGNATURE = 4
A3D_MESHBLOCK_SIGNATURE = 2
A3D_TRANSFORMBLOCK_SIGNATURE = 3
A3D_OBJECTBLOCK_SIGNATURE = 5

'''
A3D model object
'''
class A3D:
    def __init__(self):
        self.version = 0

        self.materials = []
        self.meshes = []
        self.transforms = []
        self.transformParentIDs = []
        self.objects = []

    '''
    Main IO
    '''
    def read(self, stream):
        # Check signature
        signature = stream.read(4)
        if signature != A3D_SIGNATURE:
            raise RuntimeError(f"Invalid A3D signature: {signature}")
        
        # Read file version and read version specific data
        self.version, _ = unpackStream("<2H", stream) # Likely major.minor version code
        print(f"Reading A3D version {self.version}")
        
        if self.version == 1:
            self.readRootBlock1(stream)
        elif self.version == 2:
            self.readRootBlock2(stream)
        elif self.version == 3:
            self.readRootBlock3(stream)

    '''
    Root data blocks
    '''
    def readRootBlock1(self, stream):
        raise RuntimeError("Version 1 files are not supported yet")

    def readRootBlock2(self, stream):
        # Verify signature
        signature, _ = unpackStream("<2I", stream)
        if signature != A3D_ROOTBLOCK_SIGNATURE:
            raise RuntimeError(f"Invalid root data block signature: {signature}")
        
        # Read data
        print(f"Reading root block")
        self.readMaterialBlock2(stream)
        self.readMeshBlock2(stream)
        self.readTransformBlock2(stream)
        self.readObjectBlock2(stream)

    def readRootBlock3(self, stream):
        # Verify signature
        signature, length = unpackStream("<2I", stream)
        if signature != A3D_ROOTBLOCK_SIGNATURE:
            raise RuntimeError(f"Invalid root data block signature: {signature}")

        # Read data
        self.readMaterialBlock3(stream)
        self.readMeshBlock3(stream)
        self.readTransformBlock3(stream)
        self.readObjectBlock3(stream)

        # Padding
        padding = calculatePadding(length)
        stream.read(padding)

    '''
    Material data blocks
    '''
    def readMaterialBlock2(self, stream):
        # Verify signature
        signature, _, materialCount = unpackStream("<3I", stream)
        if signature != A3D_MATERIALBLOCK_SIGNATURE:
            raise RuntimeError(f"Invalid material data block signature: {signature}")
        
        # Read data
        print(f"Reading material block with {materialCount} materials")
        for _ in range(materialCount):
            material = A3DObjects.A3DMaterial()
            material.read2(stream)
            self.materials.append(material)
    
    def readMaterialBlock3(self, stream):
        # Verify signature
        signature, length, materialCount = unpackStream("<3I", stream)
        if signature != A3D_MATERIALBLOCK_SIGNATURE:
            raise RuntimeError(f"Invalid material data block signature: {signature}")

        # Read data
        print(f"Reading material block with {materialCount} materials and length {length}")
        for _ in range(materialCount):
            material = A3DObjects.A3DMaterial()
            material.read3(stream)
            self.materials.append(material)

        # Padding
        padding = calculatePadding(length)
        stream.read(padding)

    '''
    Mesh data blocks
    '''
    def readMeshBlock2(self, stream):
        # Verify signature
        signature, _, meshCount = unpackStream("<3I", stream)
        if signature != A3D_MESHBLOCK_SIGNATURE:
            raise RuntimeError(f"Invalid mesh data block signature: {signature}")

        # Read data
        print(f"Reading mesh block with {meshCount} meshes")
        for _ in range(meshCount):
            mesh = A3DObjects.A3DMesh()
            mesh.read2(stream)
            self.meshes.append(mesh)

    def readMeshBlock3(self, stream):
        # Verify signature
        signature, length, meshCount = unpackStream("<3I", stream)
        if signature != A3D_MESHBLOCK_SIGNATURE:
            raise RuntimeError(f"Invalid mesh data block signature: {signature}")

        # Read data
        print(f"Reading mesh block with {meshCount} meshes and length {length}")
        for _ in range(meshCount):
            mesh = A3DObjects.A3DMesh()
            mesh.read3(stream)
            self.meshes.append(mesh)
        
        # Padding
        padding = calculatePadding(length)
        stream.read(padding)

    '''
    Transform data blocks
    '''
    def readTransformBlock2(self, stream):
        # Verify signature
        signature, _, transformCount = unpackStream("<3I", stream)
        if signature != A3D_TRANSFORMBLOCK_SIGNATURE:
            raise RuntimeError(f"Invalid transform data block signature: {signature}")

        # Read data
        print(f"Reading transform block with {transformCount} transforms")
        for _ in range(transformCount):
            transform = A3DObjects.A3DTransform()
            transform.read2(stream)
            self.transforms.append(transform)
        # Read parent ids
        for _ in range(transformCount):
            parentID, = unpackStream("<i", stream)
            self.transformParentIDs.append(parentID)

    def readTransformBlock3(self, stream):
        # Verify signature
        signature, length, transformCount = unpackStream("<3I", stream)
        if signature != A3D_TRANSFORMBLOCK_SIGNATURE:
            raise RuntimeError(f"Invalid transform data block signature: {signature}")

        # Read data
        print(f"Reading transform block with {transformCount} transforms and length {length}")
        transforms = []
        for _ in range(transformCount):
            transform = A3DObjects.A3DTransform()
            transform.read3(stream)
            self.transforms.append(transform)
        # Read parent ids
        for _ in range(transformCount):
            parentID, = unpackStream("<i", stream)
            self.transformParentIDs.append(parentID)

        # Padding
        padding = calculatePadding(length)
        stream.read(padding)

    '''
    Object data blocks
    '''
    def readObjectBlock2(self, stream):
        # Verify signature
        signature, _, objectCount = unpackStream("<3I", stream)
        if signature != A3D_OBJECTBLOCK_SIGNATURE:
            raise RuntimeError(f"Invalid object data block signature: {signature}")

        # Read data
        print(f"Reading object block with {objectCount} objects")
        for _ in range(objectCount):
            objec = A3DObjects.A3DObject()
            objec.read2(stream)
            self.objects.append(objec)

    def readObjectBlock3(self, stream):
        # Verify signature
        signature, length, objectCount = unpackStream("<3I", stream)
        if signature != A3D_OBJECTBLOCK_SIGNATURE:
            raise RuntimeError(f"Invalid object data block signature: {signature}")

        # Read data
        print(f"Reading object block with {objectCount} objects and length {length}")
        for _ in range(objectCount):
            objec = A3DObjects.A3DObject()
            objec.read3(stream)
            self.objects.append(objec)

        # Padding
        padding = calculatePadding(length)
        stream.read(padding)