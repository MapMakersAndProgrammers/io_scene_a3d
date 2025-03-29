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

from .A3D import A3D
from .A3DBlenderImporter import A3DBlenderImporter

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


class BattleMapBlenderImporter:
    # Allows subsequent map loads to be faster
    libraryCache = {}

    def __init__(self, mapData, propLibrarySourcePath):
        self.mapData = mapData
        self.propLibrarySourcePath = propLibrarySourcePath

    def importData(self):
        print("Importing BattleMap data into blender")

        # Load props
        propObjects = []
        for propData in self.mapData.staticGeometry:
            ob = self.getBlenderProp(propData)
            propObjects.append(ob)
        
        return propObjects

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
        
        return propOB