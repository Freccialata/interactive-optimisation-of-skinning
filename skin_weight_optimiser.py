import bpy
import mathutils
import copy
import math

class lss(bpy.types.Operator):
    bl_idname = "object.lss"
    bl_label = "Sculpting strokes to weights"
    
    def __init__(self):
        self.meshObject = bpy.context.active_object
        self.armatureObject = bpy.context.active_object.parent
        self.meshVertices = bpy.context.active_object.data.vertices
        self.vertsBeforeEdit = []
        
        self.mousePressed = False
        print("Start")
        

    def __del__(self):
        print("End")

    def execute(self, context):
        return {'FINISHED'}

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.mousePressed = True
            print("PRESSED!")
            
            for v in self.meshVertices:
                self.vertsBeforeEdit.append( copy.deepcopy(v.co) )

        if event.value == 'RELEASE' and self.mousePressed:
            self.mousePressed = False
            print('Released!')
            
            #Variables for debugging
            verticiControllati = 0
            erroreMax = 0
            nDirezioniGiuste = 0
            
            #Write to file original rest vertices----------------------------------------------------
            self.dumpXYZ("rest_orig", self.vertsBeforeEdit)
            
            vertsTemp = []
            for i, v in enumerate(self.meshVertices):
                vertsTemp.append( v.co.copy() )
            
            #Write to file edited rest vertices----------------------------------------------------
            self.dumpXYZ("rest_edited", vertsTemp)
            
            vertsTemp = []
            vertsTemp_pre = []
            
            vTempNewW = []
            vTempNewW_norm = []
            
            for i, v in enumerate(self.meshVertices):
                #get original vertex position an position after brush stroke
                oldPos_inRest = self.vertsBeforeEdit[i].copy()
                newPos_inRest = v.co.copy()
                
                #get starting bone vertex weights (old weights)
                oldWeights = self.getAssignedWeights(v)
                
                #get vertex bone matrices
                #get vertex pose bone matrices
                #get final transformation matrix interpolated with old weights
                global_toRest_matrices = []
                global_toPose_matrices = []
                final_fromRest_toPose_matrices = []
                final_interp_fromRest_toPose =  mathutils.Matrix(( (0,0,0,0), (0,0,0,0), (0,0,0,0), (0,0,0,0) ))
                
                for w in v.groups:
                    boneName = self.meshObject.vertex_groups[w.group].name
                    
                    bone = self.armatureObject.data.bones[boneName]
                    global_toRest = bone.matrix_local
                    global_toRest_matrices.append( global_toRest.copy() )
                    
                    poseBone = self.armatureObject.pose.bones[boneName]
                    global_toPose = poseBone.matrix
                    global_toPose_matrices.append( global_toPose.copy() )
                    
                    final_fromRest_toPose = global_toPose @ ( global_toRest.inverted() )
                    final_fromRest_toPose_matrices.append( final_fromRest_toPose )
                    
                    final_interp_fromRest_toPose += w.weight * final_fromRest_toPose
                
                #get new position in current pose---------------------------------
                oldPos_inPose = final_interp_fromRest_toPose @ oldPos_inRest
                newPos_inPose = final_interp_fromRest_toPose @ newPos_inRest
                
                #Make lists to file export-----------------------------------------------------------
                vertsTemp_pre.append(oldPos_inPose)
                vertsTemp.append(newPos_inPose)
                
                #CHECK for change-------------------------------------------------------------------------------------
                if (newPos_inRest-oldPos_inRest).magnitude != 0:
                    verticiControllati += 1
                    
                    #resetVertexPosition
                    v.co = oldPos_inRest
                    
                    #make destination vertices---------------------------------------------------------------------------------
                    p = self.make_p_vector(final_fromRest_toPose_matrices, oldPos_inRest)
                    
                    #linear problem composition--------------------------------------------------------------------------------
                    Tmatrix = mathutils.Matrix((
                        (p[0]-p[3]),
                        (p[1]-p[3]),
                        (p[2]-p[3])
                    ))
                    
                    Tmatrix.transpose()
                    
                    target_minus_p3 = newPos_inPose - p[3]
                    
                    print("\nPesi iniziali:", oldWeights, " vertice", i, "\n")
                    self.printVertexBones(v)
                    
                    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
                    #solve linear system-----------------------------------------------------------------------------------
                    #Static variables for Quadratic class
                    Quadratic.oldW = oldWeights #3d Vector
                    Quadratic.target_pos = newPos_inPose #3d Vector
                    Quadratic.p = p #four 3d Vectors
                    
                    #QUADRATIC 0
                    quadr0 = Quadratic(
                        (Tmatrix.transposed() @ Tmatrix),
                        (-2*Tmatrix.transposed() @ target_minus_p3),
                        (target_minus_p3 @ target_minus_p3) )
                    
                    #QUADRATIC 1
                    k = 0.05
                    oldW_3d = oldWeights.to_3d() #row vector 3d
                    quadr1 = Quadratic(
                        ( k * k * mathutils.Matrix.Identity(3) ),
                        (-2 * k * k * oldW_3d),
                        (k * k * oldW_3d @ oldW_3d) )
                    
                    #QUADRATIC 2
                    ones = mathutils.Matrix( ((1,1,1), (1,1,1), (1,1,1)) )
                    w3_3d = mathutils.Vector( ( (oldWeights.w - 1), (oldWeights.w - 1), (oldWeights.w - 1) ) )
                    quadr2 = Quadratic(
                        ( k * k * ones ),
                        ( 2 * k * k * w3_3d),
                        ( k * k * (oldWeights.w - 1) * (oldWeights.w - 1) ) )

                    #QUADRATIC 4
                    quadr3 = quadr0 + quadr1 + quadr2
                    
                    #RESTULT quadr 3
                    quadr3.get_minimum()
                    newW = quadr3.to_4d_weights(quadr3.w_min)
                    
                    #NON NORMALIZED-------------------------------------------------------------------------------------------------
                
                    nonNormWeights = newW.copy()
                    
                    #inverse check, with new weights------------------------------------------------------------------------
                    solvedPosition = self.interpolate_transform(oldPos_inRest, final_fromRest_toPose_matrices, nonNormWeights)

                    #assign new solved weights------------------------------------------------------------------------------
                    #self.assignNewWeights(v, nonNormWeights)
                    
                    #check assignment--------------------------------------------------------------------
                    assignedW = self.getAssignedWeights(v)

                    #get position with assigned weights----------------------------------------------------------
                    calcPos_inPose = self.interp_p_weights(p, assignedW)
                    
                    #fill array write to file-----------------------------------------------------
                    vTempNewW.append(solvedPosition)
                    
                    #print--------------------------------------------------------------------------------------
                    self.printVertexInfo("Informazioni sul vertice NON norm:", nonNormWeights, assignedW, solvedPosition, calcPos_inPose)
                    self.compare("\nTest rispetto a newPos_inPose", solvedPosition, newPos_inPose)
                    
                    #NORMALIZED-----------------------------------------------------------------------------------------

                    h = 1
                    h *= h
                    normWeights = newW.copy()
                    epsilon = 0.000000012
                    
                    #QUADRATIC 5 (normalizer)
                    ones = mathutils.Matrix( ( (1,1,1), (1,1,1), (1,1,1) ) )
                    Ax = mathutils.Matrix( ( (1,0,0), (0,0,0), (0,0,0) ) )
                    Ay = mathutils.Matrix( ( (0,0,0), (0,1,0), (0,0,0) ) )           
                    Az = mathutils.Matrix( ( (0,0,0), (0,0,0), (0,0,1) ) )
                    zeros = mathutils.Vector()
                    
                    quadr5 = quadr3
                    
                    if normWeights.x < -epsilon:
                        quadr5 += Quadratic(Ax*h, zeros, 0)
                        quadr5.get_minimum()
                        normWeights = quadr5.to_4d_weights(quadr5.w_min)
                        print("\nQuadratica ad x:", quadr5)
                    
                    if normWeights.y < -epsilon:
                        quadr5 += Quadratic(Ay*h, zeros, 0)
                        quadr5.get_minimum()
                        normWeights = quadr5.to_4d_weights(quadr5.w_min)
                        print("\nQuadratica ad y:", quadr5)
                    
                    if normWeights.z < -epsilon:
                        quadr5 += Quadratic(Az*h, zeros, 0)
                        quadr5.get_minimum()
                        normWeights = quadr5.to_4d_weights(quadr5.w_min)
                        print("\nQuadratica a z:", quadr5)
                    
                    if normWeights.w < -epsilon:
                        quadr5 += Quadratic(ones*h, mathutils.Vector( (-2,-2,-2) )*h, 1*h)
                        quadr5.get_minimum()
                        normWeights = quadr5.to_4d_weights(quadr5.w_min)
                        print("\nQuadratica passa per w")
                    
                    print("\nQuadratica sommata:", quadr5)
                    normWeights = self.normalizeVector(normWeights)

                    #inverse check, with new weights------------------------------------------------------------------------
                    solvedPosition = self.interpolate_transform(oldPos_inRest, final_fromRest_toPose_matrices, normWeights)

                    #assign new solved weights------------------------------------------------------------------------------
                    self.assignNewWeights(v, normWeights)
                    
                    #check assignment--------------------------------------------------------------------
                    assignedW = self.getAssignedWeights(v)
                    self.printVertexBones(v)

                    #get position with assigned weights----------------------------------------------------------
                    calcPos_inPose = self.interp_p_weights(p, assignedW)
                    
                    #fill array write to file-----------------------------------------------------
                    vTempNewW_norm.append(solvedPosition)
                    
                    #print--------------------------------------------------------------------------------------
                    self.printVertexInfo("Informazioni sul vertice NORM:", normWeights, assignedW, solvedPosition, calcPos_inPose)
                    
                    #errors and one print---------------------------------------------------------------------------
                    errore = self.compare("\nTest rispetto a newPos_inPose", solvedPosition, newPos_inPose)
                    
                    #:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
                    
                    if erroreMax < errore.length:
                        erroreMax = errore.length
                    
                    #check angle between newPos and calculated pos------------------------------------------
                    cosine = self.cosine_newPos_caluculatedPos(calcPos_inPose, newPos_inPose, oldPos_inPose)
                    
                    if cosine > 0.0:
                        nDirezioniGiuste += 1
                    
                    print("_______________________________________________________________________________________________________")
                
                else:
                    #Make lists to file export of unchanged vertices-------------------------------------------------------------
                    vTempNewW.append(oldPos_inPose)
                    vTempNewW_norm.append(newPos_inPose)
            #end for each vertex------------------
            
            #print del calcolo degli errori-----------------------------------------------------------------------------------------
            if verticiControllati>0:
                #errore massimo
                print("\nNumero vertici controllati:", verticiControllati, "\nErrore massimo:", erroreMax)
                
                #numero direzioni simili
                rapp = nDirezioniGiuste/verticiControllati
                rapp = round(rapp * 100)
                print("Numero direzioni simili:", nDirezioniGiuste, "| Percentuale:", str(rapp) + "%\n")
            
            #Write to file posed vertices----------------------------------------------------------
            #self.dumpXYZ("posed_orig", vertsTemp_pre)
            #self.dumpXYZ("posed_edited", vertsTemp)
            self.dumpTransfObject("posed_orig", vertsTemp_pre)
            self.dumpTransfObject("posed_edited", vertsTemp)
            
            #Write to file posed verts new weights-------------------------------------------------
            #self.dumpXYZ("posed_newWeights", vTempNewW)
            #self.dumpXYZ("posed_newWeightsRenormalized", vTempNewW_norm)
            self.dumpTransfObject("posed_newWeights", vTempNewW)
            self.dumpTransfObject("posed_newWeightsRenormalized", vTempNewW_norm)
            
            print("==========================================================================================")
            
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            #bpy.ops.outliner.orphans_purge()
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        
        bpy.contelalize = False
        
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    #__methods__
    def normalizeVector(self, vector):
        min = 0
        max = 1
        for i in range(4):
            if vector[i] < min:
                min = vector[i]
            if vector[i] > max:
                max = vector[i]
            
        sum = 0
        for i in range(4):
            vector[i] += -min
            vector[i] /= max - min
            sum += vector[i]
            
        for i in range(4):
            vector[i] /= sum
            
        return vector
    
    #Calculate distance between vectors to check if they are close to eachother
    def compare(self, label, a, b):
        print(label + ":\n\t", a, "-", b, "=", a-b)
        return a-b
    
    def make_p_vector(self, final_fromRest_toPose_matrices, oldPos_inRest):
        p = []
        for FinalToPoseMatrix in final_fromRest_toPose_matrices:
            p.append(FinalToPoseMatrix @ oldPos_inRest)
        return p
    
    #Interpolate a matrix manually with newfound weights to predict what Blender should do (same as interp_p_weights)
    def interpolate_transform(self, vertexCoord_rest, final_fromRest_toPose_matrices, newW):
        final_interp_fromRest_toPose = mathutils.Matrix(( (0,0,0,0), (0,0,0,0), (0,0,0,0), (0,0,0,0) ))
        for j in range(4):
            final_interp_fromRest_toPose += newW[j] * final_fromRest_toPose_matrices[j]
        return final_interp_fromRest_toPose @ vertexCoord_rest
    
    #Interpolate p vector with newfound weights to predict w hat Blender should do (same as interpolate_transform)
    def interp_p_weights(self, p, weight):
        return weight.x * p[0] + weight.y * p[1] + weight.z * p[2] + weight.w * p[3]
    
    #Assign newfound weights to Blender's data structure
    def assignNewWeights(self, vertex, newWeights):
        j = 0
        for w in vertex.groups:
            boneName = self.meshObject.vertex_groups[w.group].name
            self.meshObject.vertex_groups[boneName].add([vertex.index], newWeights[j], 'REPLACE')
            j += 1

    #Get weights from Blender's data structure of a single vertex
    def getAssignedWeights(self, vertex):
        assignWeights = []
        for w in vertex.groups:
            boneName = bpy.context.active_object.vertex_groups[w.group].name
            assignWeights.append(w.weight)
        assignWeights = mathutils.Vector(assignWeights)
        return assignWeights
       
    def printVertexBones(self, vertex):
        t = "Ossa: "
        for w in vertex.groups:
            boneName = bpy.context.active_object.vertex_groups[w.group].name
            t += boneName + ", "
        print(t, "| Indice: " + str(vertex.index) )
       
    #Print information about the vertex to help debugging
    def printVertexInfo(self, label, wBeforeAssignment, wAfterAssignment, solvedPosition, calc_pos):
        print("\n" + label)
        print("Pesi prima dell'assegnamento", wBeforeAssignment, "\nPesi dopo l'assegnamento", wAfterAssignment)
        print("\nPosizione solved pre-assegn:", solvedPosition, "\nPosizione calc post-assegn", calc_pos)
    
    #Check angle between newPos and calculated pos starting from original position with old weights
    def cosine_newPos_caluculatedPos(self, calcPos_inPose, newPos_inPose, oldPos_inPose):
        disToNewPos = oldPos_inPose - newPos_inPose
        disToCalcPos = oldPos_inPose - calcPos_inPose
        disToNewPos.normalize()
        disToCalcPos.normalize()
        print("\nCOS tra vettori 'displacement':", disToNewPos @ disToCalcPos )
        return disToNewPos @ disToCalcPos
    
    def squareDistance(self, vect1, vect2):
        dist = vect1 - vect2
        return dist @ dist
    
    #write to file and dump methods
    def dumpXYZ(self, fileName, vector):
        #self.commentDumpXYZ(fileName, vector)
        return

    def commentDumpXYZ(self, fileName, vector):
        f = open("D:\\blenderTest\\" + fileName + ".xyz", "a")
        for v in vector:
            f.write(str(v.x) + " " + str(v.y) + " " + str(v.z) + "\n")
        f.close()
        
    def dumpTransfObject(self, objectName, newVertices):
        #self.commentDumpTransfObject(objectName, newVertices)
        return
        
    def commentDumpTransfObject(self, objectName, newVertices):
        mesh = self.meshObject.data.copy()
        meshVerts = mesh.vertices
        for j in range( len(newVertices) ):
            meshVerts[j].co = newVertices[j]
        
        mesh.update()
        newObject = bpy.data.objects.new(objectName, mesh)
        collection = bpy.data.collections["Collection"].objects
        collection.link(newObject)

class Quadratic():
    #constructor
    def __init__(self, A, b, c):
        self.A = A #3x3 Matrix
        self.b = b #3d Vector
        self.c = c #Scalar
        
        self.w_min = False

    #class specific methods
    def __str__(self):
        t = "Matrice A:\n\t" + str(self.A) + "\nVettore b = " + str(self.b) + " | scalare c = " + str(self.c)
        if self.w_min:
            t += "\nMinimum: " + str(self.w_min)
        else:
            t += "\nMinimum non yet calculated or matrix has no inverse."
        return t + "\n"
    
    def evaluate(self, w):
        return w @ self.A @ w + self.b @ w + self.c
    
    def evaluate_quadratic_vector(self, w):
        return self.A @ w - self.b
    
    def get_minimum(self):
        self.w_min = (-1/2) * self.A.inverted() @ self.b

    def __add__(self, quadratic):
        A = self.A + quadratic.A
        b = self.b + quadratic.b
        c = self.c + quadratic.c
        return Quadratic(A, b, c)

    #some useful methods
    def to_4d_weights(self, w):
        newW = w.copy()
        newW.resize_4d()
        newW.w = 1 - (w.x + w.y + w.z)
        return newW

    #checking methods
    def isMinimising(self, min_weights):
        inverse = self.evaluate(min_weights.xyz)
        print("Risultato inverso da minimizzazione:", inverse)
        
        arbW = mathutils.Vector( (3, 9, 1, 11) )
        test0 = self.evaluate(arbW.xyz)
        test1 = self.evaluate(arbW.yzw)
        
        r = 0.0003
        test2 = self.evaluate( r * arbW.xyz )
        test3 = self.evaluate( (1 - r) * arbW.xyz )
        
        test4 = self.evaluate( min_weights.xyz * r )
        
        copy_min = min_weights.copy()
        for j in range(3):
            copy_min[j] += r
        test5 = self.evaluate(copy_min.xyz)
        
        results = (inverse, test0, test1, test2, test3, test4, test5)
        
        minim = min(results)
        
        print("Tutti i risultati:", results, "\n minimo tra vari test:", minim )
        
    
bpy.utils.register_class(lss)

# test call
bpy.ops.object.lss('INVOKE_DEFAULT')