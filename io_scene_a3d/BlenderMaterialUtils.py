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

'''
Functions
'''
def addImageTextureToMaterial(image, node_tree, linkAlpha=False):
    nodes = node_tree.nodes
    links = node_tree.links
    
    # Check if this material has already been edited
    if len(nodes) > 2:
        return

    # Create nodes
    bsdfNode = nodes.get("Principled BSDF")
    textureNode = nodes.new(type="ShaderNodeTexImage")
    links.new(textureNode.outputs["Color"], bsdfNode.inputs["Base Color"])
    if linkAlpha:
        links.new(textureNode.outputs["Alpha"], bsdfNode.inputs["Alpha"])

    # Apply image
    if image != None: textureNode.image = image

def decodeIntColorToTuple(intColor):
    # Fromat is argb
    a = (intColor >> 24) & 255
    r = (intColor >> 16) & 255
    g = (intColor >> 8) & 255
    b = intColor & 255
    
    return (r/255, g/255, b/255)