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
from bpy_extras.image_utils import load_image
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper
import bmesh
from mathutils import Matrix

from .A3D import A3D
from .A3DBlenderImporter import A3DBlenderImporter
from .BlenderMaterialUtils import addImageTextureToMaterial, decodeIntColorToTuple

class BattleMapBlenderImporter:
    # Allows subsequent map loads to be faster
    libraryCache = {}

    def __init__(self, mapData, lightmapData, propLibrarySourcePath, map_scale_factor=0.01, import_static_geom=True, import_collision_geom=False, import_spawn_points=False, import_lightmapdata=False):
        self.mapData = mapData
        self.lightmapData = lightmapData
        self.propLibrarySourcePath = propLibrarySourcePath
        self.map_scale_factor = map_scale_factor
        self.import_static_geom = import_static_geom
        self.import_collision_geom = import_collision_geom
        self.import_spawn_points = import_spawn_points
        self.import_lightmapdata = import_lightmapdata

        # Cache for collision meshes, don't cache triangles because they are set using unique vertices
        self.collisionPlaneMesh = None
        self.collisionBoxMesh = None

        self.materials = {}

    def importData(self):
        print("Importing BattleMap data into blender")

        # Process materials
        for materialData in self.mapData.materials:
            ma = self.createBlenderMaterial(materialData)
            self.materials[materialData.ID] = ma

        # Static geometry
        propObjects = []
        if self.import_static_geom:
            # Load props
            for propData in self.mapData.staticGeometry:
                ob = self.getBlenderProp(propData)
                propObjects.append(ob)
        print(f"Loaded {len(propObjects)} prop objects")

        # Collision geometry
        collisionObjects = []
        if self.import_collision_geom:
            # Create collision meshes
            self.collisionPlaneMesh = bpy.data.meshes.new("collisionPlane")
            bm = bmesh.new()
            bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
            bm.to_mesh(self.collisionPlaneMesh)
            bm.free()

            self.collisionBoxMesh = bpy.data.meshes.new("collisionBox")
            bm = bmesh.new()
            bmesh.ops.create_cube(bm)
            bm.to_mesh(self.collisionBoxMesh)
            bm.free()

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
        print(f"Loaded {len(collisionObjects)} collision objects")

        # Spawn points
        spawnPointObjects = []
        if self.import_spawn_points:
            # Create spawn points
            for spawnPointData in self.mapData.spawnPoints:
                ob = self.createBlenderSpawnPoint(spawnPointData)
                spawnPointObjects.append(ob)
        print(f"Loaded {len(spawnPointObjects)} spawn points")

        # Create container object to store all our objects
        objects = propObjects + collisionObjects + spawnPointObjects
        mapOB = bpy.data.objects.new("BattleMap", None)
        mapOB.empty_display_size = 100 # Alternativa use a x100 scale
        mapOB.scale = (self.map_scale_factor, self.map_scale_factor, self.map_scale_factor)
        objects.append(mapOB)

        # Create empty objects to group each type of object
        if self.import_static_geom:
            groupOB = bpy.data.objects.new("StaticGeometry", None)
            groupOB.parent = mapOB
            objects.append(groupOB)
            for ob in propObjects:
                ob.parent = groupOB
        if self.import_collision_geom:
            groupOB = bpy.data.objects.new("CollisionGeometry", None)
            groupOB.parent = mapOB
            objects.append(groupOB)
            for ob in collisionObjects:
                ob.parent = groupOB
        if self.import_spawn_points:
            groupOB = bpy.data.objects.new("SpawnPoints", None)
            groupOB.parent = mapOB
            objects.append(groupOB)
            for ob in spawnPointObjects:
                ob.parent = groupOB

        # Lighting data
        if self.import_lightmapdata:
            # Create a sun light object
            li = bpy.data.lights.new("DirectionalLight", "SUN")
            li.color = decodeIntColorToTuple(self.lightmapData.lightColour)
            
            ob = bpy.data.objects.new(li.name, li)
            ob.location = (0.0, 0.0, 1000.0) # Just place it like 10 meters off the ground (in alternativa units)
            lightAngleX, lightAngleZ = self.lightmapData.lightAngle
            ob.rotation_mode = "XYZ"
            ob.rotation_euler = (lightAngleX, 0.0, lightAngleZ)

            ob.parent = mapOB
            objects.append(ob)

            # Set ambient world light
            scene = bpy.context.scene
            if scene.world == None:
                wd = bpy.data.worlds.new("map")
                scene.world = wd
            world = scene.world
            world.use_nodes = False
            world.color = decodeIntColorToTuple(self.lightmapData.ambientLightColour)

        return objects

    def getPropLibrary(self, libraryName):
        # First check if we've already loaded the required prop library
        if not libraryName in self.libraryCache:
            # Load the proplib
            libraryPath = f"{self.propLibrarySourcePath}/{libraryName}"
            library = PropLibrary(libraryPath)
            self.libraryCache[libraryName] = library

        return self.libraryCache[libraryName]

    def tryLoadTexture(self, textureName, libraryName):
        if libraryName == None:
            # For some reason Remaster proplib is alwaus marked as None? This is not true for the ny2024 remaster prop lib though
            libraryName = "Remaster"

        propLibrary = self.getPropLibrary(libraryName)
        texture = propLibrary.getTexture(f"{textureName}.webp")
        return texture

    '''
    Blender data builders
    '''
    def getBlenderProp(self, propData):
        # Load prop
        propLibrary = self.getPropLibrary(propData.libraryName)
        prop = propLibrary.getProp(propData.name, propData.groupName)
        propOB = prop.mainObject.copy() # We want to use a copy of the prop object
        
        # Assign data
        propOB.name = f"{propData.name}_{propData.ID}"
        propOB.location = propData.position
        propOB.rotation_mode = "XYZ"
        propRotation = propData.rotation
        if propRotation == None:
            propRotation = (0.0, 0.0, 0.0)
        propOB.rotation_euler = propRotation
        propScale = propData.scale
        if propScale == None:
            propScale = (1.0, 1.0, 1.0)
        propOB.scale = propScale

        # Lighting info
        if self.import_lightmapdata:
            lightingMapObject = None
            for mapObject in self.lightmapData.mapObjects:
                if mapObject.index == propData.ID:
                    lightingMapObject = mapObject
                    break
            if lightingMapObject != None:
                #XXX: do something with lightingMapObject.recieveShadows??
                propOB.visible_shadow = lightingMapObject.castShadows

        # Material
        ma = self.materials[propData.materialID]
        if len(propOB.data.materials) != 0:
            # Create a duplicate mesh object if it needs a different material, XXX: could probably cache these to reuse datablocks
            if propOB.data.materials[0] != ma:
                propOB.data = propOB.data.copy()
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
            # Create object
            ob = bpy.data.objects.new("collisionPlane", self.collisionPlaneMesh)
            ob.location = collisionPlane.position
            ob.rotation_mode = "XYZ"
            ob.rotation_euler = collisionPlane.rotation
            ob.scale = (collisionPlane.width*0.5, collisionPlane.length*0.5, 1.0) # Unsure why they double the width and length, could be because of central origin?

            objects.append(ob)

        return objects

    def createBlenderCollisionBoxes(self, collisionBoxes):
        objects = []
        for collisionBox in collisionBoxes:
            # Create object
            ob = bpy.data.objects.new("collisionBox", self.collisionBoxMesh)
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
        ob.empty_display_size = 100 # The map will be at 100x scale so it's a good idea to match that here
        ob.location = spawnPointData.position
        ob.rotation_mode = "XYZ"
        ob.rotation_euler = spawnPointData.rotation
        
        return ob
    
    def createBlenderMaterial(self, materialData):
        ma = bpy.data.materials.new(f"{materialData.ID}_{materialData.name}")

        # Shader specific logic
        if materialData.shader == "TankiOnline/SingleTextureShader" or materialData.shader == "TankiOnline/SingleTextureShaderWinter":
            bsdf = PrincipledBSDFWrapper(ma, is_readonly=False, use_nodes=True)
            bsdf.roughness_set(1.0)
            bsdf.ior_set(1.0)

            # Try load texture
            textureParameter = materialData.textureParameters[0]
            texture = self.tryLoadTexture(textureParameter.textureName, textureParameter.libraryName)

            addImageTextureToMaterial(texture, ma.node_tree)
        elif materialData.shader == "TankiOnline/SpriteShader":
            bsdf = PrincipledBSDFWrapper(ma, is_readonly=False, use_nodes=True)
            bsdf.roughness_set(1.0)
            bsdf.ior_set(1.0)

            # Try load texture
            textureParameter = materialData.textureParameters[0]
            texture = self.tryLoadTexture(textureParameter.textureName, textureParameter.libraryName)

            addImageTextureToMaterial(texture, ma.node_tree, linkAlpha=True)
        elif materialData.shader == "TankiOnline/Terrain":
            # XXX: still need to figure out how to do the terrain properly, all manual attempts have yielded mixed results
            bsdf = PrincipledBSDFWrapper(ma, is_readonly=False, use_nodes=True)
            bsdf.roughness_set(1.0)
            bsdf.ior_set(1.0)
            bsdf.base_color_set((0.0, 0.0, 0.0))
        else:
            pass # Unknown shader

        return ma

class PropLibrary:
    propGroups = {}
    def __init__(self, directory):
        self.directory = directory
        self.libraryInfo = {}

        # Load library info
        with open(f"{self.directory}/library.json", "r") as file: self.libraryInfo = load(file)
        print(f"Loaded prop library: " + self.libraryInfo["name"])

    def getProp(self, propName, groupName):
        # Create the prop group if it's not already loaded
        if not groupName in self.propGroups:
            self.propGroups[groupName] = {}
        
        # Load the prop if it's not already loaded
        if not propName in self.propGroups[groupName]:
            # Find the prop group
            groupInfo = None
            for group in self.libraryInfo["groups"]:
                if group["name"] == groupName:
                    groupInfo = group
                    break
            if groupInfo == None:
                raise RuntimeError(f"Unable to find prop group with name {groupName} in " + self.libraryInfo["name"])
            
            # Find the prop
            propInfo = None
            for prop in groupInfo["props"]:
                if prop["name"] == propName:
                    propInfo = prop
                    break
            if propInfo == None:
                raise RuntimeError(f"Unable to find prop with name {propName} in {groupName} from " + self.libraryInfo["name"])
            
            # Create the prop
            prop = Prop()
            meshInfo = propInfo["mesh"]
            spriteInfo = propInfo["sprite"]
            if meshInfo != None:
                modelPath = f"{self.directory}/" + meshInfo["file"]
                prop.loadModel(modelPath)
            elif spriteInfo != None:
                prop.loadSprite(propInfo)
            else:
                #XXX: Uhhhhhh, empty prop?
                pass
            self.propGroups[groupName][propName] = prop
        
        return self.propGroups[groupName][propName]

    def getTexture(self, textureName):
        im = load_image(textureName, self.directory)
        return im

class Prop:
    def __init__(self):
        self.objects = []
        self.mainObject = None

    def loadModel(self, modelPath):
        fileExtension = modelPath.split(".")[-1]
        if fileExtension == "a3d":
            modelData = A3D()
            with open(modelPath, "rb") as file: modelData.read(file)

            # Import the model
            modelImporter = A3DBlenderImporter(modelData, None, reset_empty_transform=False, try_import_textures=False)
            self.objects = modelImporter.importData()
        elif fileExtension == "3ds":
            bpy.ops.import_scene.max3ds(filepath=modelPath, use_apply_transform=False)
            for ob in bpy.context.selectable_objects:
                # The imported objects are added to the active collection, remove them
                bpy.context.collection.objects.unlink(ob)
                
                # Correct the origin XXX: this does not work for all cases, investigate more
                ob.animation_data_clear()
                x, y, z = -ob.location.x, -ob.location.y, -ob.location.z
                objectOrigin = Matrix.Translation((x, y, z))
                ob.data.transform(objectOrigin)
                ob.location = (0.0, 0.0, 0.0)

                self.objects.append(ob)
        else:
            raise RuntimeError(f"Unknown model file extension: {fileExtension}")
        
        # Identify the main parent object
        for ob in self.objects:
            if ob.parent == None: self.mainObject = ob
        if self.mainObject == None:
            raise RuntimeError(f"Unable to find the parent object for: {modelPath}")

    def loadSprite(self, propInfo):
        spriteInfo = propInfo["sprite"]

        # Create a plane we can use for the sprite
        me = bpy.data.meshes.new(propInfo["name"])

        # bm = bmesh.new()
        # bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=spriteInfo["scale"]*100)
        # bm.to_mesh(me)
        # bm.free()

        ob = bpy.data.objects.new(me.name, me)

        # Assign data
        ob.scale = (spriteInfo["width"], 1.0, spriteInfo["height"]) #XXX: this should involve spriteInfo["scale"] probably?
        spriteOrigin = Matrix.Translation((0.0, spriteInfo["originY"], 0.0))
        me.transform(spriteOrigin)

        # Finalise
        self.objects.append(ob)
        self.mainObject = ob
