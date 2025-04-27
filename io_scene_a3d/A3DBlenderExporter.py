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

from . import A3DObjects
from .A3DObjects import (
    A3D_VERTEXTYPE_COORDINATE,
    A3D_VERTEXTYPE_UV1,
    A3D_VERTEXTYPE_NORMAL1,
    A3D_VERTEXTYPE_UV2,
    A3D_VERTEXTYPE_COLOR,
    A3D_VERTEXTYPE_NORMAL2
)

class A3DBlenderExporter:
    def __init__(self, modelData, objects):
        self.modelData = modelData
        self.objects = objects

    def exportData(self):
        print("Exporting blender data to A3D")

        # Process objects
        materials = {}
        meshes = []
        transforms = {}
        objects = []
        for ob in self.objects:
            me = ob.data

            # Process materials
            for ma in me.materials:
                # Make sure we haven't processed this data block already
                if ma.name in materials:
                    continue

                materialData = A3DObjects.A3DMaterial()
                materialData.name = ma.name
                materialData.diffuseMap = ""
                colorR, colorG, colorB, _ = ma.diffuse_color
                materialData.color = (colorR, colorG, colorB)

                materials[ma.name] = materialData
            # Create mesh
            mesh = self.buildA3DMesh(me)
            meshes.append(mesh)
            # Create transform
            transform = A3DObjects.A3DTransform()
            transform.position = ob.location
            rotationW, rotationX, rotationY, rotationZ = ob.rotation_quaternion
            transform.rotation = (rotationX, rotationY, rotationZ, rotationW)
            transform.scale = ob.scale
            transforms[ob.name] = transform
            # Create object
            objec = A3DObjects.A3DObject()
            objec.name = ob.name
            objec.meshID = len(meshes) - 1
            objec.transformID = len(transforms) - 1
            objects.append(objec)
        # Create parentIDs
        transformParentIDs = []
        for ob in self.objects:
            parentOB = ob.parent
            if (parentOB == None) or (parentOB.name not in transforms):
                transformParentIDs.append(0) #XXX: this is only for version 2
            else:
                parentIndex = list(transforms.keys()).index(parentOB.name)
                transformParentIDs.append(parentIndex+1)

        self.modelData.materials = materials.values()
        self.modelData.meshes = meshes
        self.modelData.transforms = transforms.values()
        self.modelData.transformParentIDs = transformParentIDs
        self.modelData.objects = objects

    def buildA3DMesh(self, me):
        mesh = A3DObjects.A3DMesh()
        mesh.vertexCount = len(me.vertices)

        # Create vertex buffers
        coordinateBuffer = A3DObjects.A3DVertexBuffer()
        coordinateBuffer.bufferType = A3D_VERTEXTYPE_COORDINATE
        normal1Buffer = A3DObjects.A3DVertexBuffer()
        normal1Buffer.bufferType = A3D_VERTEXTYPE_NORMAL1
        for vertex in me.vertices:
            coordinateBuffer.data.append(vertex.co)
            normal1Buffer.data.append(vertex.normal)
        uv1Buffer = A3DObjects.A3DVertexBuffer()
        uv1Buffer.bufferType = A3D_VERTEXTYPE_UV1
        uv1Data = me.uv_layers[0]
        for vertex in uv1Data.uv:
            uv1Buffer.data.append(vertex.vector)
        mesh.vertexBufferCount = 2 #XXX: We only do coordinate, normal1 and uv1
        mesh.vertexBuffers = [coordinateBuffer, normal1Buffer]

        # Create submeshes
        indexArrays = {} # material_index: index array
        lastMaterialIndex = None
        for polygon in me.polygons:
            if polygon.material_index != lastMaterialIndex:
                indexArrays[polygon.material_index] = []
            
            indexArrays[polygon.material_index] += polygon.vertices
            lastMaterialIndex = polygon.material_index
        submeshes = []
        for materialID, indexArray in indexArrays.items():
            submesh = A3DObjects.A3DSubmesh()
            submesh.indexCount = len(indexArray)
            submesh.indices = indexArray
            submesh.materialID = materialID
            submesh.smoothingGroups = [0] * (len(indexArray)//3) # Just set all faces to 0
            submeshes.append(submesh)
        mesh.submeshCount = len(submeshes)
        mesh.submeshes = submeshes

        return mesh
