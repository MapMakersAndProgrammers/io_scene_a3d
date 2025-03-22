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
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper

from .A3D import A3D
from .A3DBlenderImporter import A3DBlenderImporter

'''
Operators
'''
class ImportA3D(Operator, ImportHelper):
    bl_idname = "import_scene.alternativa"
    bl_label = "Import A3D"
    bl_description = "Import an A3D model"
    bl_options = {'PRESET', 'UNDO'}

    filter_glob: StringProperty(default="*.a3d", options={'HIDDEN'})
    directory: StringProperty(subtype='DIR_PATH', options={'HIDDEN'})

    # User options
    create_collection: BoolProperty(name="Create collection", description="Create a collection to hold all the model objects", default=False)
    try_import_textures: BoolProperty(name="Search for textures", description="Automatically search for lightmap, track and wheel textures and attempt to apply them", default=True)
    reset_empty_transform: BoolProperty(name="Reset empty transforms", description="Reset rotation and scale if it is set to 0, more useful for version 2 models like props", default=True)

    def draw(self, context):
        import_panel_options(self.layout, self)

    def invoke(self, context, event):
        return ImportHelper.invoke(self, context, event)

    def execute(self, context):
        filepath = self.filepath
        
        # Read the file
        print(f"Reading A3D data from {filepath}")
        modelData = A3D()
        with open(filepath, "rb") as file:
            modelData.read(file)
        
        # Import data into blender
        modelImporter = A3DBlenderImporter(modelData, self.directory, self.create_collection, self.reset_empty_transform, self.try_import_textures)
        modelImporter.importData()

        return {"FINISHED"}

'''
Menu
'''
def import_panel_options(layout, operator):
    header, body = layout.panel("alternativa_import_options", default_closed=False)
    header.label(text="Options")
    if body:
        body.prop(operator, "create_collection")
        body.prop(operator, "try_import_textures")
        body.prop(operator, "reset_empty_transform")

def menu_func_import_a3d(self, context):
    self.layout.operator(ImportA3D.bl_idname, text="Alternativa3D HTML5 (.a3d)")

'''
Registration
'''
classes = [
    ImportA3D
]

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_a3d)

def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_a3d)

if __name__ == "__main__":
    register()