import bpy
import mathutils
import numpy as np

object = bpy.context.active_object
bones = object.parent.data.bones

vertices = object.data.vertices

boneCount = len(bones)
vicinanze = np.zeros( (boneCount, boneCount) )

bonesIndeces = {}
for i in range(boneCount):
    bonesIndeces[bones[i].name] = i

def vicinanza( j, k ):
    massimo = 0
    for i in bones:
       massimo = max (
          massimo,
          vicinanza_con_figli( i , k ) * vicinanza_con_figli( i , j ) 
       )
    return massimo;


def vicinanza_con_figli( j , k ):
    root = bones[0]
    result = 1
    while 1:
        if j==k:
            return result

        if k == root:
            return 0

        result *= 0.5;
        k = k.parent;

def getVertexWeightString(vertex):
    wList = ""
    for w in vertex.groups:
        wList += object.vertex_groups[w.group].name + ": " + str(w.weight) + "\t"
    return wList + "\n"

def boneNameStrings(bones):
    t = ""
    for b in bones:
        t += b.name + "\t"
    return t + "\n"

def printVertInfo(i):
    vertex = vertices[i]s
    print("Vertice ", i, " posizione=", vertex.co)
    print("pesi=", getVertexWeightString(vertex))

#MAIN
for j in range(boneCount):
    for k in range(boneCount):
        vicinanze[j][k] = vicinanza( bones[j], bones[k] )

printVertInfo(4672)

for v in vertices:
    ossaVert = []
    weights = []
    for w in v.groups:
        boneName = object.vertex_groups[w.group].namess
        ossaVert.append(bones[boneName])
        weights.append(w.weight)
    
    if v.index == 4672:
        print(boneNameStrings(ossaVert))
        print(weights, "\n")
        
    dist_combin_per_osso = []
    for b in bones:
        vicOssoVert = 0
        if b not in ossaVert:
            for j in range( len(ossaVert) ):
                vicOssoVert += vicinanze[ bonesIndeces[ossaVert[j].name] ][ bonesIndeces[b.name] ] * weights[j]
            dist_combin_per_osso.append(vicOssoVert)
        else:
            dist_combin_per_osso.append(1)
    
    newOssaVert = [0,0,0,0]
    maxes = [0,0,0,0]
    for i in range( boneCount ):
        if maxes[0] < dist_combin_per_osso[i]:
            maxes[0] = dist_combin_per_osso[i]
            newOssaVert[0] = bones[i]
        elif maxes[1] < dist_combin_per_osso[i]:
            maxes[1] = dist_combin_per_osso[i]
            newOssaVert[1] = bones[i]
        elif maxes[2] < dist_combin_per_osso[i]:
            maxes[2] = dist_combin_per_osso[i]
            newOssaVert[2] = bones[i]
        elif maxes[3] < dist_combin_per_osso[i]:
            maxes[3] = dist_combin_per_osso[i]
            newOssaVert[3] = bones[i]
    
    if v.index == 4672:
        print(boneNameStrings(newOssaVert))
        
    for bone in ossaVert:
        if bone not in newOssaVert:
            object.vertex_groups[bone.name].remove([v.index])
    
    for bone in newOssaVert:
        if bone not in ossaVert:
            object.vertex_groups[bone.name].add([v.index], 0.0, 'REPLACE')

print()        
printVertInfo(4672)
                
print("\n", vicinanze)