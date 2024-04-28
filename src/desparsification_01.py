import bpy
import mathutils
import copy
import bmesh

class sculptWeights(bpy.types.Operator):
    bl_idname = "object.sculpt_weights"
    bl_label = "Sculpting strokes to weights"
    
    mousePressed = False
    startingVerts = []
    startingWeights = []
    diffVerts = []

    def __init__(self):
        print("Start")

    def __del__(self):
        print("End")

    def execute(self, context):
        return {'FINISHED'}

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.mousePressed= True
            print("PRESSED!")
            
            #Prendi la posizione di tutti i vertici
            for v in bpy.context.active_object.data.vertices:
                self.startingVerts.append(copy.deepcopy(v.co))
                

        if event.value == 'RELEASE' and self.mousePressed:
            self.mousePressed= False
            pen = bpy.context.workspace.tools.from_space_view3d_mode(bpy.context.mode)
            print('Released!')

            if pen.idname[0:13] == 'builtin_brush':
                print(pen.idname, " E' un pennello!")
            
            self.printVertInfo(11323)
            self.startingVerts = []
            
        if event.type in {'RIGHTMOUSE', 'ESC'}:  # Cancel
            bpy.context.scene.tool_settings.use_auto_normalize = True
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        #...Check when not to re-assign everything...
        self.desparsificate()
        
        bpy.contelalize = False

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    #__methods__
    def desparsificate(self):
        #get active object
        meshModel = bpy.context.active_object
        
        self.printVertInfo(506)
        
        #for every vertex
        count = 0
        for i, v in enumerate(meshModel.data.vertices):
            #append empty dictonary to array
            self.startingWeights.append({})
            
            #get known wheights
            for w in v.groups:
                self.startingWeights[i][meshModel.vertex_groups[w.group].name] = w.weight
            
            #REMOVE excess bone weights
            if len(self.startingWeights[i]) > 4:
                self.startingWeights[i] = self.removeBoneWeights(self.startingWeights[i], i)
        
        
        #ADD
        self.addBoneWeights()
        
        self.assignWeights()
        self.printVertInfo(506)
        
        self.startingWeights = []
        return
    
    def addBoneWeights(self):
        meshModel = bpy.context.active_object
        #BMesh representation
        bMeshModel = bmesh.new()
        bMeshModel.from_mesh(meshModel.data)
        bones = bpy.context.active_object.parent.data.bones
        assigned = True
        while assigned:
            assigned = False
            for tri in bMeshModel.faces:
                for edge in tri.edges:
                    aIndex= edge.verts[0].index
                    bIndex= edge.verts[1].index
                    aWeights= self.startingWeights[aIndex]
                    bWeights= self.startingWeights[bIndex]
                    #b contagia a
                    if len(aWeights) < 4:
                        bOrdered = self.orderDict(bWeights)
                        for boneName in bOrdered:
                            distFromBone = (-1)*self.getVectDistance(meshModel.data.vertices[aIndex].co, bones[boneName].head_local)
                            if boneName not in aWeights.keys():
                                self.startingWeights[aIndex][boneName] = distFromBone
                                assigned = True
                                break
                            else:
                                for bw, name in enumerate(aWeights):
                                    if bw < distFromBone:
                                        self.startingWeights[aIndex].pop(name)
                                        self.startingWeights[aIndex][boneName] = distFromBone
                                        break
                    #a contagia b
                    if len(bWeights) < 4:
                        aOrdered = self.orderDict(aWeights)
                        for boneName in aOrdered:
                            distFromBone = (-1)*self.getVectDistance(meshModel.data.vertices[bIndex].co, bones[boneName].head_local)
                            if boneName not in bWeights.keys():
                                self.startingWeights[bIndex][boneName] = distFromBone
                                assigned = True
                                break
                            else:
                                for bw, name in enumerate(aWeights):
                                    if bw < distFromBone:
                                        self.startingWeights[aIndex].pop(name)
                                        self.startingWeights[aIndex][boneName] = distFromBone
                                        break
        
        #zero all negative weights
        for vert in self.startingWeights:
            for boneName in vert:
                if vert[boneName] < 0.0:
                    vert[boneName] = 0.0
        bMeshModel.free()
        return
    
    def printVertInfo(self, i):
        vertex = bpy.context.active_object.data.vertices[i]
        print("Vertice ", i, " posizione=", vertex.co)
        print("pesi=", self.getVertexWeightList(vertex))
        return
        
    def orderDict(self, dictionary):
        ordDict = {k: v for k, v in sorted(dictionary.items(), key=lambda item: item[1], reverse=True)}
        return ordDict
    
    def assignWeights(self):
        #assign new expanded or contrapted weights
        for i, vWeights in enumerate(self.startingWeights):
            for vGroupName in vWeights:
                bpy.context.active_object.vertex_groups[vGroupName].add([i], vWeights[vGroupName] ,'REPLACE')
        bpy.ops.object.vertex_group_normalize_all()
    
    #REMOVE
    def removeBoneWeights(self, wDict, vertIndex):
        wDict = self.orderDict(wDict)
        #Remove weights directly on the blender mesh data structure
        for i, vGroupName in enumerate(wDict):
            if i > 3:
                bpy.context.active_object.vertex_groups[vGroupName].remove([vertIndex])
        
        #save the weights on the script data strucure
        while (len(wDict)>4):
            wDict.popitem()
        return wDict
    
    #GETTERS
    def getVertexWeightList(self, vertex):
        wList = []
        for w in vertex.groups:
            wList.append((bpy.context.active_object.vertex_groups[w.group].name, w.weight))
        return wList
    
    def getVectDistance(self, vector1, vector2):
        distVect = vector1 - vector2
        return round(distVect.magnitude * 1000) / 1000

bpy.utils.register_class(sculptWeights)

# test call
bpy.ops.object.sculpt_weights('INVOKE_DEFAULT')