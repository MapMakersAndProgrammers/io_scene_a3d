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

from json import load

import bpy
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
from bpy_extras.image_utils import load_image
import bmesh

from .A3D import A3D
from .A3DBlenderImporter import A3DBlenderImporter
from .BlenderUtils import addImageTextureToMaterial

class PropLibrary:
    propCache = {}

    def __init__(self, directory):
        self.directory = directory

        # Load library json
        self.libraryInfo = {}
        with open(f"{self.directory}/library.json", "r") as file: # XXX: Get platform agnostic way of doing this
            self.libraryInfo = load(file)
        
        print(f"Loaded prop library: {self.libraryInfo["name"]}")
    
    def getProp(self, name, groupName):
        # XXX: Handle group names, this code can only load from the remaster libs
        # Check if the prop is cached
        if not name in self.propCache:
            # Get the prop's info
            propGroupInfo = self.libraryInfo["groups"][0]
            propInfo = {}
            for propInfo in propGroupInfo["props"]:
                if propInfo["name"] == name: break

            # Load the prop
            modelFilePath = f"{self.directory}/{propInfo['mesh']['file']}" # XXX: Get platform agnostic way of doing this
            modelData = A3D()
            with open(modelFilePath, "rb") as file:
                modelData.read(file)
            
            # Import into blender
            modelImporter = A3DBlenderImporter(modelData, self.directory, try_import_textures=False)
            ob, = modelImporter.importData()
            
            self.propCache[name] = ob
        
        return self.propCache[name]
    
    def getTexture(self, textureName):
        im = load_image(textureName, self.directory)
        return im

class BattleMapBlenderImporter:
    # Allows subsequent map loads to be faster
    libraryCache = {}

    def __init__(self, mapData, propLibrarySourcePath, import_static_geom=True, import_collision_geom=False, import_spawn_points=False):
        self.mapData = mapData
        self.propLibrarySourcePath = propLibrarySourcePath
        self.import_static_geom = import_static_geom
        self.import_collision_geom = import_collision_geom
        self.import_spawn_points = import_spawn_points

        self.materials = {}

    def importData(self):
        print("Importing BattleMap data into blender")

        # Process materials
        for materialData in self.mapData.materials:
            ma = self.createBlenderMaterial(materialData)
            self.materials[materialData.ID] = ma

        propObjects = []
        if self.import_static_geom:
            # Load props
            for propData in self.mapData.staticGeometry:
                ob = self.getBlenderProp(propData)
                propObjects.append(ob)
        collisionObjects = []
        if self.import_collision_geom:
            # Load collision meshes
            collisionTriangles = self.mapData.collisionGeometry.triangles + self.mapData.collisionGeometryOutsideGamingZone.triangles
            collisionTriangleObjects = self.createBlenderCollisionTriangles(collisionTriangles)
            collisionPlanes = self.mapData.collisionGeometry.planes + self.mapData.collisionGeometryOutsideGamingZone.planes
            collisionPlaneObjects = self.createBlenderCollisionPlanes(collisionPlanes)
            collisionBoxes = self.mapData.collisionGeometry.boxes + self.mapData.collisionGeometryOutsideGamingZone.boxes
            collisionBoxObjects = self.createBlenderCollisionBoxes(collisionBoxes)

            collisionObjects += collisionTriangleObjects
            collisionObjects += collisionPlaneObjects
            collisionObjects += collisionBoxObjects
        spawnPointObjects = []
        if self.import_spawn_points:
            # Create spawn points
            for spawnPointData in self.mapData.spawnPoints:
                ob = self.createBlenderSpawnPoint(spawnPointData)
                spawnPointObjects.append(ob)

        # Create empty objects to house each type of object
        objects = propObjects + collisionObjects + spawnPointObjects
        if self.import_static_geom:
            groupOB = bpy.data.objects.new("StaticGeometry", None)
            objects.append(groupOB)
            for ob in propObjects:
                ob.parent = groupOB
        if self.import_collision_geom:
            groupOB = bpy.data.objects.new("CollisionGeometry", None)
            objects.append(groupOB)
            for ob in collisionObjects:
                ob.parent = groupOB
        if self.import_spawn_points:
            groupOB = bpy.data.objects.new("SpawnPoints", None)
            objects.append(groupOB)
            for ob in spawnPointObjects:
                ob.parent = groupOB

        return objects

    def getBlenderProp(self, propData):
        # First check if we've already loaded the required prop library
        if not propData.libraryName in self.libraryCache:
            # Load the proplib
            libraryPath = f"{self.propLibrarySourcePath}/{propData.libraryName}" # XXX: Get platform agnostic way of doing this
            library = PropLibrary(libraryPath)
            self.libraryCache[propData.libraryName] = library

        # Load prop
        propLibrary = self.libraryCache[propData.libraryName]
        propOB = propLibrary.getProp(propData.name, propData.groupName)
        propOB = propOB.copy() # We want to use a copy of the prop object
        
        # Assign data
        propOB.name = f"{propData.name}_{propData.ID}"
        propOB.location = propData.position
        propOB.rotation_mode = "XYZ"
        propOB.rotation_euler = propData.rotation
        propOB.scale = propData.scale

        # Material
        ma = self.materials[propData.materialID]
        propOB.data.materials[0] = ma

        return propOB
    
    def createBlenderCollisionTriangles(self, collisionTriangles):
        objects = []
        for collisionTriangle in collisionTriangles:
            # Create the mesh
            me = bpy.data.meshes.new("collisionTriangle")
            
            # Create array for coordinate data, blender doesn't like tuples
            vertices = []
            vertices += collisionTriangle.v0
            vertices += collisionTriangle.v1
            vertices += collisionTriangle.v2

            # Assign coordinates
            me.vertices.add(3)
            me.vertices.foreach_set("co", vertices)
            me.loops.add(3)
            me.loops.foreach_set("vertex_index", [0, 1, 2])
            me.polygons.add(1)
            me.polygons.foreach_set("loop_start", [0])

            me.validate()
            me.update()

            # Create object
            ob = bpy.data.objects.new("collisionTriangle", me)
            ob.location = collisionTriangle.position
            ob.rotation_mode = "XYZ"
            ob.rotation_euler = collisionTriangle.rotation
            #print(collisionTriangle.length) # XXX: how to handle collisionTriangle.length?
            
            objects.append(ob)

        return objects

    def createBlenderCollisionPlanes(self, collisionPlanes):
        objects = []
        for collisionPlane in collisionPlanes:
            # Create the mesh
            me = bpy.data.meshes.new("collisionPlane")
            
            bm = bmesh.new()
            bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
            bm.to_mesh(me)
            bm.free()

            # Create object
            ob = bpy.data.objects.new("collisionPlane", me)
            ob.location = collisionPlane.position
            ob.rotation_mode = "XYZ"
            ob.rotation_euler = collisionPlane.rotation
            ob.scale = (collisionPlane.width*0.5, collisionPlane.length*0.5, 1.0) # Unsure why they double the width and length, could be because of central origin?

            objects.append(ob)

        return objects

    def createBlenderCollisionBoxes(self, collisionBoxes):
        objects = []
        for collisionBox in collisionBoxes:
            # Create the mesh
            me = bpy.data.meshes.new("collisionBox")
            
            bm = bmesh.new()
            bmesh.ops.create_cube(bm)
            bm.to_mesh(me)
            bm.free()

            # Create object
            ob = bpy.data.objects.new("collisionBox", me)
            ob.location = collisionBox.position
            ob.rotation_mode = "XYZ"
            ob.rotation_euler = collisionBox.rotation
            ob.scale = collisionBox.size

            objects.append(ob)

        return objects
    
    def createBlenderSpawnPoint(self, spawnPointData):
        #TODO: implement spawn type name lookup
        ob = bpy.data.objects.new(f"SpawnPoint_{spawnPointData.type}", None)
        ob.empty_display_type = "ARROWS"
        ob.empty_display_size = 100
        ob.location = spawnPointData.position
        ob.rotation_mode = "XYZ"
        ob.rotation_euler = spawnPointData.rotation
        
        return ob
    
    def createBlenderMaterial(self, materialData):
        ma = bpy.data.materials.new(f"{materialData.ID}_{materialData.name}")

        # Shader specific logic
        if materialData.shader == "TankiOnline/SingleTextureShader":
            # First check if we've already loaded the required prop library
            if not "Remaster" in self.libraryCache:
                # Load the proplib
                libraryPath = f"{self.propLibrarySourcePath}/Remaster" # XXX: Get platform agnostic way of doing this
                library = PropLibrary(libraryPath)
                self.libraryCache["Remaster"] = library

            # Try load texture
            textureParameter = materialData.textureParameters[0]
            library = self.libraryCache["Remaster"] #XXX: libraryName is optional
            image = library.getTexture(f"{textureParameter.textureName}.webp")

            # Apply texture
            maWrapper = PrincipledBSDFWrapper(ma, is_readonly=False, use_nodes=True)
            addImageTextureToMaterial(image, ma.node_tree)
        elif materialData.shader == "TankiOnline/SpriteShader":
            pass

        return ma