'''
Copyright (C) 2014 Metalix Studios
info@metalix.co.nz
Version 1.0.0

Created by Alex Telford

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

About:
    the cmds module is designed to bring some of the functionality from Autodesk Maya python to
    Blender (maya.cmds). I originally created this so that I could make my scripts work in both
    Maya and Blender by just changing the import line.
    As a result this module has become indespensible to me and I hope you find as much use in it
    as I have.

Description:
    This module is designed to bahave 'like' maya.cmds, but due to the nature of Blender's
    object oriented and context sensitive workflow these functions will return objects.
    You can use the asString and asObject functions to convert between strings and node classes.
    asString will return a string or list of strings depending on the input.
    For example:
        if inMaya():
            selection = ls(sl=1, l=1)

        elif inBlender():
            selection = asString(ls(sl=1))

    These functions can take string and object inputs, but you will get better results when sticking
    to blender objects.
'''
try:
    import bpy

except:
    bpy = None
    print('Failed to load bpy: cmds.py')

from core.libs.types import fi, li, asList, parseArgs, isType, asFloat, OrderedDict as od
import re
import builtins
import bmesh
import threading
# depending if we are in python 2 or 3
try:
    import Queue

except:
    import queue as Queue


reAttribute = re.compile('[^A-Za-z0-9\-_]+')
global COPY_KEY_BUFFER
COPY_KEY_BUFFER = []


try:
    class NullDisplayClass(bpy.types.Operator):
        bl_idname = 'info.display_message'
        bl_label = 'DisaplyInfo'
        bl_options = set(['REGISTER'])
        report_type = bpy.props.StringProperty(default='INFO')
        report_message = bpy.props.StringProperty(default='message')
        def execute(self, context):
            self.report(set([self.report_type]), self.report_message)
            return set(['FINISHED'])

    bpy.utils.register_class(NullDisplayClass)

except:
    pass


class CONSTANTS(object):
    '''
    This class is used to store internal data to be used for conversions.
    Although it can be used outside of the functions defined here be aware that it was not it's
    intended purpose.
    if running outside of blender this module should still run, but will be missing blender content
    No documentation will be provided on this class.
    '''
    attributeConversion = dict()
    attributeConversion['locationX'] = ['translateX', 'translationX', 'positionX', 'tx', 'lx']
    attributeConversion['locationY'] = ['translateY', 'translationY', 'positionY', 'ty', 'ly']
    attributeConversion['locationZ'] = ['translateZ', 'translationZ', 'positionZ', 'tz', 'lz']

    attributeConversion['rotationX'] = ['rotateX', 'rx', 'rotation_eulerX']
    attributeConversion['rotationY'] = ['rotateY', 'ry', 'rotation_eulerY']
    attributeConversion['rotationZ'] = ['rotateZ', 'rz', 'rotation_eulerZ']

    attributeConversion['scaleX'] = ['sx']
    attributeConversion['scaleY'] = ['sy']
    attributeConversion['scaleZ'] = ['sz']
    transformAttributes = attributeConversion.keys()

    attributeConversion['location'] = ['translation', 'position', 't', 'l']
    attributeConversion['rotation'] = ['rotate', 'r', 'rotation_euler']
    attributeConversion['scale'] = ['s']
    attributeConversion['hide'] = ['visibility', 'v', 'h']

    attributeConversion['matrix_local'] = ['m', 'matrix', 'localMatrix']
    attributeConversion['matrix_world'] = ['wm', 'worldMatrix']
    attributeConversion['matrix_parent_inverse'] = ['inverseMatrix']

    coreAttributes = ['location', 'rotation', 'scale', 'hide', 'matrix_local', 'matrix_world',
                      'select', 'name']

    attributeIndices = dict(X=0, Y=1, Z=2, W=3, R=0, G=1, B=2, A=3)
    attributeIndicesInverse = ['X', 'Y', 'Z', 'W']

    constraints = dict(parent='COPY_TRANSFORMS', point='COPY_LOCATION',
                       orient='COPY_ROTATION', scale='COPY_SCALE',
                       location='COPY_LOCATION', rotation='COPY_ROTATION',
                       translation='COPY_LOCATION')

    dataTypes = dict()
    if bpy:
        dataTypes['object'] = bpy.data.objects
        dataTypes['mesh'] = bpy.data.meshes
        dataTypes['camera'] = bpy.data.cameras
        dataTypes['text'] = bpy.data.texts
        dataTypes['speaker'] = bpy.data.speakers
        dataTypes['sound'] = bpy.data.sounds
        dataTypes['lamp'] = bpy.data.lamps
        dataTypes['lattice'] = bpy.data.lattices
        dataTypes['library'] = bpy.data.libraries
        dataTypes['image'] = bpy.data.images
        dataTypes['curve'] = bpy.data.curves
        dataTypes['metaball'] = bpy.data.metaballs
        dataTypes['armature'] = bpy.data.armatures

    # To be used with the ls function, this points to where to get the data
    baseTypeDict = dict()
    if bpy:
        baseTypeDict[bpy.types.Object] = bpy.data.objects
        baseTypeDict[bpy.types.Mesh] = bpy.data.meshes
        baseTypeDict[bpy.types.Armature] = bpy.data.armatures
        baseTypeDict[bpy.types.Curve] = bpy.data.curves
        baseTypeDict[bpy.types.MetaBall] = bpy.data.metaballs
        baseTypeDict[bpy.types.Scene] = bpy.data.scenes
        baseTypeDict[bpy.types.Lamp] = bpy.data.lamps
        baseTypeDict[bpy.types.Lattice] = bpy.data.lattices
        baseTypeDict[bpy.types.Sound] = bpy.data.sounds
        baseTypeDict[bpy.types.Speaker] = bpy.data.speakers
        baseTypeDict[bpy.types.World] = bpy.data.worlds
        baseTypeDict[bpy.types.Library] = bpy.data.libraries
        baseTypeDict[bpy.types.Action] = bpy.data.actions
        baseTypeDict[bpy.types.Text] = bpy.data.texts
        baseTypeDict[bpy.types.Material] = bpy.data.materials
        baseTypeDict[bpy.types.Action] = bpy.data.actions

    # Simply a dict of components and the value is what type the component steps from
    componentTypeDict = dict()
    if bpy:
        componentTypeDict[bpy.types.MeshVertex] = bpy.types.Mesh
        componentTypeDict[bpy.types.MeshEdge] = bpy.types.Mesh
        componentTypeDict[bpy.types.MeshPolygon] = bpy.types.Mesh
        componentTypeDict[bpy.types.Spline] = bpy.types.Curve
        componentTypeDict[bpy.types.BezierSplinePoint] = bpy.types.Curve
        componentTypeDict[bpy.types.SplinePoint] = bpy.types.Curve
        componentTypeDict[bpy.types.MetaElement] = bpy.types.MetaBall
        componentTypeDict[bpy.types.Bone] = bpy.types.Armature

    # To expand on the base types, when querying for subclassed types
    subTypeDict = dict()
    if bpy:
        subTypeDict[bpy.types.Modifier] = [getattr(bpy.types, item) for item in ['MeshCacheModifier',
                                           'ArmatureModifier', 'SubsurfModifier', 'ArrayModifier',
                                           'VertexWeightEditModifier', 'FluidSimulationModifier',
                                           'SmokeModifier', 'SkinModifier',
                                           'SimpleDeformModifier', 'ExplodeModifier',
                                           'MultiresModifier', 'WireframeModifier',
                                           'LatticeModifier', 'SolidifyModifier',
                                           'SurfaceModifier', 'RemeshModifier',
                                           'OceanModifier', 'BevelModifier',
                                           'BooleanModifier', 'VertexWeightMixModifier',
                                           'CollisionModifier', 'HookModifier',
                                           'UVWarpModifier', 'BuildModifier',
                                           'DecimateModifier', 'VertexWeightProximityModifier',
                                           'DisplaceModifier', 'WaveModifier',
                                           'SmoothModifier', 'SoftBodyModifier',
                                           'UVProjectModifier', 'MirrorModifier',
                                           'EdgeSplitModifier', 'CastModifier',
                                           'LaplacianDeformModifier', 'LaplacianSmoothModifier',
                                           'WarpModifier', 'MeshDeformModifier',
                                           'MaskModifier', 'ParticleInstanceModifier',
                                           'TriangulateModifier', 'ClothModifier',
                                           'ShrinkwrapModifier', 'DynamicPaintModifier',
                                           'CurveModifier', 'ScrewModifier',
                                           'ParticleSystemModifier'] if hasattr(bpy.types, item)]

        subTypeDict[bpy.types.Constraint] = [getattr(bpy.types, item) for item in ['CopyTransformsConstraint',
                                             'DampedTrackConstraint', 'LimitScaleConstraint',
                                             'TrackToConstraint', 'ShrinkwrapConstraint',
                                             'LimitDistanceConstraint', 'FloorConstraint',
                                             'StretchToConstraint', 'LockedTrackConstraint',
                                             'CopyLocationConstraint', 'FollowPathConstraint',
                                             'FollowTrackConstraint', 'ChildOfConstraint',
                                             'ClampToConstraint', 'SplineIKConstraint', 'PythonConstraint',
                                             'CameraSolverConstraint', 'MaintainVolumeConstraint',
                                             'RigidBodyJointConstraint', 'CopyRotationConstraint',
                                             'KinematicConstraint', 'CopyScaleConstraint',
                                             'TransformConstraint', 'ObjectSolverConstraint',
                                             'ActionConstraint', 'LimitRotationConstraint',
                                             'PivotConstraint', 'LimitLocationConstraint'] if hasattr(bpy.types, item)]


        subTypeDict[bpy.types.Node] = [getattr(bpy.types, item) for item in ['NodeFrame', 'TextureNode',
                                       'NodeReroute', 'NodeGroup', 'CompositorNode', 'NodeGroupInput',
                                       'ShaderNode', 'NodeGroupOutput', 'TextureNodeValToRGB',
                                       'TextureNodeTexMagic', 'TextureNodeBricks', 'TextureNodeTexNoise',
                                       'TextureNodeTexMusgrave', 'TextureNodeGroup', 'TextureNodeTexDistNoise',
                                       'TextureNodeViewer', 'TextureNodeCurveTime', 'TextureNodeDecompose',
                                       'TextureNodeTexMarble', 'TextureNodeTexWood', 'TextureNodeMath',
                                       'TextureNodeAt', 'TextureNodeTexture', 'TextureNodeCompose',
                                       'TextureNodeInvert', 'TextureNodeTexStucci', 'TextureNodeTexVoronoi',
                                       'TextureNodeOutput', 'TextureNodeCurveRGB', 'TextureNodeMixRGB',
                                       'TextureNodeCoordinates', 'TextureNodeTexBlend', 'TextureNodeRotate',
                                       'TextureNodeValToNor', 'TextureNodeHueSaturation', 'TextureNodeImage',
                                       'TextureNodeTranslate', 'TextureNodeChecker', 'TextureNodeScale',
                                       'TextureNodeRGBToBW', 'TextureNodeDistance', 'TextureNodeTexClouds',
                                       'CompositorNodeKeyingScreen', 'CompositorNodeRLayers',
                                       'CompositorNodeInvert', 'CompositorNodeFilter', 'CompositorNodeBokehImage',
                                       'CompositorNodeValue', 'CompositorNodeSunBeams', 'CompositorNodeComposite',
                                       'CompositorNodeGroup', 'CompositorNodeRotate', 'CompositorNodeColorMatte',
                                       'CompositorNodeTime', 'CompositorNodeGamma', 'CompositorNodeSepHSVA',
                                       'CompositorNodeCrop', 'CompositorNodeLumaMatte',
                                       'CompositorNodeBilateralblur', 'CompositorNodeOutputFile',
                                       'CompositorNodeTonemap', 'CompositorNodeTransform',
                                       'CompositorNodeCurveRGB', 'CompositorNodeSwitch', 'CompositorNodeImage',
                                       'CompositorNodeLevels', 'CompositorNodeBoxMask', 'CompositorNodePixelate',
                                       'CompositorNodeTexture', 'CompositorNodeIDMask',
                                       'CompositorNodeSplitViewer', 'CompositorNodeDistanceMatte',
                                       'CompositorNodeRGB', 'CompositorNodeSetAlpha', 'CompositorNodeViewer',
                                       'CompositorNodeCombYUVA', 'CompositorNodeNormalize',
                                       'CompositorNodeStabilize', 'CompositorNodeCurveVec',
                                       'CompositorNodeDefocus', 'CompositorNodeMapRange',
                                       'CompositorNodeDBlur', 'CompositorNodeHueSat', 'CompositorNodeVecBlur',
                                       'CompositorNodeScale', 'CompositorNodeTranslate', 'CompositorNodeValToRGB',
                                       'CompositorNodeColorSpill', 'CompositorNodeCornerPin',
                                       'CompositorNodeLensdist', 'CompositorNodePlaneTrackDeform',
                                       'CompositorNodeInpaint', 'CompositorNodeDilateErode',
                                       'CompositorNodeDoubleEdgeMask', 'CompositorNodeBlur',
                                       'CompositorNodeAlphaOver', 'CompositorNodeMask', 'CompositorNodeMovieClip',
                                       'CompositorNodeMixRGB', 'CompositorNodeDespeckle', 'CompositorNodeSepRGBA',
                                       'CompositorNodeCombHSVA', 'CompositorNodeMapValue', 'CompositorNodeFlip',
                                       'CompositorNodeColorCorrection', 'CompositorNodeBokehBlur',
                                       'CompositorNodeCombYCCA', 'CompositorNodeSepYCCA',
                                       'CompositorNodeEllipseMask', 'CompositorNodePremulKey',
                                       'CompositorNodeMapUV', 'CompositorNodeSepYUVA', 'CompositorNodeRGBToBW',
                                       'CompositorNodeKeying', 'CompositorNodeHueCorrect', 'CompositorNodeGlare',
                                       'CompositorNodeChannelMatte', 'CompositorNodeZcombine',
                                       'CompositorNodeDisplace', 'CompositorNodeDiffMatte',
                                       'CompositorNodeBrightContrast', 'CompositorNodeCombRGBA',
                                       'CompositorNodeChromaMatte', 'CompositorNodeMath',
                                       'CompositorNodeColorBalance', 'CompositorNodeTrackPos',
                                       'CompositorNodeMovieDistortion', 'CompositorNodeNormal',
                                       'ShaderNodeLightFalloff', 'ShaderNodeCombineRGB', 'ShaderNodeGeometry',
                                       'ShaderNodeHueSaturation', 'ShaderNodeBsdfHair', 'ShaderNodeTexBrick',
                                       'ShaderNodeUVMap', 'ShaderNodeTexture', 'ShaderNodeOutputMaterial',
                                       'ShaderNodeInvert', 'ShaderNodeHoldout', 'ShaderNodeScript',
                                       'ShaderNodeBsdfGlass', 'ShaderNodeValue', 'ShaderNodeExtendedMaterial',
                                       'ShaderNodeMaterial', 'ShaderNodeBsdfVelvet', 'ShaderNodeOutputWorld',
                                       'ShaderNodeMapping', 'ShaderNodeSeparateXYZ', 'ShaderNodeTexImage',
                                       'ShaderNodeRGBCurve', 'ShaderNodeBsdfToon', 'ShaderNodeLayerWeight',
                                       'ShaderNodeSubsurfaceScattering', 'ShaderNodeEmission',
                                       'ShaderNodeParticleInfo', 'ShaderNodeFresnel', 'ShaderNodeVectorCurve',
                                       'ShaderNodeLightPath', 'ShaderNodeGroup', 'ShaderNodeTexNoise',
                                       'ShaderNodeGamma', 'ShaderNodeNewGeometry', 'ShaderNodeCombineXYZ',
                                       'ShaderNodeSeparateHSV', 'ShaderNodeBump', 'ShaderNodeNormal',
                                       'ShaderNodeValToRGB', 'ShaderNodeVolumeAbsorption',
                                       'ShaderNodeSeparateRGB', 'ShaderNodeVolumeScatter',
                                       'ShaderNodeObjectInfo', 'ShaderNodeBackground',
                                       'ShaderNodeBsdfGlossy', 'ShaderNodeAmbientOcclusion',
                                       'ShaderNodeOutputLamp', 'ShaderNodeCombineHSV', 'ShaderNodeHairInfo',
                                       'ShaderNodeOutput', 'ShaderNodeNormalMap', 'ShaderNodeOutputLineStyle',
                                       'ShaderNodeMath', 'ShaderNodeRGBToBW', 'ShaderNodeTexGradient',
                                       'ShaderNodeAddShader', 'ShaderNodeCameraData', 'ShaderNodeTexSky',
                                       'ShaderNodeTexWave', 'ShaderNodeUVAlongStroke', 'ShaderNodeTangent',
                                       'ShaderNodeTexMusgrave', 'ShaderNodeBsdfAnisotropic',
                                       'ShaderNodeTexChecker', 'ShaderNodeMixRGB', 'ShaderNodeBsdfRefraction',
                                       'ShaderNodeBsdfTransparent', 'ShaderNodeBsdfTranslucent',
                                       'ShaderNodeMixShader', 'ShaderNodeRGB', 'ShaderNodeWireframe',
                                       'ShaderNodeTexCoord', 'ShaderNodeBlackbody', 'ShaderNodeAttribute',
                                       'ShaderNodeBsdfDiffuse', 'ShaderNodeBrightContrast',
                                       'ShaderNodeTexEnvironment', 'ShaderNodeLampData',
                                       'ShaderNodeVectorTransform', 'ShaderNodeWavelength',
                                       'ShaderNodeTexMagic', 'ShaderNodeVectorMath', 'ShaderNodeSqueeze',
                                       'ShaderNodeTexVoronoi'] if hasattr(bpy.types, item)]

    subTypeList = []
    for subTypes in subTypeDict.values():
        subTypeList += subTypes

    # Full list of supported type objects
    typesList = list(baseTypeDict.keys())
    typesList += list(subTypeDict.keys())
    typesList += subTypeList
    if bpy:
        typesList += [bpy.types.Driver, bpy.types.FCurve, bpy.types.NodeTree]

    driverTransformConversion = dict()
    driverTransformConversion['location'] = ['LOC_X', 'LOC_Y', 'LOC_Z']
    driverTransformConversion['rotation'] = ['ROT_X', 'ROT_Y', 'ROT_Z']
    driverTransformConversion['scale'] = ['SCALE_X', 'SCALE_Y', 'SCALE_Z']

    matrixTransformAttrConversion = dict(location='to_translation', rotation='to_euler', scale='to_scale')

    renderFormats = ['BMP', 'IRIS', 'PNG', 'JPEG', 'JPEG2000', 'TARGA',
                     'TARGA_RAW', 'CINEON', 'DPX', 'OPEN_EXR_MULTILAYER',
                     'OPEN_EXR', 'HDR', 'TIFF', 'AVI_JPEG', 'AVI_RAW',
                     'FRAMESERVER', 'H264', 'FFMPEG', 'THEORA', 'XVID']

    tangentTypes = dict(spline='BEZIER', linear='LINEAR', bezier='BEZIER',
                        constant='CONSTANT', flat='BEZIER', stepped='CONSTANT')


def parseDouble(value):
    '''
    This function is used internally, it will take an input of string, float, list, etc and return a two part tuple

    IN:
        [value] value in type(list, tuple, int, float, str)

    OUT:
        [tuple] (value[0], value[1])
    '''
    if isType(value, [list, tuple]):
        if len(value) <= 0:
            raise RuntimeError('parseDouble: invalid value: {0}'.format(value))

        if len(value) >= 2:
            value = (asFloat(value[0]), asFloat(value[1]))

        if len(value) == 1:
            value = (asFloat(value), asFloat(value))

    elif isType(value, [int, float, str]):
        value = (asFloat(value), asFloat(value))

    if value is None:
        raise RuntimeError('parseDouble: invalid value: {0}'.format(value))

    return value


def scaleInRange(value, originalRange, targetRange):
    '''
    This function is used internally, It takes a value and a range and places it in the appropriate
    position in the second range

    IN:
        [float] value
        [tuple] originalRange
        [tuple] targetRange

    OUT:
        [float] value
    '''
    oR = (originalRange[0] if len(originalRange) == 2 else min(originalRange),
          originalRange[1] if len(originalRange) == 2 else max(originalRange))
    tR = (targetRange[0] if len(targetRange) == 2 else min(targetRange),
          targetRange[1] if len(targetRange) == 2 else max(targetRange))

    # Avoid zero division errors
    if oR[0] == oR[1]:
        return oR[0]

    if tR[0] == tR[1]:
        return tR[0]

    p = (value-oR[0]) / (oR[1]-oR[0])
    result = p*(tR[1] - tR[0]) + tR[0]
    return result


class Ptr(object):
    '''
    This class is used to hold a pointer to attributes with indices to be used internally

    IN:
        [ptr] attribute, the attribute to reference
        [str] name, optional for item attributes
        [int] index, optional if there is multiple indices
    '''
    def __init__(self, object, name=None, index=None):
        self.object = object
        self.name = name
        self.index = index

    def set(self, value):
        if self.name:
            if hasattr(self.object, self.name):
                item = getattr(self.object, self.name)
                if self.index is not None:
                    item[self.index] = value

                else:
                    item = value

            elif hasattr(self.object, 'keys') and self.name in self.object.keys():
                if self.index is not None:
                    self.object[self.name][self.index] = value

                else:
                    self.object[self.name] = value

        else:
            if self.index:
                self.object[self.index] = value

            else:
                self.object = value

    def get(self):
        item = None
        if self.name:
            if hasattr(self.object, self.name):
                item = getattr(self.object, self.name)

            elif hasattr(self.object, 'keys') and self.name in self.object.keys():
                item = self.object.keys()[self.name]

        else:
            item = self.object

        if item and self.index is not None:
            return item[self.index]

        return item


def getDataType(type, getParentCurve=False):
    '''
    Return all items that match the specified type
    This is designed to be used internally

    IN:
        [type] type, the type to look for, example: bpy.types.Node
        [bool] getParentCurve, specifically for getting drivers

    OUT:
        [list] items
    '''
    def getNodeTrees():
        '''
        Get all node trees

        OUT:
            [list] items
        '''
        results = []
        for items in [bpy.data.materials, bpy.data.worlds, bpy.data.scenes]:
            for items in items:
                nodeTree = items.nodeTree
                if not nodeTree:
                    continue

            results.append(nodeTree)

        return results


    def getNodes(type=None):
        '''
        Get all nodes in blender, you can optionally pass in a type to filter


        Optional:
            [type] type, the type to look for, example: bpy.types.ShaderNodeOutputMaterial

        OUT:
            [list] items
        '''
        for nodeTree in getDataType(bpy.types.NodeTree):
            for node in nodeTree.nodes:
                if type is not None:
                    if isType(node, type):
                        yield node

                    else:
                        continue

                yield node


    def getFCurves():
        '''
        Get all animation curves

        OUT:
            [list] items
        '''
        for action in getDataType(bpy.types.Action):
            for curve in action.fcurves:
                yield curve


    def getDrivers(getParentCurve=False):
        '''
        Get all drivers in blender


        Optional:
            [bool] getParentCurve, if True will return the FCurve instead of the driver, default=False

        OUT:
            [list] items
        '''
        results = []
        for dataType in CONSTANTS.baseTypeDict.keys():
            if dataType in [bpy.types.FCurve, bpy.types.Driver]:
                continue

            for item in getDataType(dataType):
                if not hasattr(item, 'animation_data') or not item.animation_data:
                    continue

                for driver in item.animation_data.drivers:
                    if not getParentCurve:
                        driver = driver.driver

                    results.append(driver)

        return results


    def getModifiers(type=None):
        '''
        Get all modifiers in blender, you can optionally pass in a type to filter


        Optional:
            [type] type, the type to look for, example: bpy.types.ArmatureModifier

        OUT:
            [list] items
        '''
        results = []
        for dataType in CONSTANTS.baseTypeDict.keys():
            if dataType in [bpy.types.FCurve, bpy.types.Driver, bpy.types.Modifier, bpy.types.Constraint]:
                continue

            for item in getDataType(dataType):
                if not hasattr(item, 'modifiers'):
                    continue

                for modifier in item.modifiers:
                    if type is not None:
                        if isType(modifier, type):
                            results.append(modifier)

                        else:
                            continue

                results.append(modifier)

        return results


    def getConstraints(type=None):
        '''
        Get all constraints in blender, you can optionally pass in a type to filter


        Optional:
            [type] type, the type to look for, example: bpy.types.LimitLocationConstraint

        OUT:
            [list] items
        '''
        results = []
        for dataType in CONSTANTS.baseTypeDict.keys():
            if dataType in [bpy.types.FCurve, bpy.types.Driver, bpy.types.Modifier, bpy.types.Constraint]:
                continue

            for item in getDataType(dataType):
                if not hasattr(item, 'constraints'):
                    continue

                for constraint in item.modifiers:
                    if type is not None:
                        if isType(constraint, type):
                            results.append(constraint)

                        else:
                            continue

                    results.append(constraint)

        return results

    if type in CONSTANTS.baseTypeDict.keys():
        return list(CONSTANTS.baseTypeDict.get(type))

    elif type in [bpy.types.NodeTree]:
        return list(getNodeTrees())

    elif type in [bpy.types.Node]:
        return list(getNodes())

    elif type in [bpy.types.FCurve]:
        return list(getFCurves())

    elif type in [bpy.types.Driver]:
        return list(getDrivers(getParentCurve=getParentCurve))

    elif type in [bpy.types.Modifier]:
        return list(getModifiers())

    elif type in [bpy.types.Constraint]:
        return list(getConstraints())

    elif type in CONSTANTS.subTypeDict[bpy.types.Modifier]:
        return list(getModifiers(type))

    elif type in CONSTANTS.subTypeDict[bpy.types.Constraint]:
        return list(getConstraints(type))

    elif type in CONSTANTS.subTypeDict[bpy.types.Node]:
        return list(getNodes(type))

    print('WARNING: invalid type: {0}'.format(type))
    return []


def ls(search=None,
       flatten=None, fl=None,
       type=None, t=None,
       referencedNodes=None, rn=None,
       selection=None, sl=None,
       visible=None, v=None,
       invisible=None, iv=None,
       regex=None, rgx=None,
       caseInsensitive=None, ci=None,
       getParentCurve=None, gpc=None,
       *args, **kwargs):
    '''
    The ls command returns the names (and optionally the type names) of objects in the scene.
    ls will always return a list of objects, unless the type is a component then it is a list of tuples.
    If flatten is True, component mode will return a list of components instead of tuples
    If search is an object or list of objects, it will search for components on the search objects

    Optional Parameters:
        [str]  search             : String to search for
        [bool] flatten/fl         : Flattens the returned list of objects so that each component is identified individually, default=False
                                  : This is useful when listing components and you do not want a list of tuples
        [str]  type/t             : Type of item to return, accepts string or type class
        [bool] referencedNodes/rn : Returns only items from a linked library, default=False
        [bool] selection/sl       : Returns selected objects, default=False
        [bool] visible/v          : Returns visible objects, default=False
        [bool] invisible/iv       : returns hidden objects, default=False
        [bool] regex              : Enables regular expression searching, default=False
        [bool] getParentCurve/gpc : If True will get the parent curve when listing drivers, default=False

    Out:
        [list] objects

    '''
    # Parse arguments
    flatten = parseArgs(flatten, fl, False)
    objectType = parseArgs(type, t, None)
    referencedNodes = parseArgs(referencedNodes, rn, False)
    selection = parseArgs(selection, sl, False)
    visible = parseArgs(visible, v, False)
    regex = parseArgs(regex, rgx, False)
    caseInsensitive = parseArgs(caseInsensitive, ci, False)
    invisible = parseArgs(invisible, iv, False)
    getParentCurve = parseArgs(getParentCurve, gpc, False)
    type = builtins.type

    def mesh(data, selection=False, type='component'):
        if selection:
            b = bmesh.from_edit_mesh(data)
            if type == 'component':
                selectMode = fi(list(b.select_mode)) or 'VERT'
                type = {'VERT': 'vertex', 'EDGE': 'edge', 'FACE': 'face'}.get(selectMode)

        else:
            b = bmesh.new()
            b.from_mesh(data)

        if type == 'vertex':
            components = b.verts
            cData = data.vertices

        elif type == 'edge':
            components = b.edges
            cData = data.edges

        elif type == 'face':
            components = b.faces
            cData = data.polygons

        else:
            components = b.verts

        if selection:
            components = [c for c in components if c.select]

        result = [cData[c.index] for c in components]
        return result

    def curve(data, selection=False):
        points = []
        for spline in data.splines:
            if spline.type.lower() == 'nurbs':
                if selection:
                    for point in spline.points:
                        if not point.select:
                            continue
                        points.append(point)

                else:
                    points += list(spline.points)

            else:
                if selection:
                    for point in spline.bezier_points:
                        if not any([point.select_control_point, point.select_left_handle, point.select_right_handle]):
                            continue
                        points.append(point)

                else:
                    points += list(spline.bezier_points)
        return points

    def component(objects, selection=False, flatten=False, type='component'):
        objectType = type
        type = builtins.type
        results = []

        for obj in objects:
            oData = obj.data
            if selection and not (hasattr(oData, 'is_editmode') and oData.is_editmode):
                continue

            if type(oData) == bpy.types.Mesh:
                result = mesh(oData, selection, type=objectType)

            elif type(oData) == bpy.types.Curve:
                result = curve(oData, selection)

            else:
                print('invalid type {0}: {1}'.format(type(obj), obj))

        if flatten:
            results += result

        else:
            results.append((obj, result))

        return results

    def filterItems(items, type=None, search=None, selection=False,
                    visible=None, invisible=None, regex=False,
                    referencedNodes=False, caseInsensitive=False):
        results = []

        for item in items:
            # Check Type
            if type:
                if isType(type, str):
                    # case insensitive due to blender using caps and maya using lower case
                    if not item.type.lower() == type.lower():
                        continue

                # Only check subtypes as by this point we have already been filtered through main types
                elif type in CONSTANTS.subTypes:
                    if not type(item) == type:
                        continue

            if selection and (hasattr(item, 'select') and not item.select):
                continue

            # Check visibility
            isVisible = not item.hide if hasattr(item, 'hide') else False
            if visible is True and not isVisible:
                continue

            if invisible is True and isVisible:
                continue

            isReferenced = item.library if hasattr(item, 'library') else False
            if referencedNodes and not isReferenced:
                continue

            # Check name
            if search and hasattr(item, 'name'):
                name = item.name
                if regex:
                    if not re.match(search, name):
                        continue

                elif caseInsensitive:
                    if search.lower() not in name.lower():
                        continue

                else:
                    if search not in name:
                        continue

            results.append(item)

        return results

    results = []

    # COMPONENTS
    # Different way to check components as it is a lot more restricted
    # Still need support for lattice and metaballs
    if objectType in ['component', 'vertex', 'edge', 'face', 'cv', 'spline', 'point']:
        if not any([search, selection]):
            print('WARNING: objects or selection Parameters required when listing components')
            return []

        if search:
            search = asList(search)
            objects = asObjects(search)

        else:
            objects = ls(sl=1)

        if not objects:
            return []

        return component(objects, selection=selection, type=objectType, flatten=flatten)

    # OBJECTS
    if objectType in CONSTANTS.typesList:
        items = getDataType(objectType, getParentCurve=getParentCurve)

    else:
        items = bpy.data.objects

    results = filterItems(items, type=objectType, search=search, selection=selection,
                          visible=visible, invisible=invisible, regex=regex,
                          referencedNodes=referencedNodes, caseInsensitive=caseInsensitive)

    # Items such as constraints and modifiers can be returned multiple times, filter them out here
    results = list(set(results))

    # Make sure the active object is always last
    activeObject = bpy.context.scene.objects.active
    if activeObject in results:
        results.pop(results.index(activeObject))
        results.append(activeObject)

    return results


def parent(objects=None, target=None,
           world=None, w=None,
           relative=None, r=None,
           absolute=None, a=None,
           *args, **kwargs):
    '''
    Parents the objects under the given target.
    If world is True unparent the items.

    Optional Parameters:
        [list]  objects                : Object or list of objects to parent
        [obj]   target                 : Object to parent objects to
        [bool]  world/w                : If True will unparent the items
        [bool]  relative/r             : If True will maintain local transformations
        [bool]  absolute/a             : If True will maintain world transformations
    '''
    world = parseArgs(world, w, False)
    relative = parseArgs(relative, r, None)
    absolute = parseArgs(absolute, a, None)
    if not any([relative, absolute]):
        absolute = bool(absolute is None)

    if objects is None:
        objects = ls(sl=1)

    if not objects:
        return

    objects = asObjects(objects, forceObjects=True)

    selection = ls(sl=1)

    if not any([target, world]):
        target = li(objects)

    target = asObject(target, forceObjects=True)

    select(objects)
    if world:
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM' if absolute else 'CLEAR')

    else:
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=bool(absolute))

    if selection:
        select(selection)



def select(objects=None,
           clear=None, cl=None,
           add=False, all=False,
           deselect=None, d=None,
           toggle=None, tgl=None,
           replace=None, r=None,
           *args, **kwargs):
    '''
    This command is used to put objects onto or off of the active list.
    default action is to replace the selected objects

    Optional Parameters:
        [list] objects    : list of objects to select
        [bool] clear/cl   : clears the selection, default=False
        [bool] add        : appends items to selection, default=False
        [bool] all        : selects all selectable objects, default=False
        [bool] deselect/d : removes the items from the selection, default=False
        [bool] toggle/tgl : toggles the selected state of the items, default=False
        [bool] replace/r  : Replaces the selection, this is the default action
    '''
    clear = parseArgs(clear, cl, False)
    deselect = parseArgs(deselect, d, False)
    toggle = parseArgs(toggle, tgl, False)
    replace = parseArgs(replace, r, True) # not that this is used anywhere

    # Bulk actions on selection
    if any([clear, all, toggle]):
        if all:
            mode = 'SELECT'

        elif toggle:
            mode = 'TOGGLE'

        else:
            mode = 'DESELECT'

        for action in [bpy.ops.curve, bpy.ops.mesh, bpy.ops.mball, bpy.ops.lattice, bpy.ops.object]:
            try:
                action.select_all(action=mode)

            except:
                pass

        return

    # This does not seem to work, for some reason blender will not select components when in component mode
    # isEditMode = any([obj.data.is_editmode for obj in bpy.data.objects if hasattr(obj.data, 'is_editmode')])
    # if isEditMode:
    #     bpy.ops.object.mode_set(mode='OBJECT')

    # If replacing selection, clear it first
    if not any([deselect, add]):
        select(clear=True)

    value = bool(not deselect)

    objects = asObjects(objects)
    for obj in objects:
        for attr in ['select', 'select_control_point']:
            if not hasattr(obj, attr):
                continue

            obj.__setattr__(attr, value)
            break

    lastItem = li(objects)
    if lastItem in bpy.data.objects.values():
        bpy.context.scene.objects.active = lastItem

    # if isEditMode:
    #     bpy.ops.object.mode_set(mode='EDIT')


def listRelatives(objects=None,
                  allDecendants=None, ad=None,
                  allParents=None, ap=None,
                  children=None, c=None,
                  shapes=None, s=None,
                  parents=None, p=None,
                  type=None,
                  *args, **kwargs):
    '''
    Lists objects or shapes related to the specified object(s)

    Optional Parameters:
        [list] objects          : list of objects to query
        [bool] allDecendants/ad : If True will list all childrens children recursively, default=False
        [bool] allParents/ap    : If True will list all parents parents recursively, default=False
        [bool] children/c       : Will list immediate children of this node, default=False
        [bool] shapes/s         : Will list any shapes of this object if there is any, default=False
        [bool] parents/p        : Will list any parents of this object if there is any, default=False
        [bool] type             : Filters the items by type, default=False

    Out:
        [list] objects
    '''
    def recursiveGetChildren(obj, results=None):
        results = results or []
        children = obj.children
        if not children:
            return results

        for child in children:
            results.append(child)
            results = recursiveGetChildren(child, results=results)

        return results

    allDecendants = parseArgs(allDecendants, ad, False)
    allParents = parseArgs(allParents, ap, False)
    children = parseArgs(children, c, False)
    shapes = parseArgs(shapes, s, False)
    parents = parseArgs(parents, p, False)
    objects = asObjects(objects, forceObjects=True)

    results = []
    for obj in objects:
        if parents and hasattr(obj, 'parent'):
            if allParents:
                o = obj
                while hasattr(o, 'parent'):
                    parent = o.parent
                    results.append(parent)
                    o = parent

            else:
                parent = obj.parent
                if parent:
                    results.append(parent)

        if children and hasattr(obj, 'children'):
            if allDecendants:
                children = recursiveGetChildren(obj)

            else:
                children = obj.children

            if children:
                results += children

        if shapes:
            data = obj.data
            if data:
                results.append(data)

    return results


def listAttr(objects=None,
             connectable=None, c=None,
             keyable=None, k=None,
             locked=None, l=None,
             unlocked=None, u=None,
             settable=None, s=None,
             userDefined=None, ud=None,
             internal=None, i=None,
             *args, **kwargs):
    '''
    Lists attributes for the specified objects

    Optional Parameters:
        [list] objects        : list of objects to query
        [bool] connectable/c  : List only attributes that can recieve connections, default=False
        [bool] keyable/k      : List only attributes that can accept keyframes, default=False
        [bool] locked/l       : List only locked attributes, default=False
        [bool] unlocked/u     : List only unlocked attributes, default=False
        [bool] settable/s     : List only attributes that are settable, default=False
        [bool] userDefined/ud : List only attributes that are not default, default=False
        [bool] internal/i     : If True will include attributes starting with underscores, default=False

    Out:
        [list] attributes
    '''
    objects = asObjects(objects)
    connectable = parseArgs(connectable, c, False)
    keyable = parseArgs(keyable, k, False)
    locked = parseArgs(locked, l, False)
    unlocked = parseArgs(unlocked, u, False)
    settable = parseArgs(settable, s, False)
    userDefined = parseArgs(userDefined, ud, None)
    internal = parseArgs(internal, i, False)
    results = []
    for obj in objects:
        if not userDefined:
            for realAttr, attr in dict(location='location', rotation_euler='rotation', scale='scale').items():
                subAttrs = ['{0}{1}'.format(attr, axis) for axis in ['X', 'Y', 'Z']]
                if not hasattr(obj, realAttr):
                    continue

                # attribute = getattr(obj, attr)
                lockAttr = getattr(obj, 'lock_{0}'.format(attr))

                for i, subAttr in enumerate(subAttrs):
                    if subAttr in results:
                        continue

                    if (locked is True and lockAttr[i] is False):
                        continue

                    if (unlocked is True and lockAttr[i] is True):
                        continue

                    if (settable or keyable) and getDriver(obj, subAttr):
                        continue

                    results.append(subAttr)

            if hasattr(obj, 'hide') and not locked:
                results.append('hide')

        # We cannot lock custom attributes so don't bother checking
        if userDefined in [False, 0] or locked is True:
            continue

        for attr, value in obj.items():
            if attr in results:
                continue

            if not internal and attr.startswith('_'):
                continue

            if any([settable, keyable]):
                driver = getDriver(obj, attr)
                if driver:
                    continue

                if keyable and type(value) not in [int, float]:
                    continue

            results.append(attr)

    return list(set(results))


def addDriver(node, attribute, idData=None, dataPath=None, expression=None):
    '''
    Adds a driver to a node

    Required:
        [obj] node            : The node on which to create the driver
        [str] attribute       : attribute to add driver to

    Optional:
        [id]  idData          : optional id_data for the target
        [str] dataPath        : optional path to source attribute
        [str] expression      : string expression, default=var

    OUT:
        [bpy.types.FCurve] driver
    '''
    def getAttributeDataPath(attribute):
        '''
        Format the attribute in a way that the driver system can handle

        IN:
            [str] attribute

        OUT:
            [tuple] (attribute, index)
        '''
        # We may have already been passed an attribute
        if '[' in attribute:
            return (attribute, None)

        attribute, index = getAttributeIndex(attribute)
        if attribute not in CONSTANTS.coreAttributes:
            attribute = '["{0}"]'.format(attribute)

        return (attribute, index)

    transformChannel = None
    attribute, attributeIndex = getAttributeDataPath(attribute)

    if dataPath:
        dataPath, index = getAttributeDataPath(dataPath)
        if dataPath in CONSTANTS.driverTransformConversion.keys():
            transformChannel = CONSTANTS.driverTransformConversion.get(dataPath)[index or 0]


    if attributeIndex is not None:
        driver = node.driver_add(attribute, attributeIndex)

    else:
        driver = node.driver_add(attribute)

    var = driver.driver.variables.new()
    if idData:
        var.targets[0].id = idData

    if dataPath:
        var.targets[0].data_path = dataPath

        if transformChannel:
            var.type = 'TRANSFORMS'
            var.targets[0].transform_type = transformChannel
            var.targets[0].transform_space = 'LOCAL_SPACE'

    driver.driver.expression = expression or 'var'

    return driver


def getFCurve(object, attribute=None, driver=False, createIfNotExists=False):
    '''
    This will return the FCurve for the attribute if it exists

    IN:
        [obj]  object
        [str]  attribute
        [bool] driver    : If True will get drivers instead of animation curves
        [bool] createIfNotExists : If True will Create the curve if it does not exist

    OUT:
        [bpy.types.FCurve] FCurve
    '''
    def getCurve(data, attribute, index):
        for item in data:
            dataPath = reAttribute.sub('', item.data_path)
            if not dataPath == attribute:
                continue

            if not item.array_index == index:
                continue

            return item
        return None

    if isType(object, bpy.types.FCurve):
        return object

    object, attribute = parseObjectAttribute(object, attribute)

    if not hasattr(object, 'animation_data'):
        return None

    data = object.animation_data
    if not data:
        if createIfNotExists and hasattr(object, 'animation_data_create'):
            object.animation_data_create()

        else:
            return None

    stripAttribute, index = getAttributeIndex(attribute)
    index = index or 0

    if driver:
        items = data.drivers
    else:
        items = data.action.fcurves

    item = getCurve(items, stripAttribute, index)
    if item:
        return item

    if not createIfNotExists:
        return None

    if driver:
        driver = addDriver(object, attribute)
        return driver

    # To add an empty curve, we must create it with a key, then remove the key
    object.keyframe_insert(stripAttribute, index)
    curve = getCurve(object.animation_data.action.fcurves, stripAttribute, index)
    if not curve:
        return None

    curve.keyframe_points.remove(curve.keyframe_points[0])
    return curve


def getFCurves(data, driver=False, createIfNotExists=False):
    '''
    This will return the FCurves for specified data

    IN:
        [obj]  data              : A Dictionary of objectAttributes or other various object inputs
        [bool] driver            : If True will get drivers instead of animation curves
        [bool] createIfNotExists : If True will Create the curve if it does not exist

    OUT:
        [list] FCurves
    '''
    curves = []
    if isType(data, bpy.types.FCurve):
        return [data]

    elif isType(data, [list, tuple]):
        curves = [c for c in data if isType(c, [bpy.types.FCurve])]

    if curves:
        return curves

    data = parseObjectAttributes(data, listAttrIfEmpty=True, removeNone=True)
    for obj, attrs in data.items():
        curves += [getFCurve(obj, attr, driver=driver, createIfNotExists=createIfNotExists) for attr in attrs]

    return [c for c in curves if c]


def getDriver(object, attribute=None):
    '''
    This will return the driver for the attribute if it exists

    IN:
        [obj] object
        [str] attribute

    OUT:
        [bpy.types.FCurve] driver
    '''
    return getFCurve(object, attribute, driver=True)


def getDriverInfo(driver):
    '''
    This will return the info for the specified driver

    IN:
        [obj] driver

    OUT:
        [dict] info

    Example output:
        {'attribute': 'locationX',
         'driver': bpy.data.objects['Plane']...Driver,
         'expression': 'var',
         'object': bpy.data.objects['Plane'],
         'source': {bpy.data.armatures['Armature'].bones['Bone']: ['locationY']},
         'type': 'SCRIPTED',
         'variables': [{'name': 'var',
                        'targets': {bpy.data.objects['Armature']: {'attribute': 'locationY',
                                                                   'bone': bpy.data.armatures['Armature'].bones['Bone'],
                                                                   'space': 'WORLD_SPACE',
                                                                   'target': bpy.data.objects['Plane']...DriverTarget,
                                                                   'type': 'LOC_Y'}},
                        'type': 'TRANSFORMS',
                        'variable': bpy.data.objects['Plane']...DriverVariable}]}
    '''
    curve = None
    if hasattr(driver, 'driver'):
        curve = driver
        driver = driver.driver

    if not driver:
        return {}

    results = dict(driver=driver, type=driver.type, object=driver.id_data, attribute=None,
                   source={}, expression=driver.expression, variables=[])

    # We need the curve to get the attribute it is connected to
    if curve:
        index = curve.array_index
        attribute = reAttribute.sub('', curve.data_path)
        if attribute in ['location', 'rotation', 'scale'] or not index == 0:
            attribute = resolveAttributeName('{0}[{1}]'.format(attribute, index))

        results['attribute'] = attribute

    for var in driver.variables:
        item = dict(variable=var, name=var.name, type=var.type, targets={})
        for target in var.targets:
            object = target.id
            bone = target.bone_target
            if bone and object.type == 'ARMATURE':
                bone = object.data.bones.get(bone)

            attribute = target.data_path
            if attribute in ['location', 'rotation', 'scale']:
                index = CONSTANTS.driverTransformConversion[attribute].index(target.transform_type)
                attribute = resolveAttributeName('{0}[{1}]'.format(attribute, index))

            item['targets'][object] = dict(target=target, space=target.transform_space, bone=bone,
                                           attribute=attribute)

            if bone:
                object = bone

            if target.id in results['source']:
                results['source'][object].append(attribute)

            else:
                results['source'][object] = [attribute]

        results['variables'].append(item)

    return results


def getFCurveInfo(curve):
    '''
    This will return the info for the specified curve

    IN:
        [obj] curve

    OUT:
        [dict] info

    Example output:
        {'attribute': 'locationX',
         'driver': bpy.data.objects['Plane']...Driver,
         'curve': bpy.data.objects['Plane']...FCurve,
         'extrapolation' : 'CONSTANT',
         'range' : (1.0, 250.0),
         'modifiers' : [],
         'keys' : {key: {keyframe, value, time, baseValue, handleLeft, handleRight}}
    '''
    results = dict()
    index = curve.array_index
    attribute = reAttribute.sub('', curve.data_path)
    if attribute in ['location', 'rotation', 'scale'] or not index == 0:
        attribute = resolveAttributeName('{0}[{1}]'.format(attribute, index))

    results['attribute'] = attribute
    results['driver'] = curve.driver
    results['curve'] = curve
    results['action'] = curve.id_data
    results['extrapolation'] = curve.extrapolation
    results['muted'] = bool(curve.mute)
    results['keys'] = dict()

    results['modifiers'] = []
    for modifier in curve.modifiers:
        data = dict()
        data['active'] = modifier.active
        data['type'] = modifier.type
        data['muted'] = bool(modifier.mute)
        data['modifier'] = modifier
        results['modifiers'].append(data)
        # As each modifier has different values there is little point getting them here

    for key in curve.keyframe_points:
        data = dict()
        co = key.co
        data['interpolation'] = key.interpolation
        data['time'] = co[0]
        data['value'] = co[1]
        data['handles'] = dict()
        data['handles']['left'] = dict(position=tuple(key.handle_left), type=key.handle_left_type)
        data['handles']['right'] = dict(position=tuple(key.handle_right), type=key.handle_right_type)

        results['keys'][key] = data

    return results


    # TODO We also need one for just getting key/value pairs for performance. perhaps embed it into keyframe()


def getAttributeIndex(attribute):
    '''
    This is used to get an index of an attribute when available.
    For example
    translateX returns (translate, 0)
    colorG returns (color, 1)
    prop returns (prop, None)

    IN:
        [str] attribute

    OUT:
        [tuple] (attribute, index)
    '''
    if not isType(attribute, [str]):
        raise RuntimeError('{0} is not a string'.format(attribute))

    attribute = resolveAttributeName(attribute)
    if re.match('rotation[XYZW]', attribute):
        attribute = attribute.replace('rotation', 'rotation_euler')

    indices = CONSTANTS.attributeIndices
    char = attribute[-1]
    if char in indices.keys():
        attribute = attribute[:-1]

    return (attribute, indices.get(char))


def resolveAttributeName(attribute, object=None):
    '''
    Given an attribute name it will resolve it into something that can be used by the cmds module.
    This does not necesarily mean that the attribute exists, it is simply checking names
    As a result this makes attributes behave similar to maya
    translateX becomes locationX
    ry becomes rotationY
    customProperty remains the same
    optionally if an object is specified it will first check if the attribute exists on that object
    as a custom attribute

    IN:
        [str]    attribute
        [object] object, default=None

    OUT:
        [str]    attribute
    '''
    if not attribute:
        return None

    if object is None and isType(attribute, str) and '.' in attribute:
        object, attribute = attribute.rsplit('.', 1)

    object = asObject(object)

    if isType(object, [str]):
        object = asObject(object)

    if object is None and isType(attribute, [list, tuple]):
        if not len(attribute) == 2:
            raise RuntimeError('must be string or tuple of (object, attribute) or (object, [attributes])')

        object, attribute = attribute

    # Check if we are parsing multiple attributes, although not explicetly exposed we need to support this internally
    if isType(attribute, [list, tuple]):
        results = [resolveAttributeName(attr, object) for attr in attribute]
        return results

    if object and attribute in object.keys():
        return attribute

    # Check if the index has been passed in in list form
    listIndexMatch = re.findall('([A-Za-z0-9_\-\.]*)\[([0-9]*)\]', attribute)
    if listIndexMatch:
        attribute, index = listIndexMatch[0]
        attribute = '{0}{1}'.format(attribute, CONSTANTS.attributeIndicesInverse[int(index)])

    else:
        attribute = reAttribute.sub('', attribute)

    for key, values in CONSTANTS.attributeConversion.items():
        if attribute in values:
            return key

    return attribute


def resolveAttributeNames(attributes, object=None, transforms=False):
    '''
    This will resolve the attribute names and return a unique list
    If transforms is True, it will only return the base transform attributes

    IN:
        [list]   attributes
        [object] object, default=None
        [bool]   transforms, default=False

    OUT:
        [list]   attributes
    '''
    results = list(set([resolveAttributeName(attribute, object) for attribute in asList(attributes)]))
    results = [attr for attr in results if attr in CONSTANTS.transformAttributes]
    return results


def parseObjectAttribute(object, attribute=None):
    '''
    This is used to get the various combinations of object, attribute to an appropriate form
    object or attribute may return as None if it could not validate them, but it will always be a tuple
    If attribute is not None, it will assume that object is an object or string
    valid inputs:
        object=object, attribute=attribute
        object=(object, attribute), attribute=None
        object='object.attribute', attribute=None
        object='object.attribute', attribute=None

    IN:
        [input] object
        [str]   attribute

    OUT:
        [tuple] (object, attribute)
    '''
    if not any([object, attribute]):
        raise RuntimeError('Could not parseObjectAttribute({0}, {1})'.format(object, attribute))

    # Check if correct inputs already passed
    if attribute:
        # Do note that node may return as a None type if invalid
        node = asObject(object)
        attribute = resolveAttributeName(attribute, node)
        return (node, attribute)

    if isType(object, [str]):
        if '.' not in object:
            return (None, None)

        o, a = object.rsplit('.', 1)
        if not re.match('[0-9].*', a):
            object, attribute = (o, a)
        node = asObject(object)
        attribute = resolveAttributeName(attribute, node)
        return (node, attribute)

    if isType(object, [list, tuple]):
        object = asList(object)
        if not len(object) == 2:
            raise RuntimeError('invalid object for parseObjectAttribute({0}, {1})'.format(object, attribute))

        object, attribute = object
        return parseObjectAttribute(object, attribute)

    if isType(object, [dict]):
        key = fi(object.keys())
        if not key:
            return (None, None)

        value = object.get(key)
        return parseObjectAttribute(key, value)
        return (node, attribute)

    raise RuntimeError('Could not parseObjectAttribute({0}, {1})'.format(object, attribute))


def parseObjectAttributes(object, attributes=None, listAttrIfEmpty=False, removeNone=False):
    '''
    Like parseObjectAttribute but will return a dictionary of dict(object=attributes)
    This will handle multiple objects so be aware of your input
    valid inputs:
        object=object, attributes=[attributes]
        object=(object, [attributes]), attributes=None
        object=[(object, attribute), (object, attribute)]

    IN:
        [input] object
        [list]  attribute
        [bool]  listAttrIfEmpty, If True an empty list for attrs will be replaced with a listAttr
        [bool]  removeNone,      If True any objects with attributes as None will be removed

    OUT:
        [dict]  dict(object=attributes)
    '''
    def parseResults(results, listAttrIfEmpty=False, removeNone=False):
        items = dict()
        for obj, attrs in results.items():
            if removeNone and attrs is None:
                continue

            if listAttrIfEmpty and attrs is not None and not attrs:
                items[obj] = listAttr(obj)
                continue

            items[obj] = asList(attrs)

        return items

    results = dict()
    if not any([object, attributes]):
        return results

    # Check if correct inputs already passed
    if attributes:
        attributes = asList(attributes)
        if isType(object, [str]):
            if '.' in object:
                o, a = object.rsplit('.', 1)
                if not re.match('[0-9].*', a):
                    object = o

            object = asObject(object)
            results = {object: attributes}
            return parseResults(results, listAttrIfEmpty, removeNone)

        if isType(object, [list, tuple]):
            for item in object:
                results.update(parseObjectAttributes(item, attributes))

            return parseResults(results, listAttrIfEmpty, removeNone)

        if isType(object, [dict]):
            # No logical way to process this
            raise RuntimeError('Could not parseObjectAttributes({0}, {1})'.format(object, attributes))

        object = asObject(object)
        if object:
            results = {object: attributes}

        return parseResults(results, listAttrIfEmpty, removeNone)

    # attributes is None at this point
    # If object is not in str, list, tuple, dict, it cannot be parsed
    if isType(object, [str]):
        object, attribute = parseObjectAttribute(object, None)
        results = {object: asList(attribute, skipNoneType=True)}
        results = parseResults(results, listAttrIfEmpty, removeNone)
        return results

    if isType(object, [list]):
        for item in object:
            results.update(parseObjectAttributes(item, None))

        return parseResults(results, listAttrIfEmpty, removeNone)

    if isType(object, [tuple]):
        if len(object) == 2:
            results.update(parseObjectAttributes(object[0], object[1]))

        else:
            for item in object:
                results.update(parseObjectAttributes(item, None))

        return parseResults(results, listAttrIfEmpty, removeNone)

    if isType(object, [dict]):
        for key, value in object.items():
            results.update(parseObjectAttributes(key, value))

        return parseResults(results, listAttrIfEmpty, removeNone)

    node = asObject(object)
    if node:
        return parseResults({node: []}, listAttrIfEmpty, removeNone)

    raise RuntimeError('Could not parseObjectAttributes({0}, {1})'.format(object, attributes))


def getAttributePointer(object, attribute=None):
    '''
    This is used internally to store pointers to blenders custom attributes

    Required Parameters:
        [obj] object        : The object to operate on
        [str] attribute     : The attribute to query

    Out:
        [Ptr] pointer
    '''
    if attribute is None:
        attribute = resolveAttributeName(object)

    else:
        attribute = resolveAttributeName(attribute, object=object)

    if isType(attribute, [list, tuple]):
        raise RuntimeError('getAttributePointer does not support multiple attributes')

    if attribute in CONSTANTS.coreAttributes:
        return Ptr(object, attribute)

    if attribute in CONSTANTS.transformAttributes:
        attr, index = getAttributeIndex(attribute)
        return Ptr(object, attr, index)

    if attribute in object.keys():
        return Ptr(object, attribute)

    return None


def getAttr(object,
            attribute=None, at=None,
            keyable=None, k=None,
            lock=None, l=None,
            settable=None, s=None,
            time=None, t=None,
            type=None,
            evaluate=None, e=None,
            worldspace=None, ws=None,
            *args, **kwargs):
    '''
    Queries an attribute it's setting or value, default is to get the value

    Required Parameters:
        [obj] object        : The object to operate on
        [str] attribute/at  : The attribute to query

    Optional Parameters:
        [bool]  keyable/k      : Get the keyable state of the attribute
        [bool]  lock/l         : Get the locked state of the attribute
        [bool]  settable/s     : Get the settable state of the attribute
        [float] time/t         : Get the value at the specified time
        [bool]  type           : If True will return the type of attribute
        [bool]  evaluate/e     : If True will return the calculated value including constraints, default=True
                               : This is only useful for transform attributes
        [bool]  worldspace/ws  : If True will return the value in worldspace, default=False
                               : This is only useful for transform attributes

    Out:
        [value] value
    '''
    attribute = parseArgs(attribute, at, False)
    keyable = parseArgs(keyable, k, False)
    lock = parseArgs(lock, l, False)
    settable = parseArgs(settable, s, False)
    time = parseArgs(time, t, None)
    evaluate = parseArgs(evaluate, e, True)
    worldspace = parseArgs(worldspace, ws, False)
    result = None

    if isType(object, str) and '.' in object:
        object, attribute = object.rsplit('.', 1)

    object = asObject(object)

    if attribute is None:
        attribute = resolveAttributeName(object)

    else:
        attribute = resolveAttributeName(attribute, object=object)

    if isType(attribute, [list, tuple]):
        raise RuntimeError('getAttr does not support multiple attributes')

    if lock:
        if not attribute in CONSTANTS.transformAttributes:
            return False

        attr, index = getAttributeIndex(attribute)
        lockAttr = getattr(object, 'lock_{0}'.format(attr))
        return lockAttr[index]

    if attribute in CONSTANTS.coreAttributes:
        if settable:
            return True

        if keyable:
            return False

        result = getattr(object, attribute)

    if attribute in CONSTANTS.transformAttributes:
        if any([settable, keyable]):
            return bool(getDriver(object, attribute) is None)

        attr, index = getAttributeIndex(attribute)
        if evaluate:
            if worldspace:
                matrix = object.matrix_world

            else:
                matrix = object.matrix_local

            vector = getattr(matrix, CONSTANTS.matrixTransformAttrConversion.get(attr))()

        else:
            vector = getattr(object, attr)

        result = vector[index]

    if attribute in object.keys():
        if settable:
            return True

        result = object.get(attribute)

        if keyable:
            return bool(isType(result, [int, float]))

    if type:
        return type(result)

    return result


def setAttr(object,
            attribute=None,
            value=None, v=None,
            at=None,
            lock=None, l=None,
            *args, **kwargs):
    '''
    Sets an attribute value or state.

    Common Usage:
        setAttr(obj, 'translateX', 14)
        setAttr('pCube1.translateX', v=14)

    Required Parameters:
        [obj] object        : The object to operate on
        [str] attribute/at  : The attribute to query
        [str] value/v       : The value to set

    Optional Parameters:
        [bool] locked/l     : Get the locked state of the attribute
    '''
    attribute = parseArgs(attribute, at, False)
    value = parseArgs(value, v, None)
    lock = parseArgs(lock, l, None)

    if isType(object, str) and '.' in object:
        if value is None:
            value = attribute

        object, attribute = object.rsplit('.', 1)

    object = asObject(object)

    if attribute is None:
        attribute = resolveAttributeName(object)

    else:
        attribute = resolveAttributeName(attribute, object=object)

    if isType(attribute, [list, tuple]):
        raise RuntimeError('getAttr does not support multiple attributes')

    if lock is not None:
        if not attribute in CONSTANTS.transformAttributes:
            return False

        attr, index = getAttributeIndex(attribute)
        lockAttr = getattr(object, 'lock_{0}'.format(attr))
        lockAttr[index] = lock
        return True

    if getDriver(object, attribute):
        return False

    ptr = getAttributePointer(object, attribute)

    if not ptr:
        raise RuntimeError('Could not locate attribute {0}.{1}'.format(object.name, attribute))

    ptr.set(value)
    return True


def addAttr(object,
            attribute=None,
            defaultValue=None, dv=None,
            type = None,
            minValue=None, min=None,
            maxValue=None, max=None,
            *args, **kwargs):
    '''
    Adds an attribute to an object or node
    if a type is not specified the attribute type is considered to be a float
    valid types are int, float, string, vector. Although any python object is supported.

    Required Parameters:
        [obj] object              : The object to operate on
        [str] attribute           : The attribute to add

    Optional Parameters:
        [value] defaultValue/dv   : Default value for this attribute
        [str]  type               : Attribute Type, will guess if not specified
        [float] minValue/min      : Minimum value
        [float] maxValue/max      : Maximum value
    '''
    defaultValue = parseArgs(defaultValue, dv, False)
    minValue = parseArgs(minValue, min, False)
    maxValue = parseArgs(maxValue, max, False)
    defaultTypes = dict(int=0, float=0.0, string='', vector=(0.0, 0.0, 0.0, 0.0))
    if type not in defaultTypes:
        type = 'float'

    object = asObject(object)

    # We need this to set min and max values
    if not '_RNA_UI' in object.keys():
        object['_RNA_UI'] = dict()

    if not defaultValue:
        defaultValue = defaultTypes.get(type)

    object[attribute] = defaultValue
    if type in ['int', 'float']:
        object['_RNA_UI'][attribute] = dict(min=min, max=max)


def attributeQuery(attribute,
                   node=None, n=None,
                   exists=None, ex=None,
                   type=None,
                   keyable=None, k=None,
                   maxExists=None, mxe=None,
                   maximum=None, max=None,
                   minExists=None, mne=None,
                   minimum=None, min=None,
                   range=None, r=None,
                   *args, **kwargs):
    '''
    Queries settings of an attribute

    Required Parameters:
        [str] attribute           : The attribute to query
        [obj] node/n              : The object to operate on

    Optional Parameters:
        [bool] exists/ex          : Returns True if the attribute exists
        [bool] type               : Returns The type of attribute
        [bool] keyable/k          : Returns True if the attribute is keyable
        [bool] maxExists/mxe      : Returns True if this attribute has a maximum
        [bool] maximum/max        : Returns the maximum value for this attribute if it exists or None
        [bool] minExists/mne      : Returns True if this attribute has a minExists
        [bool] minimum/min        : Returns the minimum value for this attribute if it exists or None
        [bool] range/r            : Returns the range if it exists
    '''
    node = parseArgs(node, n, None)
    exists = parseArgs(exists, ex, False)
    keyable = parseArgs(keyable, k, False)
    maxExists = parseArgs(maxExists, mxe, False)
    maximum = parseArgs(maximum, max, False)
    minExists = parseArgs(minExists, mne, False)
    minimum = parseArgs(minimum, min, False)
    range = parseArgs(range, r, False)

    if not node:
        node, attribute = parseObjectAttribute(attribute, None)

    else:
        node, attribute = parseObjectAttribute(node, attribute)

    if not node:
        raise RuntimeError('{0} does not exist'.format(node))

    if not any([exists, keyable, maxExists, maximum, minExists, minimum, range]):
        raise RuntimeError('No flag specified to query')

    attribute = resolveAttributeName(attribute, object=node)

    if exists:
        return bool(attribute in listAttr(node))

    if keyable:
        return getAttr(node, attribute, keyable=True)

    # Check if min/max are set
    if '_RNA_UI' not in object.keys() or attribute not in object['_RNA_UI'].keys():
        if any([minExists, maxExists]):
            return False

        elif range:
            return (None, None)

        return None

    # Check that the data has been set correctly
    attrData = object['_RNA_UI'].get(attribute)
    if not attrData or not isType(attrData, [dict]):
        if any([minExists, maxExists]):
            return False

        elif range:
            return (None, None)

        return None

    min = attrData.get('min') or None
    max = attrData.get('max') or None

    if minExists:
        return bool(min is not None)

    if maxExists:
        return bool(max is not None)

    if minimum:
        return min

    if maximum:
        return max

    if range:
        return (min, max)

    return None


def connectAttr(source, target,
                force=None, f=None,
                removeExisting=None, re=None,
                *args, **kwargs):
    '''
    Connects two attributes together, currently this function only works with objects

    Required Parameters:
        [tuple] source            : The source as a tuple (obj, attribute) or string 'pCube1.translateX'
        [tuple] target            : The target as a tuple (obj, attribute) or string 'pCube1.translateX'

    Optional Parameters:
        [bool] force/f            : Forces the connection if the attribute is locked or already connected
        [bool] removeExisting/re  : If True will remove all existing variables
    '''
    # TODO At some point we will need to check if it is connected and error, currently it just doubles up
    force = parseArgs(force, f, False)
    removeExisting = parseArgs(removeExisting, re, False)
    sourceObject, sourceAttribute = parseObjectAttribute(source)
    targetObject, targetAttribute = parseObjectAttribute(target)

    if removeExisting:
        driver = getDriver(targetObject, targetAttribute)
        if driver:
            info = getDriverInfo(driver)
            for var in info['variables']:
                driver.driver.variables.remove(var['variable'])

    if not all([sourceObject, targetObject, sourceAttribute, targetAttribute]):
        error = 'invalid inputs: connectAttr(source={0}, target={1}, force={2})'.format(source, target, force)
        raise RuntimeError(error)

    driver = addDriver(sourceObject, sourceAttribute, idData=targetObject.id_data,
                       dataPath=targetAttribute, expression='var')
    driver.driver.type = 'SUM'

    return driver


def disconnectAttr(source, target=None, *args, **kwargs):
    '''
    disconnects attributes, If a only a source is specified, the entire driver is removed.
    For example:
        disconnectAttr( (Cube, 'locationX'), (Cube2, 'locationY') )
          will disconnect Cube.locationX from Cube2.locationY if it can

        disconnectAttr( (Cube, 'locationX') )
          will remove the driver attached to Cube.locationX

    Required Parameters:
        [tuple] source            : The source as a tuple (obj, attribute) or string 'pCube1.translateX'

    Optional Parameters:
        [tuple] target            : The target as a tuple (obj, attribute) or string 'pCube1.translateX'

    Out:
        [bool]  success           : True if a driver was removed, False if no driver found
    '''
    sourceObject, sourceAttribute = parseObjectAttribute(source)

    if not all([sourceObject, sourceAttribute]):
        raise RuntimeError('invalid inputs: disconnectAttr(source={0}, target={1})'.format(source, target))

    driver = getDriver(sourceObject, sourceAttribute)

    if not driver:
        return False

    # If we are not specifying a pair of attributes, remove the driver
    if target is None:
        sourceObject.driver_remove(driver.data_path, driver.array_index)
        return True

    targetObject, targetAttribute = parseObjectAttribute(target)
    if not all([targetObject, targetAttribute]):
        raise RuntimeError('invalid inputs: disconnectAttr(source={0}, target={1})'.format(source, target))

    info = getDriverInfo(driver)
    hasRemovedDriver = False
    for var in info['variables']:
        target = var['targets'].get(targetObject)
        if not target:
            continue

        if not target.get('attribute') == targetAttribute:
            continue

        driver.driver.variables.remove(var['variable'])
        hasRemovedDriver = True

    return hasRemovedDriver


def breakConnections(object, attribute,
                     includeAnimationCurves=None, iac=None,
                     *args, **kwargs):
    '''
    This will break off anything that is affecting this attribute

    Required Parameters:
        [Object] object
        [str]    attribute

    Optional Parameters:
        [bool]   includeAnimationCurves/iac : If False will not break an animation curve, default=True
    '''
    includeAnimationCurves = parseArgs(includeAnimationCurves, iac, True)
    object, attribute = parseObjectAttribute(object, attribute)
    if not attribute:
        return False

    # Let's remove any drivers if any
    disconnectAttr((object, attribute))

    # Remove any constraints if it is a transform attribute
    if attribute in CONSTANTS.transformAttributes:
        baseAttribute, index = getAttributeIndex(attribute)
        axis = CONSTANTS.attributeIndicesInverse[index].lower()
        # This will now only return constraints
        constraints = listConnections([{object: attribute}], includeConstraints=True)
        for constraint in constraints:
            if constraint.type == 'TRANSFORM':
                if not constraint.map_to_lower() == baseAttribute:
                    continue

                object.constraints.remove(constraint)
                continue

            if constraint.type == 'COPY_TRANSFORMS':
                object.constraints.remove(constraint)
                continue

            if constraint.type in ['FOLLOW_PATH', 'SHRINKWRAP', 'PIVOT']:
                if not baseAttribute in ['location', 'rotation']:
                    continue

                object.constraints.remove(constraint)
                continue

            if constraint.type in ['LIMIT_DISTANCE', 'FLOOR']:
                if not baseAttribute in ['location']:
                    continue

                object.constraints.remove(constraint)
                continue

            if hasattr(constraint, 'map_to') and constraint.map_to.lower() == axis:
                constraint.map_to = axis.upper()

            if hasattr(constraint, 'free_axis') and constraint.free_axis.lower().endswith(axis):
                object.constraints.remove(constraint)
                continue

            if hasattr(constraint, 'use_{0}_{1}'.format(baseAttribute, index)) and getattr(constraint, 'use_{0}_{1}'.format(baseAttribute, index)):
                setattr(constraint, 'use_{0}_{1}'.format(baseAttribute, index), False)

            if hasattr(constraint, 'use_min_{0}'.format(index)) and getattr(constraint, 'use_min_{0}'.format(index)):
                setattr(constraint, 'use_min_{0}'.format(index), False)

            if hasattr(constraint, 'use_max_{0}'.format(index)) and getattr(constraint, 'use_max_{0}'.format(index)):
                setattr(constraint, 'use_max_{0}'.format(index), False)

            if hasattr(constraint, 'use_{0}'.format(index)) and getattr(constraint, 'use_{0}'.format(index)):
                setattr(constraint, 'use_{0}'.format(index), False)

    # Now we can remove animation curves
    if not includeAnimationCurves:
        return True

    animationCurve = getFCurve(object, attribute)
    if animationCurve:
        object.animation_data.action.fcurves.remove(animationCurve)

    return True


def listConnections(connections=None,
                    desitination=None, d=None,
                    source=None, s=None,
                    plugs=None, p=None,
                    drivers=None, dr=None,
                    type=None, t=None,
                    includeAnimationCurves=None, iac=None,
                    includeConstraints=None, ic=None,
                    *args, **kwargs):
    '''
    Lists any objects connected to the specified objects
    connections can be a list of strings ['pCube1.translateX'] or a list of tuples [(object, attribute) or multi-attribuet [(object, [attr, attr])]
    Do note that unlike in Maya, in Blender an attribute may have more than one source connection
    If getting plugs the results will be a list of tuples

    Optional Parameters:
        [list] connections            : connections to query, uses selection if not specified
        [bool] desitination/d         : lists only desitination plugs
        [bool] source/s               : lists only source plugs, default=True
        [bool] plugs/p                : Returns dicts of (object, attr), default=False
        [bool] drivers/dr             : if true will return drivers
        [str]  type/t                 : if true will return objects matching this type
    '''
    def getDrivers(obj, attr=None, source=False, desitination=False, plugs=False,
                   returnDrivers=True, allDrivers=None):
        drivers = []
        if source:
            driver = getDriver(obj, attr)
            if driver:
                item = driver
                info = getDriverInfo(driver)
                if not returnDrivers:
                    item = info.get('object')

                if plugs:
                    drivers.append(info['source'])

                else:
                    drivers.append(item)


        if not desitination:
            return drivers

        for driverInfo in allDrivers:
            for source, sourceAttr in driverInfo['source'].items():
                if not source == obj:
                    continue

                if not fi(sourceAttr) == attr:
                    continue

                item = driverInfo['object']
                if returnDrivers:
                    item = driverInfo['driver']

                if plugs:
                    drivers.append({driverInfo['object']: driverInfo['attribute']})

                else:
                    drivers.append(item)

                break

        return [d for d in drivers if d]

    def getTransformConstraints(obj):
        axis = dict(x=[], y=[], z=[])
        allConstraints=dict(location=axis, rotation=axis, scale=axis)
        for constraint in obj.constraints:
            if constraint.mute:
                continue

            if constraint.type == 'TRANSFORM':
                allConstraints[constraint.map_to.lower()]['x'].append(constraint)
                allConstraints[constraint.map_to.lower()]['y'].append(constraint)
                allConstraints[constraint.map_to.lower()]['z'].append(constraint)
                continue

            if constraint.type == 'COPY_TRANSFORMS':
                allConstraints['location']['x'].append(constraint)
                allConstraints['location']['y'].append(constraint)
                allConstraints['location']['z'].append(constraint)
                allConstraints['rotation']['x'].append(constraint)
                allConstraints['rotation']['y'].append(constraint)
                allConstraints['rotation']['z'].append(constraint)
                allConstraints['scale']['x'].append(constraint)
                allConstraints['scale']['y'].append(constraint)
                allConstraints['scale']['z'].append(constraint)
                continue

            if constraint.type in ['FOLLOW_PATH', 'SHRINKWRAP', 'PIVOT']:
                allConstraints['location']['x'].append(constraint)
                allConstraints['location']['y'].append(constraint)
                allConstraints['location']['z'].append(constraint)
                allConstraints['rotation']['x'].append(constraint)
                allConstraints['rotation']['y'].append(constraint)
                allConstraints['rotation']['z'].append(constraint)
                continue

            if constraint.type in ['LIMIT_DISTANCE', 'FLOOR']:
                allConstraints['location']['x'].append(constraint)
                allConstraints['location']['y'].append(constraint)
                allConstraints['location']['z'].append(constraint)
                continue

            if constraint.type == 'MAINTAIN_VOLUME':
                if constraint.owner_space == 'LOCAL':
                    for axis in ['x', 'y', 'z']:
                        if not constraint.free_axis.lower().endswith(axis):
                            continue

                        allConstraints['scale'][axis].append(constraint)

                else:
                    allConstraints['scale']['x'].append(constraint)
                    allConstraints['scale']['y'].append(constraint)
                    allConstraints['scale']['z'].append(constraint)
                continue

            if constraint.type == 'CHILD_OF':
                for attr in ['location', 'rotation', 'scale']:
                    for axis in ['x', 'y', 'z']:
                        if getattr(constraint, 'use_{0}_{1}'.format(attr, axis)):
                            allConstraints[attr][axis].append(constraint)
                continue

            for attr in ['location', 'rotation', 'scale']:
                if constraint.type == 'LIMIT_{0}'.format(attr.upper()):
                    for axis in ['x', 'y', 'z']:
                        if getattr(constraint, 'use_min_{0}'.format(axis)) or getattr(constraint, 'use_max_{0}'.format(axis)):
                            allConstraints[attr][axis].append(constraint)

                if constraint.type == 'COPY_{0}'.format(attr.upper()):
                    for axis in ['x', 'y', 'z']:
                        if getattr(constraint, 'use_{0}'.format(axis)):
                            allConstraints[attr][axis].append(constraint)

        return allConstraints

    desitination = parseArgs(desitination, d, False)
    source = parseArgs(source, s, False)
    plugs = parseArgs(plugs, p, False)
    drivers = parseArgs(drivers, dr, False)
    type = parseArgs(type, t, None)
    includeAnimationCurves = parseArgs(includeAnimationCurves, iac, False)
    includeConstraints = parseArgs(includeConstraints, ic, False)

    if type in ['fcurve', 'animCurve']:
        type = bpy.types.FCurve

    results = []

    if not any([desitination, source]):
        source = True

    if connections is None:
        connections = ls(sl=1)

    if not connections:
        return []

    allDrivers = None
    if desitination:
        allDrivers = [getDriverInfo(driver) for driver in ls(type=bpy.types.Driver, gpc=True)]

    connections = parseObjectAttributes(connections, listAttrIfEmpty=True, removeNone=True)
    for obj, attrs in connections.items():
        if not type == bpy.types.FCurve:
            drivers = []
            for attr in attrs:
                drivers += getDrivers(obj, attr, source, desitination, plugs=plugs,
                                      returnDrivers=drivers, allDrivers=allDrivers)

            results += drivers

        if includeAnimationCurves or type == bpy.types.FCurve:
            curves = []
            for attr in attrs:
                curve = getFCurve(obj, attr)
                if not curve:
                    continue

                curves.append(getFCurve(obj, attr))

            results += curves

        if includeConstraints:
            constraints = []
            allConstraints = getTransformConstraints(obj)

            for attr in attrs:
                attr, index = getAttributeIndex(attr)
                if attr not in allConstraints.keys():
                    continue

                axis = ['x', 'y', 'z'][index]
                if axis not in allConstraints[attr]:
                    continue

                if plugs:
                    for constraint in allConstraints[attr][axis]:
                        constraints.append({constraint: []})

                else:
                    constraints += allConstraints[attr][axis]

            results += constraints

    # TODO: Filter out certain types

    if plugs:
        items = {}
        for item in results:
            obj, attrs = fi(list(item.items()))
            if obj in items.keys():
                items[obj] += asList(attrs)

            else:
                items[obj] = asList(attrs)

            items[obj] = list(set(items[obj]))

        results = [(obj, items[obj]) for obj in items.keys()]

    else:
        results = list(set(results))

    return results


def bakeSimulation(objects=None, attribute=None,
                   startTime=None, st=None,
                   endTime=None, et=None,
                   step=None, s=None,
                   *args, **kwargs):
    '''
    This will bake down the data for an attribute and break any connections it may have.
    WARNING: Currently this is quite destructive, it will remove constraints and drivers
             affecting the attributes, save your scene first

    Optional Parameters:
        [obj] objects      : Object or objects to query, optionally a list of tuples of object attribute pairs
        [str] attribute    : The attribute or list of attributes to keyframe, Not used if objects is a list of tuples
        [int] startTime/st : Time to start baking from, default=TimeSlider
        [int] endTime/et   : Time to end baking, default=TimeSlider
        [int] step/s       : Time to increment between frames, default=1
    '''
    startTime = parseArgs(startTime, st, playbackOptions(min=True, query=True))
    endTime = parseArgs(endTime, et, playbackOptions(max=True, query=True))
    step = parseArgs(step, s, 1) or 1
    objects = parseObjectAttributes(objects, attribute, listAttrIfEmpty=True, removeNone=True)
    objectData = dict()
    frame = startTime

    currentFrame = currentTime(q=1)

    # Gather data first
    while frame <= endTime:
        currentTime(frame)
        bpy.context.scene.update()
        for object, attributes in objects.items():
            if object not in objectData.keys():
                objectData[object] = dict()

            for attribute in attributes:
                if attribute not in objectData[object].keys():
                    objectData[object][attribute] = dict()

                value = getAttr(object, attribute)

                objectData[object][attribute][frame] = value

        frame += step

    # we are using cutKey, so let's make sure we leave the key copy buffer intact
    global COPY_KEY_BUFFER
    keyBuffer = COPY_KEY_BUFFER
    for object, attributes in objectData.items():
        for attribute, keyInfo in attributes.items():
            # Let's break off all connections for this attribute.
            breakConnections(object, attribute, includeAnimationCurves=False)
            # In the case that there is animation, we want to cut it, not remove it
            animationCurve = getFCurve(object, attribute)
            if animationCurve:
                cutKey(object, attribute, time=(startTime, endTime))

            for key, value in keyInfo.items():
                setKeyframe(object, attribute, time=key, value=value)

    currentTime(currentFrame)
    COPY_BUFFER = keyBuffer


def warning(msg, *args, **kwargs):
    '''
    Prints a warning to the UI and continues to run

    Required Parameters:
        [str] msg                     : The message to display
    '''
    print(msg)
    bpy.ops.info.display_message(report_type='WARNING', report_message=msg)


def displayInfo(msg, *args, **kwargs):
    '''
    Prints a message to the UI and continues to run

    Required Parameters:
        [str] msg                     : The message to display
    '''
    print(msg)
    bpy.ops.info.display_message(report_type='INFO', report_message=msg)


def error(msg, *args, **kwargs):
    '''
    Prints an error to the UI and terminates

    Required Parameters:
        [str] msg                     : The message to display
    '''
    print(msg)
    bpy.ops.info.display_message(report_type='ERROR', report_message=msg)
    raise RuntimeError(msg)


def transform(translate=None, rotate=None, scale=None,
              object=None,
              relative=None, r=None,
              absolute=None, a=None,
              worldSpace=None, ws=None,
              objectSpace=None, os=None):
    '''
    Transform the object or objects, by default this is a relative trasformation
    if no object is specified it will use the selection

    Optional Parameters:
        [tuple] translate             : vector3 array to translate
        [tuple] rotate                : vector3 array to rotate
        [tuple] scale                 : vector3 array to scale
        [obj]   object                : Object or list of objects to move
        [bool]  relative/r            : If True will move relative to current location
        [bool]  absolute/a            : If True will move to the absolute values
        [bool]  worldSpace/ws         : Move relative to World
        [bool]  objectSpace/os        : Move relative to object
    '''
    def validifyVector(vector):
        if not vector:
            vector = [0, 0, 0]

        elif isType(vector, [int, float]):
            vector = [vector, vector, vector]

        elif not hasattr(vector, '__len__') or not len(vector) == 3:
            raise RuntimeError('Invalid vectorArray3: {0}'.format(vector))

        return list(vector)

    def mergeTuples(a, b, absolute=False):
        a = validifyVector(a)
        b = validifyVector(b)

        for i, value in enumerate(b):
            if absolute:
                a[i] = a[i] if value is None else value

            else:
                a[i] += value or 0

        return a

    relative = parseArgs(relative, r, False)
    absolute = parseArgs(absolute, a, False)
    worldSpace = parseArgs(worldSpace, ws, False)
    objectSpace = parseArgs(objectSpace, os, False)
    objects = ls(sl=1) if object is None else asObjects(asList(object), forceObjects=True)
    if not objects:
        return

    for obj in objects:
        matrix = obj.matrix_world if worldSpace else obj.matrix_local

        for vector, attr in {translate: 'translation', rotate: 'rotation', scale: 'scale'}.items():
            if vector is not None:
                value = mergeTuples(getattr(matrix, attr), vector, absolute=absolute)
                setattr(matrix, attr, value)

        obj.data.update()


def move(x=None, y=None, z=None,
         object=None,
         relative=None, r=None,
         absolute=None, a=None,
         worldSpace=None, ws=None,
         objectSpace=None, os=None):
    '''
    Moves the object or objects
    if no object is specified it will use the selection

    Optional Parameters:
        [float] x                     : distance to move in X
        [float] y                     : distance to move in y
        [float] z                     : distance to move in z
        [obj]   object                : Object or list of objects to move
        [bool]  relative/r            : If True will move relative to current location
        [bool]  absolute/a            : If True will move to the absolute values
        [bool]  worldSpace/ws         : Move relative to World
        [bool]  objectSpace/os        : Move relative to object
    '''
    relative = parseArgs(relative, r, False)
    absolute = parseArgs(absolute, a, False)
    worldSpace = parseArgs(worldSpace, ws, False)
    objectSpace = parseArgs(objectSpace, os, False)
    return transform(translate=(x, y, z), object=object,
                     relative=relative, absolute=absolute,
                     worldSpace=worldSpace, objectSpace=objectSpace)


def rotate(x=None, y=None, z=None,
           object=None,
           relative=None, r=None,
           absolute=None, a=None,
           worldSpace=None, ws=None,
           objectSpace=None, os=None,
           pivot=None, p=None,
           centerPivot=None, cp=None,
           objectCenterPivot=None, ocp=None):
    '''
    Rotate the object or objects
    if no object is specified it will use the selection

    Optional Parameters:
        [float] x                     : distance to rotate in X
        [float] y                     : distance to rotate in y
        [float] z                     : distance to rotate in z
        [obj]   object                : Object or list of objects to rotate
        [bool] relative/r             : If True will rotate relative to current location
        [bool] absolute/a             : If True will rotate to the absolute values
        [bool] worldSpace/ws          : Move relative to World
        [tuple] pivot/p               : Pivot to rotate around
        [bool] centerPivot/cp         : if True will rotate around the center of all objects
        [bool] objectCenterPivot/ocp  : if True each object will rotate around it's own pivot
    '''
    relative = parseArgs(relative, r, False)
    absolute = parseArgs(absolute, a, False)
    worldSpace = parseArgs(worldSpace, ws, False)
    objectSpace = parseArgs(objectSpace, os, False)
    return transform(rotate=(x, y, z), object=object,
                     relative=relative, absolute=absolute,
                     worldSpace=worldSpace, objectSpace=objectSpace)


def scale(x=None, y=None, z=None,
          object=None,
          relative=None, r=None,
          absolute=None, a=None,
          worldSpace=None, ws=None,
          objectSpace=None, os=None,
          pivot=None, p=None,
          centerPivot=None, cp=None,
          objectCenterPivot=None, ocp=None):
    '''
    Scale the object or objects
    if no object is specified it will use the selection

    Optional Parameters:
        [float] x                     : distance to scale in X
        [float] y                     : distance to scale in y
        [float] z                     : distance to scale in z
        [obj]   object                : Object or list of objects to scale
        [bool] relative/r             : If True will scale relative to current location
        [bool] absolute/a             : If True will scale to the absolute values
        [bool] worldSpace/ws          : Move relative to World
        [tuple] pivot/p               : Pivot to scale around
        [bool] centerPivot/cp         : if True will scale around the center of all objects
        [bool] objectCenterPivot/ocp  : if True each object will scale around it's own pivot
    '''
    relative = parseArgs(relative, r, False)
    absolute = parseArgs(absolute, a, False)
    worldSpace = parseArgs(worldSpace, ws, False)
    objectSpace = parseArgs(objectSpace, os, False)
    return transform(scale=(x, y, z), object=object,
                     relative=relative, absolute=absolute,
                     worldSpace=worldSpace, objectSpace=objectSpace)


def group(objects=None,
          name=None, n=None,
          empty=None, em=None,
          relative=None, r=None):
    '''
    Group the objects under a locator

    Optional Parameters:
        [obj]  objects                : Object or list of objects to group
        [str]  name/n                 : Name for the group
        [bool] empty/em               : If True will create an empty group
        [bool] relative/r             : If True will preserve existing transformations

    OUT:
        [obj]  empty
    '''
    name = parseArgs(name, n, None)
    empty = parseArgs(empty, em, False)
    relative = parseArgs(relative, r, None)

    loc = createLocator(name=name)

    bpy.context.scene.objects.active = loc
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=bool(relative))
    if not objects and not empty:
        objects = ls(sl=1)

    if not empty and objects:
        parent(objects, loc, relative=relative)

    return loc


def objExists(object):
    '''
    Checks if an object exists

    Required Parameters:
        [obj]  object                 : The object to query
    '''
    obj = asObject(object, forceObjects=True)
    return bool(obj is not None)


def delete(objects):
    '''
    deletes the specified object, objects, component, shape, library, etc
    CURRENTLY THIS DOES NOT SUPPORT COMPONENTS

    Required Parameters:
        [list] objects                 : The objects to delete
    '''
    objects = asObjects(objects, forceObjects=False)
    # Gather the data into ordered sets to make sure we delete things in the correct order.
    data = od()
    data['skipped'] = []
    data['ignored'] = []
    data['keys'] = []
    data['drivers'] = []
    data['fcurves'] = []
    data['modifiers'] = []
    data['constraints'] = []
    # data['components'] = []
    data['data'] = []
    data['objects'] = []
    for item in objects:
        if item in list(bpy.data.objects):
            data['objects'].append(item)
            continue

        if type(item) in CONSTANTS.baseTypeDict.keys():
            data['data'].append(item)
            continue

        if type(item).__name__.endswith('Constraint'):
            data['constraints'].append(item)
            continue

        if type(item).__name__.endswith('Modifier'):
            data['modifiers'].append(item)
            continue

        if type(item) == bpy.types.FCurve:
            if item.driver:
                data['drivers'].append(item.driver)
                # Once we remove the driver the animCurve is also disconnected
                # so we won't add both for drivers

            else:
                data['fcurves'].append(item)

            continue

        if type(item) == bpy.types.Driver:
            data['drivers'].append(item.driver)
            continue

        if type(item) == bpy.types.Keyframe:
            data['keys'].append(item)
            continue

        data['ignored'].append(item)

    # Remove items where applicable
    for key in data['keys']:
        # Get the curve, I know this seems slow, but Blender is fast at this
        # Don't use a try except here is it crashes Blender
        keyCurve = None
        for curve in key.id_data.action.fcurves:
            if key in list(curve.keyframe_points):
                keyCurve = curve
                break

        if not keyCurve:
            data['skipped'].append(key)
            continue

        keyCurve.keyframe_points.remove(key)

    for driver in data['drivers']:
        driverCurve = None
        for curve in list(driver.id_data.animation_data.drivers):
            if curve.driver == driver:
                driverCurve = curve
                break

        if not driverCurve:
            data['skipped'].append(driver)
            continue

        driver.id_data.driver_remove(curve.data_path, curve.array_index)

    for itemType in ['fcurves', 'modifiers', 'constraints']:
        for item in data[itemType]:
            allItems = getattr(item.id_data, itemType)
            if item not in list(allItems):
                data['skipped'].append(item)
                continue

            allItems.remove(item)

    for item in data['data']:
        collection = CONSTANTS.baseTypeDict.get(type(item))
        if not collection:
            data['skipped'].append(item)
            continue

        item.user_clear()
        collection.remove(item)

    for item in data['objects']:
        itemData = item.data
        if itemData.users <= 1:
            collection = CONSTANTS.baseTypeDict.get(type(itemData))
            if collection:
                itemData.user_clear()
                collection.remove(itemData)

        for scene in item.users_scene:
            scene.objects.unlink(item)

        bpy.data.objects.remove(item)

    if data['ignored']:
        print('Skipped deletion of unsupported items:')
        print('\t{0}'.format(data['ignored']))

    if data['skipped']:
        print('Skipped deletion of items without data to delete from:')
        print('\t{0}'.format(data['skipped']))


def fullConstraint(target, source,
                   name=None, n=None,
                   weight=None, w=None,
                   skip=None, s=None,
                   maintainOffset=None, mo=None):
    '''
    Constrains all the targets specified in taget to the source object,
    Translate and Rotate and Scale are constrained.
    Due to the nature of Blender's constraint system, this will return a list of constraints

    Required Parameters:
        [obj]   target                 : Target or Targets to constrain
        [obj]   source                 : The object to constrain to

    Optional Parameters:
        [float] weight/w               : Influence effect, default=1.0
        [list]  skip/s                 : A list of attributes to not constrain, default=None
        [bool]  maintainOffset/mo      : If True will leave the object in it's current position, default=False

    OUT:
        [list] constraints
    '''
    def createConstraint(source, target, type=None, skip=None, maintainOffset=False, weight=1.0, name=None):
        '''
        This function is used to create the actual constraint and set up the attributes.
        Same inputs as parent function
        '''
        source = asObject(source)
        target = asObject(target)
        type = type or CONSTANTS.constraints.get('point')
        skip = [str(a).lower() for a in asList(skip) if str(a).lower() in ['x', 'y', 'z']]

        constraint = source.constraints.new(type)
        constraint.target = target
        constraint.influence = weight

        if maintainOffset:
            constraint.target_space = 'LOCAL'
            constraint.owner_space = 'LOCAL'

        if name:
            constraint.name = name

        # Attempt to disable axis if they exist
        for axis in skip:
            attr = 'use_{0}'.format(axis)
            if not hasattr(constraint, attr):
                continue

            setattr(constraint, attr, False)

        return constraint

    def resolveAttrs(attrs):
        '''
        Take a list of transform attributes and return a dictionary of {'translate': ['X', 'Y', 'Z']}

        IN:
            [list] attrs

        OUT:
            [dict] attrs
        '''
        attrs = list(set(asList(attrs)))
        attrs = resolveAttributeNames(attrs, transforms=True)
        axis = dict()
        for attr in attrs:
            m = attr[:-1]
            if m not in axis.keys():
                axis[m] = [attr[-1]]

            axis[attr[:-1]].append(attr[-1])

        return axis


    name = parseArgs(name, n, None)
    weight = parseArgs(weight, n, 1.0)
    skip = parseArgs(skip, s, None)
    maintainOffset = parseArgs(maintainOffset, mo, None)
    skip = resolveAttrs(skip)

    source = asObject(source)
    target = asObject(target)

    constraints = []

    for attr, axis in skip.items():
        if len(axis) == 3:
            continue

        constraintType = CONSTANTS.constraints.get(attr)
        if not constraintType:
            continue

        constraint = createConstraint(source, target, type=constraintType, skip=axis,
                                      maintainOffset=maintainOffset, weight=weight, name=name+'_'+attr)
        constraints.append(constraint)

    return constraint


def parentConstraint(target, source,
                     name=None, n=None,
                     weight=None, w=None,
                     skip=None, s=None,
                     maintainOffset=None, mo=None):
    '''
    Constrains all the targets specified in taget to the source object,
    Translate and Rotate are constrained, Scale is ignored

    Required Parameters:
        [obj]   target                 : Target or Targets to constrain
        [obj]   source                 : The object to constrain to

    Optional Parameters:
        [float] weight/w               : Influence effect, default=1.0
        [list]  skip/s                 : A list of attributes to not constrain, default=None
        [bool]  maintainOffset/mo      : If True will leave the object in it's current position, default=False

    OUT:
        [list] constraints
    '''
    name = parseArgs(name, n, None)
    weight = parseArgs(weight, n, None)
    skip = parseArgs(skip, s, None)
    maintainOffset = parseArgs(maintainOffset, mo, None)
    skip = list(set(asList(skip) + ['scaleX', 'scaleY', 'scaleZ']))
    return fullConstraint(target, source, name=name, weight=weight,
                          skip=skip, maintainOffset=maintainOffset)


def orientConstraint(target, source,
                     name=None, n=None,
                     weight=None, w=None,
                     skip=None, s=None,
                     maintainOffset=None, mo=None):
    '''
    Constrains all the targets specified in taget to the source object,
    Only Rotation in constrained

    Required Parameters:
        [obj]   target                 : Target or Targets to constrain
        [obj]   source                 : The object to constrain to

    Optional Parameters:
        [float] weight/w               : Influence effect, default=1.0
        [list]  skip/s                 : A list of attributes to not constrain, default=None
        [bool]  maintainOffset/mo      : If True will leave the object in it's current position, default=False

    OUT:
        [list] constraints
    '''
    name = parseArgs(name, n, None)
    weight = parseArgs(weight, n, None)
    skip = parseArgs(skip, s, None)
    maintainOffset = parseArgs(maintainOffset, mo, None)
    skip = list(set(asList(skip) + ['locationX', 'locationY', 'locationZ', 'scaleX', 'scaleY', 'scaleZ']))
    return fullConstraint(target, source, name=name, weight=weight,
                          skip=skip, maintainOffset=maintainOffset)


def pointConstraint(target, source,
                     name=None, n=None,
                     weight=None, w=None,
                     skip=None, s=None,
                     maintainOffset=None, mo=None):
    '''
    Constrains all the targets specified in taget to the source object,
    Only Translation is constrained

    Required Parameters:
        [obj]   target                 : Target or Targets to constrain
        [obj]   source                 : The object to constrain to

    Optional Parameters:
        [float] weight/w               : Influence effect, default=1.0
        [list]  skip/s                 : A list of attributes to not constrain, default=None
        [bool]  maintainOffset/mo      : If True will leave the object in it's current position, default=False

    OUT:
        [list] constraints
    '''
    name = parseArgs(name, n, None)
    weight = parseArgs(weight, n, None)
    skip = parseArgs(skip, s, None)
    maintainOffset = parseArgs(maintainOffset, mo, None)
    skip = list(set(asList(skip) + ['rotationX', 'rotationY', 'rotationZ', 'scaleX', 'scaleY', 'scaleZ']))
    return fullConstraint(target, source, name=name, weight=weight,
                          skip=skip, maintainOffset=maintainOffset)


def scaleConstraint(target, source,
                     name=None, n=None,
                     weight=None, w=None,
                     skip=None, s=None,
                     maintainOffset=None, mo=None):
    '''
    Constrains all the targets specified in taget to the source object,
    Only Scale is constrained

    Required Parameters:
        [obj]   target                 : Target or Targets to constrain
        [obj]   source                 : The object to constrain to

    Optional Parameters:
        [float] weight/w               : Influence effect, default=1.0
        [list]  skip/s                 : A list of attributes to not constrain, default=None
        [bool]  maintainOffset/mo      : If True will leave the object in it's current position, default=False

    OUT:
        [list] constraints
    '''
    name = parseArgs(name, n, None)
    weight = parseArgs(weight, n, None)
    skip = parseArgs(skip, s, None)
    maintainOffset = parseArgs(maintainOffset, mo, None)
    skip = list(set(asList(skip) + ['rotationX', 'rotationY', 'rotationZ', 'locationX', 'locationY', 'locationZ']))
    return fullConstraint(target, source, name=name, weight=weight,
                          skip=skip, maintainOffset=maintainOffset)


def lookThru(camera=None,
             query=None, q=None):
    '''
    Sets or queries the active viewport camera

    Optional Parameters:
        [obj]   camera                 : Camera to set
        [bool]  query/q                : If True will return the name of the active camera, default=False
    '''
    query = parseArgs(query, q, False)
    if query:
        return bpy.context.camera

    cam = asObject(camera)
    if not cam:
        raise RuntimeError('Camera does not exist: {0}'.format(camera))

    if not cam.type == 'CAMERA':
        raise RuntimeError('Object is not a camera: {0}'.format(camera))

    bpy.context.camera = cam


def currentTime(frame=None,
                update=None, u=None,
                query=None, q=None):
    '''
    Sets or queries the current frame

    Optional Parameters:
        [float] frame                  : Will change the active frame to this frame
        [bool]  update/u               : If True will update the scene when changing, default=True
        [bool]  query/q                : If True will return the current frame, default=False
    '''
    update = parseArgs(update, u, True)
    query = parseArgs(query, q, False)
    if query:
        return bpy.context.scene.frame_current

    if frame is not None:
        if update:
            bpy.context.scene.frame_set(frame)

        else:
            bpy.context.scene.frame_current = frame


def keyframe(objects=None,
             index=None,
             time=None, t=None,
             absolute=None, a=None,
             relative=None, r=None,
             timeChange=None, tc=None,
             valueChange=None, vc=None,
             indexValue=None, iv=None,
             keyframeCount=None, kc=None,
             eval=None, ev=None,
             selected=None, sl=None,
             lastSelected=None, lsl=None,
             keys=None, k=None,
             query=None, q=None):
    '''
    This function is used to query or manipulate animation curves.
    If no objects are specified it will use the selection

    Optional Parameters:
        [obj]   objects                : List of objects to operate on, or a list of tuples of object, attributes (obj, [attr])
        [tuple] time/t                 : Time range to operate or query
        [bool]  absolute/a             : If True will operate in absolute values
        [bool]  relative/r             : If True will operate in relative values
        [float] timeChange/tc          : How far to move the curve in time (X-axis)
        [float] valueChange/vc         : How far to move the curve in value (Y-axis)
        [bool]  indexValue/iv          : If True will return the indices instead of time values.
        [bool]  eval/ev                : If True Will return values for the keys instead of time values
        [bool]  selected/sl            : If True Will return or operate on selected keys
        [bool]  keys/k                 : If True Will return a dictionary of key:curve, intended for diagnostics
        [bool]  lastSelected/lsl       : If True Will return or operate on the last selected key only
        [bool]  query/q                : If True will operate in query mode
    '''
    def getKeys(curves, time=None, selected=False, lastSelected=False):
        if time is not None:
            time = parseDouble(time)

        results = od()
        for curve in curves:
            for key in curve.keyframe_points:
                if time is not None:
                    if not time[0] < key.co[0] < time[1]:
                        continue

                if (selected or lastSelected) and not key.select_control_point:
                    continue

                results[key] = curve

        if lastSelected:
            key = li(list(results.keys())[0])
            if key is None:
                return od()

            value = results[key]
            results = od()
            results[key] = value

        return results

    def offsetKey(key, index, value, absolute):
        v = key.co[index]
        left = key.handle_left[index]
        right = key.handle_right[index]
        if absolute:
            vc = v - value
            time = value
            left = left - vc
            right = right - vc

        else:
            time = v + value
            left = left + value
            right = right + value

        key.co[index] = time
        key.handle_left[index] = left
        key.handle_right[index] = right

    time = parseArgs(time, t, None)
    absolute = parseArgs(absolute, a, None)
    relative = parseArgs(relative, r, None)
    timeChange = parseArgs(timeChange, tc, None)
    valueChange = parseArgs(valueChange, vc, None)
    indexValue = parseArgs(indexValue, iv, None)
    keyframeCount = parseArgs(keyframeCount, kc, None)
    eval = parseArgs(eval, ev, None)
    selected = parseArgs(selected, sl, None)
    lastSelected = parseArgs(lastSelected, lsl, None)
    returnKeys = parseArgs(keys, k, False)
    query = parseArgs(query, q, False)

    if objects is None:
        objects = ls(sl=1)

    if not objects:
        return dict() if returnKeys else list()

    if query and not any([valueChange, timeChange, indexValue, keyframeCount, eval]):
        timeChange = True

    curves = getFCurves(objects)

    if not curves:
        if query:
            return dict() if returnKeys else list()

        else:
            return False

    results = []

    keys = getKeys(curves, time=time, selected=selected, lastSelected=lastSelected)
    if returnKeys and query:
        return keys

    if query:
        if indexValue:
            for curve in curves:
                pts = list(curve.keyframe_points)
                print(pts)
                results += [pts.index(key) for key in pts if key in keys]

        if keyframeCount:
            return len(keys.keys())

        if timeChange:
            results += [key.co[0] for key in keys.keys()]

        if valueChange:
            results += [key.co[1] for key in keys.keys()]

        if eval:
            results += [curve.evaluate(key.co[0]) for key, curve in keys.items()]

        return results

    doTimeChange = bool(not timeChange in [False, None])
    doValueChange = bool(not valueChange in [False, None])
    if not any([doTimeChange, doValueChange]):
        return False

    timeChange = asFloat(timeChange)
    valueChange = asFloat(valueChange)
    for key in keys.keys():
        if doTimeChange:
            offsetKey(key, 0, timeChange, absolute)

        if doValueChange:
            offsetKey(key, 1, valueChange, absolute)

    return True


def copyKey(objects,
            attribute=None, at=None,
            time=None, t=None,
            value=None, v=None,
            cut=None, c=None,
            *args, **kwargs):
    '''
    This function is used Copy keyframes to the keyframe buffer
    If a curve is provided it will be added to the curves portion of the stored results

    Optional Parameters:
        [obj]   objects                : Object or objects to query, optionally a list of tuples of object attribute pairs
        [str]   attribute/at           : The attribute or list of attributes to keyframe, Not used if objects is a list of tuples
        [float] time/t                 : The time or time range to query, default = all keys
        [float] value/v                : The value or value range to query
        [bool]  cut/c                  : If True will delete the keys after copying, default=False

    OUT:
        [dict] keys copied to buffer

    Format:
        {
            object : {
                attribute: [keys]
            }
            'curves': {
                curve: [keys]
            }
        }
    '''
    def getKeyInfo(curve, time=None, cut=None):
        keyData = keyframe(curves, time=time, keys=True, query=True)
        results = []

        for key in list(keyData.keys()):
            if time is not None and not (time[0] <= key.co[1] <= time[1]):
                continue

            item = dict(key=key, curve=curve)
            for value in ['handle_left_type', 'handle_right_type', 'interpolation']:
                item[value] = getattr(key, value)

            for value in ['co', 'handle_left', 'handle_right']:
                item[value] = tuple(getattr(key, value))

            results.append(item)

        if cut not in [None, False, 0]:
            for item in results:
                key = item.get('key')
                if key not in curve.keyframe_points:
                    continue

                curve.keyframe_points.remove(key)

        return results

    global COPY_KEY_BUFFER
    attribute = parseArgs(attribute, at, None)
    time = parseArgs(time, t, None)
    value = parseArgs(value, v, None)
    cut = parseArgs(cut, c, False)

    if time is not None:
        time = parseDouble(time)

    if objects is None:
        objects = ls(sl=1)

    results = od()
    results['curves'] = od()
    results['data'] = od()

    curves = []
    if isType(objects, bpy.types.FCurve):
        curves = [objects]

    elif isType(objects, [list, tuple]):
        curves = [c for c in objects if isType(c, [bpy.types.FCurve])]

    if curves:
        for curve in curves:
            keyInfo = getKeyInfo(curve)
            results['curves'][curve] = keyInfo

    data = parseObjectAttributes(objects, attributes=attribute, listAttrIfEmpty=True, removeNone=True)
    for object, attributes in data.items():
        for attribute in attributes:
            curve = getFCurve(object, attribute)
            if not curve:
                continue

            keyInfo = getKeyInfo(curve)
            if object not in results.keys():
                results['data'][object] = dict()

            results['data'][object][attribute] = keyInfo

    COPY_KEY_BUFFER = results

    return results


def cutKey(objects,
           attribute=None, at=None,
           time=None, t=None,
           value=None, v=None,
           *args, **kwargs):
    '''
    This function is used Cut keyframes to the keyframe buffer
    Basically it just runs copyKey(cut=True)

    Optional Parameters:
        [obj]   objects                : Object or objects to query, optionally a list of tuples of object attribute pairs
        [str]   attribute/at           : The attribute or list of attributes to keyframe, Not used if objects is a list of tuples
        [float] time/t                 : The time or time range to query, default = all keys
        [float] value/v                : The value or value range to query

    OUT:
        [list] keys copied to buffer
    '''
    attribute = parseArgs(attribute, at, None)
    time = parseArgs(time, t, None)
    value = parseArgs(value, v, None)
    return copyKey(objects, attribute=attribute, time=time, value=value, cut=True)


def pasteKey(objects,
             attribute=None, at=None,
             time=None, t=None,
             option=None, o=None,
             *args, **kwargs):
    '''
    This function is used Copy keyframes to the keyframe buffer
    If objects is a list of FCurves, only FCurves are taken into account.
    You cannot mix FCurves and object attribute pairs at this stage
    If a time range is not specified, the range is determined from the start/end of key length

    Optional Parameters:
        [obj]   objects                : Object or objects to query, optionally a list of tuples of object attribute pairs
        [str]   attribute/at           : The attribute or list of attributes to keyframe, Not used if objects is a list of tuples
        [float] time/t                 : The time or time range, default = all keys
        [str]   option/o               : Paste Option, default=insert

    OUT:
        [list] keys copied to buffer

    Paste Options:
        insert                 : Insert the keys into the curve, will not alter any existing keys on different frames
        replace                : Replaces all keys during the range of these keys or range specified
        replaceCompletely      : Removes all existing keys before pasting
        scaleInsert            : Will scale the pasted range to fit the specified range instead of cropping
        scaleReplace           : As above but will use replace mode
        scaleReplaceCompletely : As above but will use replaceCompletely mode
    '''
    def applyData(curve, keyInfo, time=None, option=None):
        times = [k['co'][0] for k in keyInfo]
        keyRange = (min(times), max(times))

        if not time:
            time = keyRange

        if option in ['replaceCompletely', 'scaleReplaceCompletely']:
            for key in curve.keyframe_points:
                curve.keyframe_points.remove(key)

        if option in ['replace', 'scaleReplace']:
            for key in curve.keyframe_points:
                if time[0] <= key.co[0] <= time[1]:
                    curve.keyframe_points.remove(key)

        for item in keyInfo:
            offset = 0
            co = item['co']
            if not (time[0] <= co[0] <= time[1]):
                continue

            if option in ['scaleInsert', 'scaleReplace', 'scaleReplaceCompletely'] and not keyRange == time:
                # Adjust time values here
                newValue = scaleInRange(co[0], keyRange, time)
                offset = co[0] - newValue

            key = curve.keyframe_points.insert(co[0]+offset, co[1])
            for attr in ['handle_left', 'handle_right']:
                value = item.get(attr) + offset
                setattr(key, attr, value)

            for attr in ['handle_left_type', 'handle_right_type', 'interpolation']:
                setattr(key, attr, item.get(attr))

    global COPY_KEY_BUFFER
    attribute = parseArgs(attribute, at, None)
    time = parseArgs(time, t, None)
    option = parseArgs(option, o, 'insert')

    if objects is None:
        objects = ls(sl=1)

    curves = []
    if isType(objects, bpy.types.FCurve):
        curves = [objects]

    elif isType(objects, [list, tuple]):
        curves = [c for c in objects if isType(c, [bpy.types.FCurve])]

    # We paste based on order, if copy=(A, B, C), and objects=(C, A, B), (C=A, A=B, B=C)
    data = parseObjectAttributes(objects, attributes=attribute, listAttrIfEmpty=True, removeNone=True)
    curveInfo = COPY_KEY_BUFFER.get('curves')
    objectInfo = COPY_KEY_BUFFER.get('data')

    # If curves are input, only deal with curves at this stage, grab data until you run out.
    if curves:
        i = 0
        if curveInfo:
            for curve, keyInfo in curveInfo.items():
                if i >= len(curves):
                    return

                applyData(curves[i], keyInfo, option=option)
                i += 1

        for object, attributes in objectInfo.items():
            for attribute, keyInfo in attributes.items():
                if i >= len(curves):
                    return

                applyData(curves[i], keyInfo, option=option)
                i += 1

        return

    objectInfoKeys = list(objectInfo.keys())
    iO = 0
    for object, attributes in data:
        if iO >= len(objectInfoKeys):
            return

        attributeData = objectInfo[objectInfoKeys[i]]
        attributeKeys = list(attributeData.keys())
        iA = 0
        for attribute in attributes:
            if iA >= len(attributeKeys):
                continue

            keyInfo = attributeData[attributeKeys[i]]
            curve = getFCurve(object, attribute, createIfNotExists=True)
            applyData(curve, keyInfo, option=option)

            iA += 1

        iO += 1

    return curves


def scaleKey(objects=None,
             attribute=None, at=None,
             time=None, t=None,
             timeScale=None, ts=None,
             valueScale=None, vs=None,
             timePivot=None, tp=None,
             valuePivot=None, vp=None,
             newStartTime=None, nst=None,
             newEndTime=None, net=None,
             newStartValue=None, nsv=None,
             newEndValue=None, nev=None):
    '''
    This function will scale keys

    Optional Parameters:
        [obj]   objects                : Object or objects to query, optionally a list of tuples of object attribute pairs
        [str]   attribute/at           : The attribute or list of attributes to keyframe, Not used if objects is a list of tuples
        [tuple] time/t                 : Time range to operate or query
        [float] timeScale/ts           : Amount to scale in time (x)
        [float] valueScale/vs          : Amount to scale in value (y)
        [float] timePivot/tp           : frame to scale from
        [float] valuePivot/vp          : value to scale from
        [float] newStartTime/nst       : Start time for absolute range
        [float] newEndTime/net         : End time for absolute range
        [float] newStartValue/nsv      : Minimum value for value scaling
        [float] newEndValue/nev        : Maximum value for value scaling
    '''
    def parsePivot(start, end, pivot, scale):
        newStart = (start-pivot) * scale
        newEnd = (end-pivot) * scale
        return (newStart, newEnd)

    def scaleIt(key, start, end, axis):
        setattr(key.co, axis, scaleInRange(keyRange, (start, end), getattr(key.co, axis)))
        setattr(key.handle_left, axis, scaleInRange(keyRange, (start, end), getattr(key.handle_left, axis)))
        setattr(key.handle_right, axis, scaleInRange(keyRange, (start, end), getattr(key.handle_right, axis)))

    attribute = parseArgs(attribute, at, None)
    time = parseArgs(time, t, None)
    timeScale = parseArgs(timeScale, ts, None)
    valueScale = parseArgs(valueScale, vs, None)
    timePivot = parseArgs(timePivot, tp, 0)
    valuePivot = parseArgs(valuePivot, vp, 0)
    newStartTime = parseArgs(newStartTime, nst, None)
    newEndTime = parseArgs(newEndTime, net, None)
    newStartValue = parseArgs(newStartValue, nsv, None)
    newEndValue = parseArgs(newEndValue, nev, None)

    if time is not None:
        time = parseDouble(time)

    curves = []
    if isType(objects, bpy.types.FCurve):
        curves = [objects]

    elif isType(objects, [list, tuple]):
        curves = [c for c in objects if isType(c, [bpy.types.FCurve])]

    if not curves:
        if attribute:
            data = parseObjectAttributes(objects, attributes=attribute, listAttrIfEmpty=True, removeNone=True)

        else:
            data = objects

        curves = getFCurves(data, createIfNotExists=False)

    if not curves:
        return

    for curve in curves:
        # Store these so we don't overwrite originals
        _nst, _net = (newStartTime, newEndTime)
        _nsv, _nev = (newStartValue, newEndValue)
        keys = list(curve.keyframe_points)
        if time:
            keys = [k for k in keys if time[0] < k['co'][0] < time[1]]

        timeValues = {}
        for key in keys:
            _co = key['co']
            timeValues[_co[0]] = _co[1]

        keyRange = (min(timeValues.keys()), max(timeValues.keys()))
        valueRange = (min(timeValues.values()), max(timeValues.values()))

        if timeScale is not None:
            _nst, _net = parsePivot(keyRange[0], keyRange[1], timePivot, timeScale)

        if valueScale is not None:
            _nsv, _nev = parsePivot(valueRange[0], valueRange[1], valuePivot, valueScale)

        # Due to this method you cannot have a specific range and a scale, this is intentional
        if _nst is not None or _net is not None:
            if _nst is None:
                _nst = keyRange[0]

            if _net is None:
                _net = keyRange[1]

        if _nsv is not None or _nev is not None:
            if _nsv is None:
                _nsv = valueRange[0]

            if _nev is None:
                _nev = valueRange[1]

        for key in keys:
            if _nst is not None:
                scaleIt(key, _nst, _net, 'x')

            if _nsv is not None:
                scaleIt(key, _nsv, _nev, 'y')

    return curves


def setKeyframe(objects=None,
                attribute=None, at=None,
                inTangentType=None, itt=None,
                outTangentType=None, ott=None,
                time=None, t=None,
                value=None, v=None):
    '''
    This function is used Set keyframe values
    If no objects are specified it will use the selection

    Optional Parameters:
        [obj]   objects                : Object or objects to keyframe, optionally a list of tuples of object attribute pairs
        [str]   attribute/at           : The attribute or list of attributes to keyframe, Not used if objects is a list of tuples
        [str]   inTangentType/itt      : Left Tangent, options are constant, linear, bezier
        [str]   outTangentType/ott     : Right Tangent, options are spline, linear, flat, stepped
        [float] time/t                 : The time to operate on, default = currentTime
        [float] value/v                : The value to set, if None will use the current value
    '''
    def getPreviousKey(curve, key):
        index = list(curve.keyframe_points).index(key)
        if index <= 0:
            return None

        return curve.keyframe_points[index-1]

    attribute = parseArgs(attribute, at, None)
    inTangentType = parseArgs(inTangentType, itt, None)
    outTangentType = parseArgs(outTangentType, ott, None)
    time = parseArgs(time, t, currentTime(q=1))
    value = parseArgs(value, v, None)
    if inTangentType and str(inTangentType).lower() not in CONSTANTS.tangentTypes.keys():
        raise RuntimeError('inTangentType not in CONSTANT, LINEAR, BEZIER, FLAT')

    if outTangentType and str(outTangentType).lower() not in CONSTANTS.tangentTypes.keys():
        raise RuntimeError('outTangentType not in CONSTANT, LINEAR, BEZIER, FLAT')

    if objects is None:
        objects = ls(sl=1)

    curves = []
    if isType(objects, bpy.types.FCurve):
        curves = [objects]

    elif isType(objects, [list, tuple]):
        curves = [c for c in objects if isType(c, [bpy.types.FCurve])]

    if not curves:
        if attribute:
            data = parseObjectAttributes(objects, attributes=attribute, listAttrIfEmpty=True, removeNone=True)

        else:
            data = objects

        curves = getFCurves(data, createIfNotExists=True)

    if not curves:
        return []

    keys = []
    for curve in curves:
        v = value
        if value is None:
            v = curve.evaluate(time)

        key = curve.keyframe_points.insert(time, v)
        keys.append(key)
        if outTangentType:
            key.interpolation = CONSTANTS.tangentTypes.get(outTangentType.lower())
            if outTangentType.lower() == 'flat':
                key.handle_right[1] = key.co[1]

        if inTangentType:
            if inTangentType.lower() == 'flat':
                key.handle_right[1] = key.co[1]
                continue

            prevKey = getPreviousKey(curve, key)
            if not prevKey:
                continue

            prevKey.interpolation = CONSTANTS.tangentTypes.get(inTangentType.lower())

    return keys


def createLocator(name=None, n=None,
                  type=None, t=None):
    '''
    This will create an empty/locator

    Optional Parameters:
        [str]   name/n                 : Name of this locator
        [str]   type/t                 : Type of this locator
    '''
    name = parseArgs(name, n, None)
    type = parseArgs(type, t, 'PLAIN_AXES')

    selection = ls(sl=1)

    bpy.ops.object.empty_add(type=type)
    locator = ls(sl=1)[0]
    if name:
        locator.name = name

    if selection:
        select(selection, replace=True)

    return locator


def duplicate(objects=None, allDecendants=None, ad=None):
    '''
    This will duplicate either the specified or selected objects

    Optional:
        [list] objects          : the objects to duplicate, default=ls(sl=1)
        [bool] allDecendants/ad : If True will duplicate all children, default=False
    '''
    allDecendants = parseArgs(allDecendants, ad, False)
    if objects is None:
        objects = ls(sl=True)

    objects = asList(objects)
    if not objects:
        return []

    selection = ls(sl=1)
    select(objects)
    bpy.ops.object.duplicate(objects)
    result = ls(sl=1)
    select(selection)
    return result


def createCamera(name=None, n=None):
    '''
    This will create a camera

    Optional Parameters:
        [str]   name/n                 : Name of this locator
    '''
    name = parseArgs(name, n, None)

    selection = ls(sl=1)

    bpy.ops.object.camera_add()
    camera = ls(sl=1)[0]
    if name:
        camera.name = name

    if selection:
        select(selection, replace=True)

    return camera


def playblast(filename=None,
              camera=None, c=None,
              startTime=None, st=None,
              endTime=None, et=None,
              format=None, fmt=None,
              framePadding=None, fp=None,
              forceOverwrite=None, fo=None,
              height=None, h=None,
              width=None, w=None,
              rawFrameNumbers=None, rfn=None,
              sound=None, s=None,
              restoreSettings=None, rs=None,
              *args, **kwargs):
    '''
    This will run an opengl render,
    If a setting is not specified it will obtain it from the active scene
    Sound is currently unsupported

    Optional Parameters:
        [str]   filename                 : Where to output the files
        [str]   camera/c                 : The camera to render
        [float] startTime/st             : Start frame
        [float] endTime/et               : EndTime
        [str]   format/fmt               : Output format (jpg, png, exr)
        [int]   framePadding/fp          : Frame Padding, 4 = image.0001.png
        [bool]  forceOverwrite/fo        : Overwrite files when rendering
        [int]   width/w                  : Width of image
        [int]   height/h                 : Height of image
        [list]  rawFrameNumbers/rfn      : A list of frames to render
    '''
    scene = bpy.context.scene
    camera = parseArgs(camera, c, scene.camera)
    startTime = parseArgs(startTime, st, playbackOptions(min=True, query=True))
    endTime = parseArgs(endTime, et, playbackOptions(max=True, query=True))
    format = parseArgs(format, fmt, scene.render.image_settings.file_format).upper()
    framePadding = parseArgs(framePadding, fp, 4)
    forceOverwrite = parseArgs(forceOverwrite, fo, scene.render.use_overwrite)
    height = parseArgs(height, h, scene.render.resolution_x)
    width = parseArgs(width, w, scene.render.resolution_y)
    rawFrameNumbers = parseArgs(rawFrameNumbers, rfn, None)
    sound = parseArgs(sound, s, None)
    restoreSettings = parseArgs(restoreSettings, rs, True)
    if format not in CONSTANTS.renderFormats:
        raise RuntimeError('format "{0}" not in types("{1}")'.format(format, '","'.join(CONSTANTS.renderFormats)))

    # Store Settings
    settings = {}
    settings['camera'] = scene.camera
    settings['startTime'] = playbackOptions(min=True, query=True)
    settings['endTime'] = playbackOptions(max=True, query=True)
    settings['format'] = scene.render.image_settings.file_format
    settings['forceOverwrite'] = scene.render.use_overwrite
    settings['width'] = scene.render.resolution_x
    settings['height'] = scene.render.resolution_y
    settings['filename'] = scene.render.filepath

    # Apply Settings
    if camera:
        scene.camera = asObject(camera)

    if startTime is not None:
        playbackOptions(min=startTime)

    if endTime is not None:
        playbackOptions(max=endTime)

    if format:
        scene.render.image_settings.file_format = format

    if forceOverwrite is not None:
        scene.render.use_overwrite = bool(forceOverwrite)

    if width is not None:
        scene.render.resolution_x = width

    if height is not None:
        scene.render.resolution_y = height

    # Playblast
    bpy.ops.render.opengl(animation=True)

    # Restore Settings
    if restoreSettings:
        scene.camera = settings['camera']
        playbackOptions(min=settings['startTime'])
        playbackOptions(max=settings['endTime'])
        scene.render.image_settings.file_format = settings['format']
        scene.render.use_overwrite = settings['forceOverwrite']
        scene.render.resolution_x = settings['width']
        scene.render.resolution_y = settings['height']
        scene.render.filepath = settings['filename']


def playbackOptions(animationStartTime=None, ast=None,
                    animationEndTime=None, aet=None,
                    minTime=None, min=None,
                    maxTime=None, max=None,
                    framesPerSecond=None, fps=None,
                    frameStep=None, by=None,
                    audioScrubbing=None, asc=None,
                    audioMuted=None, am=None,
                    avSync=None, avs=None,
                    frameDropping=None, fd=None,
                    query=None, q=None,
                    *args, **kwargs):
    '''
    Query or set options for playback such as range, framerate, audio, etc
    When query is True it will return the value instead of setting it

    Optional Parameters:
        [float] animationStartTime/ast   : Frame Range Start
        [float] animationEndTime/aet     : Frame Range End
        [float] minTime/min              : Start of sub range
        [float] maxTime/max              : End of sub range
        [float] framesPerSecond/fps      : Framerate
        [float] frameStep/by             : Frames to skip
        [bool]  audioScrubbing/asc       : Enable or disable audio during scrub
        [bool]  audioMuted/am            : Enable or disable audio
        [bool]  avSync/avs               : Enable or disable AV Syncing
        [bool]  frameDropping/fd         : If True will drop frames if it cannot play back at realtime.
        [bool]  query/q                  : If True will return values instead of setting
    '''
    animationStartTime = parseArgs(animationStartTime, ast, None)
    animationEndTime = parseArgs(animationEndTime, aet, None)
    minTime = parseArgs(minTime, min, None)
    maxTime = parseArgs(maxTime, max, None)
    framesPerSecond = parseArgs(framesPerSecond, fps, None)
    frameStep = parseArgs(frameStep, by, None)
    audioScrubbing = parseArgs(audioScrubbing, asc, None)
    audioMuted = parseArgs(audioMuted, am, None)
    avSync = parseArgs(avSync, avs, None)
    frameDropping = parseArgs(frameDropping, fd, None)
    query = parseArgs(query, q, False)
    scene = bpy.context.scene

    if query:
        if any([animationStartTime, minTime]):
            return scene.frame_start

        if any([animationEndTime, maxTime]):
            return scene.frame_end

        if framesPerSecond:
            return scene.render.fps

        if frameStep:
            return scene.frame_step

        if audioScrubbing:
            return scene.use_audio_scrub

        if audioMuted:
            return scene.use_audio

        if avSync:
            return scene.use_audio_sync

        if frameDropping:
            return scene.use_frame_drop

        raise RuntimeError('Invalid Inputs: playbackOptions')

    if animationStartTime is not None:
        scene.frame_start = float(animationStartTime)

    if animationEndTime is not None:
        scene.frame_end = float(animationStartTime)

    # TODO: Until support for min/max in blender, just act like start, end
    if minTime is not None:
        scene.frame_start = float(minTime)

    if maxTime is not None:
        scene.frame_end = float(maxTime)

    if framesPerSecond is not None:
        scene.render.fps = float(framesPerSecond)
        scene.render.fps_base = 1.0

    if frameStep is not None:
        scene.frame_step = int(frameStep)

    if audioScrubbing is not None:
        scene.use_audio_scrub = bool(audioScrubbing)

    if audioMuted is not None:
        scene.use_audio = bool(audioMuted)

    if avSync is not None:
        scene.use_audio_sync = bool(avSync)

    if frameDropping is not None:
        scene.use_frame_drop = bool(frameDropping)


def dgdirty(objects=None,
            allPlugs=None, a=None,
            *args, **kwargs):
    '''
    Forces the object data to update.
    This is particularly used when setting local space transforms

    Optional Parameters:
        [list] objects      : Objects to refresh
        [bool] allPlugs/a   : If True will refresh every object
    '''
    allPlugs = parseArgs(allPlugs, a, False)
    if not any([objects, allPlugs]):
        return

    if allPlugs and objects is None:
        objects = ls()

    else:
        objects = asObjects(objects, forceObjects=True)

    for item in objects:
        data = item.data
        if not data or not hasattr(data, 'update'):
            continue

        data.update()


def asObjects(objects, dataType=None, forceObjects=False):
    '''
    This will determine what type of node the input is and return it as a blender object
    If the input is not a string, it is returned directly.
    if dataType, it will look for the node in that particular area
    if dataType, it will look for the node in that particular area
    If forceObjects is True, it will find objects when passed in components
    returns a list

    Required Parameters:
        [list] objects

    Optional Parameters:
        [str]  dataType
        [bool] forceObjects

    OUT:
        [list] objects
    '''
    results = []
    for obj in asList(objects):
        node = asObject(obj, dataType=dataType)
        if not node:
            continue

        results.append(node)

    return results


def asObject(obj, dataType=None, forceObjects=False):
    '''
    This will determine what type of node the input is and return it as a blender object
    If the input is not a string, it is returned directly.
    if dataType, it will look for the node in that particular area
    If forceObjects is True, it will find objects when passed in components

    Required Parameters:
        [obj] obj

    Optional Parameters:
        [str]  dataType
        [bool] forceObjects

    OUT:
        obj
    '''
    typeConvert = dict(light='lamp', rig='armature')
    if dataType in typeConvert.keys():
        dataType = typeConvert.get(dataType)

    findObject = False
    if isType(obj, [list, tuple]):
        obj = fi(obj)

    if isType(obj, [dict]):
        obj = fi(obj.values())

    if not obj:
        return None

    if not issubclass(type(obj), str):
        if forceObjects:
            findObject = True
        else:
            return obj

    if dataType:
        if dataType not in CONSTANTS.dataTypes.keys():
            return None

        data = CONSTANTS.dataTypes.get(dataType)
        if findObject and obj in data.values():
            return obj

        if not findObject:
            item = data.get(obj)
            if item:
                return item

        return None

    for module in [bpy.data.objects, bpy.data.meshes, bpy.data.cameras, bpy.data.lamps,
                   bpy.data.curves, bpy.data.metaballs, bpy.data.armatures, bpy.data.lattices,
                   bpy.data.libraries, bpy.data.texts, bpy.data.speakers, bpy.data.sounds,
                   bpy.data.images]:
        item = None
        if findObject and obj in module.values():
            item = obj

        if not findObject:
            item = module.get(obj)

        if item:
            return item

    return None

def objectType(obj, isAType=None, isa=None,\
               forceObjects=None, fo=None):
    '''
    attempt to determine the type of object

    IN:
        [obj]      obj             : Object to check
        [str]      isAType/isa     : Will return a boolean if the type this string
        [str]      forceObjects/fo : If True makes sure this is an object in bpy.data

    OUT:
        [str/bool] type
    '''
    isAType = parseArgs(isAType, isa)
    forceObjects = parseArgs(forceObjects, fo, True)
    nodeType = 'unknown'
    node = asObject(obj, forceObjects=forceObjects)
    if not obj:
        raise RuntimeError('{0} does not exist'.format(obj))

    for dataType, module in CONSTANTS.dataTypes:
        if node in module.values():
            nodeType = dataType
            break

    if isAType is not None:
        return bool(nodeType == isAType)

    return nodeType


def asString(item):
    '''
    This will convert the input to string form
    tuples/dicts are assumed to be node, attribute pairs
    a list will simply be split and passed through this function recursively

    Valid Inputs:
        item=object, returns string object
        item=[object, object], returns [str object, str object]
        item=(object, attribute), returns 'object.attribute'
        item=dict(object=attribute), returns 'object.attribute'

    IN:
        [item] item

    OUT:
        variableType result
    '''
    if not item:
        return ''

    if isType(item, list):
        return [asString(i) for i in item]

    if isType(item, tuple):
        if not len(item) == 2:
            raise RuntimeError('asString tuples must be of length 2')

        object, attribute = item
        if not isType(object, str):
            object = asObject(object, forceObjects=True)
            object = object.name if object else ''

        return '{0}.{1}'.format(object, attribute)

    if isType(item, dict):
        results = []
        for key, value in item.items():
            results.append(asString((key, value)))

        return results

    object = asObject(item, forceObjects=True)
    if object:
        return object.name

    else:
        return str(object)


class BatchedThread(threading.Thread):
    '''
    A generic thread designed to be used internally with the batch function

    IN:
        [Queue.Queue] queue
        [function]    function
        [dic]         parameters, optional, default=None
    '''
    def __init__(self, queue, function, parameters=None):
        threading.Thread.__init__(self)
        self.queue = queue
        self.function = function
        self.parameters = parameters
        self.result = {}
        self.data = {}
        self.isAlive = True

    def run(self):
        while self.isAlive:
            data = self.queue.get()
            if not data:
                break

            index = data[0]
            data = asList(data[1])
            self.data[index] = data

            if self.parameters:
                self.result[index] = self.function(data, **self.parameters)

            else:
                self.result[index] = self.function(data)

            self.queue.task_done()


def batch(items, function, parameters=None, batchSize=-1, threads=-1):
    '''
    A Quick way to batch process a large number of items through a function
    The function must accept a single input followed by your optional parameters
    The first input of the function will be passed a list
    The result is in the same order as the inputs

    IN:
        [list]     items, The items to operate on
        [function] function, The function to pass the items through

    Optional:
        [dict]     parameters, optional dictionary of parameters, default=None
        [int]      batchSize,  -1 for 1 per item, otherwise they will go in this amount
        [int]      threads,    -1 for 1 per item, otherwise they will go in this amount

    OUT:
        [list] results
    '''
    items = asList(items)
    batchSize = 1 if batchSize < 1 else batchSize
    batches = [items[i:i+batchSize] for i in range(0, len(items), batchSize)]
    numThreads = max(len(batches) if threads < 1 else threads, len(batches))
    threads = []

    queue = Queue.Queue()
    for i in range(numThreads):
        t = BatchedThread(queue, function, parameters)
        t.start()
        threads.append(t)

    for index, batch in enumerate(batches):
        queue.put((index, batch))

    queue.join()

    threadData = {}
    for thread in threads:
        thread.isAlive = False
        for index in thread.data.keys():
            threadData[index] = thread.result[index]

    results = []
    for i in range(len(batches)):
        results += threadData[i]

    return results
