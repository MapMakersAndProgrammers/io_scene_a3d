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
from bpy.types import Operator, OperatorFileListElement, AddonPreferences
from bpy.props import StringProperty, BoolProperty, CollectionProperty, FloatProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper

from .A3D import A3D
from .A3DBlenderImporter import A3DBlenderImporter
from .A3DBlenderExporter import A3DBlenderExporter
from .BattleMap import BattleMap
from .BattleMapBlenderImporter import BattleMapBlenderImporter
from .LightmapData import LightmapData

from os.path import isdir
from time import time

'''
Addon preferences
'''
class Preferences(AddonPreferences):
    bl_idname = __package__

    propLibrarySourcePath: StringProperty(name="Prop library source path", subtype='DIR_PATH')

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "propLibrarySourcePath")

'''
Operators
'''
class ImportA3D(Operator, ImportHelper):
    bl_idname = "import_scene.alternativa"
    bl_label = "Import A3D"
    bl_description = "Import an A3D model"
    bl_options = {'PRESET', 'UNDO'}

    filter_glob: StringProperty(default="*.a3d", options={'HIDDEN'})
    directory: StringProperty(subtype="DIR_PATH", options={'HIDDEN'})
    files: CollectionProperty(type=OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})

    # User options
    create_collection: BoolProperty(name="Create collection", description="Create a collection to hold all the model objects", default=False)
    try_import_textures: BoolProperty(name="Search for textures", description="Automatically search for lightmap, track and wheel textures and attempt to apply them", default=True)
    reset_empty_transform: BoolProperty(name="Reset empty transforms", description="Reset rotation and scale if it is set to 0, more useful for version 2 models like props", default=True)

    def draw(self, context):
        import_panel_options_a3d(self.layout, self)

    def invoke(self, context, event):
        return ImportHelper.invoke(self, context, event)

    def execute(self, context):
        importStartTime = time()

        objects = []
        for file in self.files:
            filepath = f"{self.directory}/{file.name}"
            # Read the file
            print(f"Reading A3D data from {filepath}")
            modelData = A3D()
            with open(filepath, "rb") as file:
                modelData.read(file)
        
            # Import data into blender
            modelImporter = A3DBlenderImporter(modelData, self.directory, self.reset_empty_transform, self.try_import_textures)
            objects += modelImporter.importData()

        # Link objects to collection
        collection = bpy.context.collection
        if self.create_collection:
            collection = bpy.data.collections.new("Collection")
            bpy.context.collection.children.link(collection)
        for obI, ob in enumerate(objects):
            collection.objects.link(ob)

        importEndTime = time()
        self.report({'INFO'}, f"Imported {len(objects)} objects in {importEndTime-importStartTime}s")

        return {"FINISHED"}

class ExportA3D(Operator, ExportHelper):
    bl_idname = "export_scene.alternativa"
    bl_label = "Export A3D"
    bl_description = "Export an A3D model"
    bl_options = {'PRESET', 'UNDO'}

    filter_glob: StringProperty(default="*.a3d", options={'HIDDEN'})
    filename_ext: StringProperty(default=".a3d", options={'HIDDEN'})

    a3d_version: EnumProperty(
        items=(
            ("2", "A3D2", "Version 2 files are used to store map geometry like props and simple models like drones and particle effects"),
            ("3", "A3D3", "Version 3 files are used to store tank turret and hull models")
        ),
        description="A3D file version",
        default="2",
        name="version"
    )

    def draw(self, context):
        export_panel_options_a3d(self.layout, self)

    def invoke(self, context, event):
        return ExportHelper.invoke(self, context, event)
    
    def execute(self, context):
        print(f"Exporting blender data to {self.filepath}")

        modelData = A3D()
        modelExporter = A3DBlenderExporter(modelData, bpy.context.selected_objects, version=int(self.a3d_version))
        modelExporter.exportData()

        # Write file
        with open(self.filepath, "wb") as file:
            modelData.write(file, version=int(self.a3d_version))

        return {"FINISHED"}

class ImportBattleMap(Operator, ImportHelper):
    bl_idname = "import_scene.tanki_battlemap"
    bl_label = "Import map"
    bl_description = "Import a BIN format Tanki Online map file"
    bl_options = {'PRESET', 'UNDO'}

    filter_glob: StringProperty(default="*.bin", options={'HIDDEN'})
    directory: StringProperty(subtype="DIR_PATH", options={'HIDDEN'})

    # User options
    import_static_geom: BoolProperty(name="Import static geometry", description="Static geometry includes all the visual aspects of the map", default=True)
    import_collision_geom: BoolProperty(name="Import collision geometry", description="Collision geometry defines the geometry used for collision checks and cannot normally be seen by players", default=False)
    import_spawn_points: BoolProperty(name="Import spawn points", description="Places a marker at locations where tanks can spawn", default=False)
    import_lightmapdata: BoolProperty(name="Import lighting information", description="Loads the lightmapdata file which stores information about the sun, ambient lighting and shadow settings. Only works on remaster maps.", default=True)
    map_scale_factor: FloatProperty(name="Map scale", description="Sets the map's default scale, maps and models are at a 100x scale so this allows you to directly import the map in the right size.", default=0.01, min=0.0, soft_max=1.0)

    def draw(self, context):
        import_panel_options_battlemap(self.layout, self)

    def invoke(self, context, event):
        return ImportHelper.invoke(self, context, event)
    
    def execute(self, context):
        print(f"Reading BattleMap data from {self.filepath}")
        importStartTime = time()

        # lightmapdata files only exist for remaster maps
        lightmapData = LightmapData()
        if self.import_lightmapdata:
            try:
                with open(f"{self.directory}/lightmapdata", "rb") as file: lightmapData.read(file)
            except:
                print("Couldn't open lightmapdata file, ignoring")
                self.import_lightmapdata = False

        # read map data
        mapData = BattleMap()
        with open(self.filepath, "rb") as file:
            mapData.read(file)

        # Import data into blender
        preferences = context.preferences.addons[__package__].preferences
        if not isdir(preferences.propLibrarySourcePath):
            raise RuntimeError("Please set a valid prop library folder in addon properties!")
        mapImporter = BattleMapBlenderImporter(mapData, lightmapData, preferences.propLibrarySourcePath, self.map_scale_factor, self.import_static_geom, self.import_collision_geom, self.import_spawn_points, self.import_lightmapdata)
        objects = mapImporter.importData()

        # Link objects
        collection = bpy.context.collection
        for ob in objects:
            collection.objects.link(ob)
        
        importEndTime = time()
        self.report({'INFO'}, f"Imported {len(objects)} objects in {importEndTime-importStartTime}s")

        return {"FINISHED"}

'''
Menu
'''
def import_panel_options_a3d(layout, operator):
    header, body = layout.panel("alternativa_import_options", default_closed=False)
    header.label(text="Options")
    if body:
        body.prop(operator, "create_collection")
        body.prop(operator, "try_import_textures")
        body.prop(operator, "reset_empty_transform")

def export_panel_options_a3d(layout, operator):
    header, body = layout.panel("alternativa_import_options", default_closed=False)
    header.label(text="Options")
    if body:
        body.prop(operator, "a3d_version")

def import_panel_options_battlemap(layout, operator):
    header, body = layout.panel("tanki_battlemap_import_options", default_closed=False)
    header.label(text="Options")
    if body:
        body.prop(operator, "import_static_geom")
        body.prop(operator, "import_collision_geom")
        body.prop(operator, "import_spawn_points")
        body.prop(operator, "import_lightmapdata")
        body.prop(operator, "map_scale_factor")

def menu_func_import_a3d(self, context):
    self.layout.operator(ImportA3D.bl_idname, text="Alternativa3D HTML5 (.a3d)")

def menu_func_export_a3d(self, context):
    self.layout.operator(ExportA3D.bl_idname, text="Alternativa3D HTML5 (.a3d)")

def menu_func_import_battlemap(self, context):
    self.layout.operator(ImportBattleMap.bl_idname, text="Tanki Online BattleMap (.bin)")

'''
Registration
'''
classes = [
    Preferences,
    ImportA3D,
    ExportA3D,
    ImportBattleMap
]

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_a3d)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_a3d)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_battlemap)

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_a3d)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export_a3d)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_battlemap)

if __name__ == "__main__":
    register()