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

import bpy
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
from bpy_extras.image_utils import load_image

from .A3DObjects import (
    A3D_VERTEXTYPE_COORDINATE,
    A3D_VERTEXTYPE_UV1,
    A3D_VERTEXTYPE_NORMAL1,
    A3D_VERTEXTYPE_UV2,
    A3D_VERTEXTYPE_COLOR,
    A3D_VERTEXTYPE_NORMAL2
)
from .BlenderMaterialUtils import addImageTextureToMaterial

def mirrorUVY(uv):
    x, y = uv
    return (x, 1-y)

class A3DBlenderImporter:
    def __init__(self, modelData, directory, reset_empty_transform=True, try_import_textures=True):
        self.modelData = modelData
        self.directory = directory
        self.materials = []
        self.meshes = []

        # User settings
        self.reset_empty_transform = reset_empty_transform
        self.try_import_textures = try_import_textures

    def importData(self):
        print("Importing A3D model data into blender")
        
        # Create materials
        for materialData in self.modelData.materials:
            ma = self.buildBlenderMaterial(materialData)
            self.materials.append(ma)
        
        # Build meshes
        for meshData in self.modelData.meshes:
            me = self.buildBlenderMesh(meshData)
            self.meshes.append(me)
        
        # Create objects
        objects = []
        for objectData in self.modelData.objects:
            ob = self.buildBlenderObject(objectData)
            objects.append(ob)
        # Assign object parents and link to collection
        for obI, ob in enumerate(objects):
            # Assign parents
            parentID = self.modelData.transformParentIDs[obI]
            if parentID == 0 and self.modelData.version < 3:
                # version 2 models use 0 to signify empty parent
                continue
            elif parentID == -1:
                # version 3 models use -1 to signify empty parent
                continue
            parentOB = objects[parentID]
            ob.parent = parentOB
        
        return objects

    '''
    Blender data builders
    '''
    def buildBlenderMaterial(self, materialData):
        ma = bpy.data.materials.new(materialData.name)
        maWrapper = PrincipledBSDFWrapper(ma, is_readonly=False, use_nodes=True)
        maWrapper.base_color = materialData.color
        maWrapper.roughness = 1.0
        
        return ma

    def buildBlenderMesh(self, meshData):
        me = bpy.data.meshes.new(meshData.name)

        # Gather all vertex data
        coordinates = []
        uv1 = []
        normal1 = []
        uv2 = []
        colors = []
        normal2 = []
        for vertexBuffer in meshData.vertexBuffers:
            if vertexBuffer.bufferType == A3D_VERTEXTYPE_COORDINATE:
                coordinates += vertexBuffer.data
            elif vertexBuffer.bufferType == A3D_VERTEXTYPE_UV1:
                uv1 += vertexBuffer.data
            elif vertexBuffer.bufferType == A3D_VERTEXTYPE_NORMAL1:
                normal1 += vertexBuffer.data
            elif vertexBuffer.bufferType == A3D_VERTEXTYPE_UV2:
                uv2 += vertexBuffer.data
            elif vertexBuffer.bufferType == A3D_VERTEXTYPE_COLOR:
                colors += vertexBuffer.data
            elif vertexBuffer.bufferType == A3D_VERTEXTYPE_NORMAL2:
                normal2 += vertexBuffer.data

        # Add blender vertices
        blenderCoordinates = []
        for coordinate in coordinates:
            blenderCoordinates += coordinate # Blender doesn't like tuples
        me.vertices.add(len(blenderCoordinates)//3)
        me.vertices.foreach_set("co", blenderCoordinates)
        # Aggregate submesh data and import
        indices = []
        for submesh in meshData.submeshes:
            indices += submesh.indices
        me.loops.add(len(indices))
        me.loops.foreach_set("vertex_index", indices)
        me.polygons.add(len(indices)//3)
        me.polygons.foreach_set("loop_start", range(0, len(indices), 3))

        # UVs
        if len(uv1) != 0:
            uvData = me.uv_layers.new(name="UV1").data
            for po in me.polygons:
                uvData[po.loop_start].uv = mirrorUVY(uv1[indices[po.loop_start]])
                uvData[po.loop_start+1].uv = mirrorUVY(uv1[indices[po.loop_start+1]])
                uvData[po.loop_start+2].uv = mirrorUVY(uv1[indices[po.loop_start+2]])
        if len(uv2) != 0:
            uvData = me.uv_layers.new(name="UV2").data
            for po in me.polygons:
                uvData[po.loop_start].uv = mirrorUVY(uv2[indices[po.loop_start]])
                uvData[po.loop_start+1].uv = mirrorUVY(uv2[indices[po.loop_start+1]])
                uvData[po.loop_start+2].uv = mirrorUVY(uv2[indices[po.loop_start+2]])

        # Apply materials (version 2)
        faceIndexBase = 0
        for submeshI, submesh in enumerate(meshData.submeshes):
            if submesh.materialID == None or len(self.materials) == 0: #XXX: perhaps try add a material slot to the object so we still make use of the submesh data instead of skipping it when there are no materials?
                # if materialID is None then this is a version 3 model submesh
                continue
            me.materials.append(self.materials[submesh.materialID])
            for faceI in range(submesh.indexCount//3):
                me.polygons[faceI+faceIndexBase].material_index = submeshI
            faceIndexBase += submesh.indexCount//3

        # Finalise
        me.validate()
        me.update()
        return me

    def buildBlenderObject(self, objectData):
        me = self.meshes[objectData.meshID]
        mesh = self.modelData.meshes[objectData.meshID]
        transform = self.modelData.transforms[objectData.transformID]

        # Apply materials to mesh (version 3)
        for materialID in objectData.materialIDs:
            if materialID == -1:
                continue
            me.materials.append(self.materials[materialID])
        # Set the default material to the first one we added
        for polygon in me.polygons:
            polygon.material_index = 0

        # Select a name for the blender object
        #XXX: review this, maybe we should just stick to the name we are given
        name = ""
        if objectData.name != "":
            name = objectData.name
        elif mesh.name != "":
            name = mesh.name
        else:
            name = transform.name

        # Create the object
        ob = bpy.data.objects.new(name, me)

        # Set transform
        ob.location = transform.position
        ob.scale = transform.scale
        ob.rotation_mode = "QUATERNION"
        x, y, z, w = transform.rotation
        ob.rotation_quaternion = (w, x, y, z)
        if self.reset_empty_transform:
            if transform.scale == (0.0, 0.0, 0.0): ob.scale = (1.0, 1.0, 1.0)
            if transform.rotation == (0.0, 0.0, 0.0, 0.0): ob.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)

        # Attempt to load textures
        if self.try_import_textures and len(me.materials) != 0:
            ma = me.materials[0] # Assume this is the main material
            name = name.lower()
            if name == "hull" or name == "turret":
                # lightmap.webp
                print("Load lightmap")
                
                # Load image
                image = load_image("lightmap.webp", self.directory, check_existing=True)
                # Apply image
                addImageTextureToMaterial(image, ma.node_tree)
            elif "track" in name:
                # tracks.webp
                print("Load tracks")

                # Load image
                image = load_image("tracks.webp", self.directory, check_existing=True)
                # Apply image
                addImageTextureToMaterial(image, ma.node_tree)
            elif "wheel" in name:
                # wheels.webp
                print("Load wheels")

                # Load image
                image = load_image("wheels.webp", self.directory, check_existing=True)
                # Apply image
                addImageTextureToMaterial(image, ma.node_tree)

        return ob