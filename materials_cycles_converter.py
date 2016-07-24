# gpl: author Silvio Falcinelli. Fixes by others.
# special thanks to user blenderartists.org cmomoney


import bpy
import math
from math import (log, pow, exp)

import os
from os import path, access
from .warning_messages_utils import warning_messages

from bpy.props import *

# switch for operator's function called after AutoNodeInitiate
CHECK_AUTONODE = False

# collect report for the operator
# string that has . as delimiters for splitting into new lines
COLLECT_REPORT = []


def collect_report():
    messages = ".".join(COLLECT_REPORT)
    bpy.ops.mat_converter.reports('INVOKE_DEFAULT', message=messages)
    COLLECT_REPORT = []


def AutoNodeOff(operator=None):
    mats = bpy.data.materials
    for cmat in mats:
        cmat.use_nodes = False
    bpy.context.scene.render.engine = 'BLENDER_RENDER'
    if operator:
        warning_messages(operator, 'BI_SW_NODES_OFF')


def CheckImagePath(operator=None):
    for image in bpy.data.images:
        if image:
            path = bpy.path.abspath(image.filepath)
            if os.path.exists(path):
                if (os.access(os.path.dirname(path), os.W_OK) and
                   os.access(path, os.W_OK)):
                    continue
                else:
                    warning_messages(operator, 'TEX_D_T_ERROR', image.name, "FILE")
                    return False
            else:
                warning_messages(operator, 'TEX_PATH_ERROR', image.name, "FILE")
                return False
        return False
    return True


def BakingText(tex, mode):
    print("\n________________________________________ \n"
          "INFO start bake texture " + tex.name)

    saved_img_path = None
    bpy.ops.object.mode_set(mode='OBJECT')
    sc = bpy.context.scene
    tmat = ''
    img = ''
    Robj = bpy.context.active_object
    for n in bpy.data.materials:
        if n.name == 'TMP_BAKING':
            tmat = n
    if not tmat:
        tmat = bpy.data.materials.new('TMP_BAKING')
        tmat.name = "TMP_BAKING"

    bpy.ops.mesh.primitive_plane_add()
    tm = bpy.context.active_object
    tm.name = "TMP_BAKING"
    tm.data.name = "TMP_BAKING"
    bpy.ops.object.select_pattern(extend=False, pattern="TMP_BAKING", case_sensitive=False)
    sc.objects.active = tm
    bpy.context.scene.render.engine = 'BLENDER_RENDER'
    tm.data.materials.append(tmat)
    if len(tmat.texture_slots.items()) == 0:
        tmat.texture_slots.add()
    tmat.texture_slots[0].texture_coords = 'UV'
    tmat.texture_slots[0].use_map_alpha = True
    tmat.texture_slots[0].texture = tex.texture
    tmat.texture_slots[0].use_map_alpha = True
    tmat.texture_slots[0].use_map_color_diffuse = False
    tmat.use_transparency = True
    tmat.alpha = 0
    tmat.use_nodes = False
    tmat.diffuse_color = 1, 1, 1
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.unwrap()

    for n in bpy.data.images:
        if n.name == 'TMP_BAKING':
            n.user_clear()
            bpy.data.images.remove(n)

    if mode == "ALPHA" and tex.texture.type == 'IMAGE':
        sizeX = tex.texture.image.size[0]
        sizeY = tex.texture.image.size[1]
    else:
        bake_size = (int(sc.img_bake_size) if sc.img_bake_size else 1024)
        sizeX = bake_size
        sizeY = bake_size
    bpy.ops.image.new(name="TMP_BAKING", width=sizeX, height=sizeY, color=(0.0, 0.0, 0.0, 1.0), alpha=True, float=False)
    bpy.data.screens['UV Editing'].areas[1].spaces[0].image = bpy.data.images["TMP_BAKING"]
    sc.render.engine = 'BLENDER_RENDER'
    img = bpy.data.images["TMP_BAKING"]
    img = bpy.data.images.get("TMP_BAKING")
    img.file_format = "JPEG"

    path = bpy.path.abspath(sc.conv_path)
    tex_name = getattr(getattr(tex.texture, "image", None), "name", None)
    print("tex_name is:", tex_name)
    texture_name = (tex_name if tex_name else tex.texture.name)

    if mode == "ALPHA" and tex.texture.type == 'IMAGE':
        #img.filepath_raw = tex.texture.image.filepath + "_BAKING.jpg"
        new_tex_name = texture_name + "_BAKING.jpg"
        img.filepath_raw = path + texture_name + "_BAKING.jpg"
        print("img.filepath_raw = path + tex_name + _BAKING.jpg is", path + new_tex_name)
        saved_img_path = img.filepath_raw
        print("saved_img_path is:", saved_img_path)
    else:
        #img.filepath_raw = tex.texture.name + "_PTEXT.jpg"
        new_tex_name = texture_name + "_PTEXT.jpg"
        img.filepath_raw = path + texture_name + "_PTEXT.jpg"
        saved_img_path = img.filepath_raw
        print("saved_img_path is:", saved_img_path)

    sc.render.bake_type = 'ALPHA'
    sc.render.use_bake_selected_to_active = True
    sc.render.use_bake_clear = True
    bpy.ops.object.bake_image()
    img.save()
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.delete()
    bpy.ops.object.select_pattern(extend=False, pattern=Robj.name, case_sensitive=False)
    sc.objects.active = Robj
    tex.texture.name = new_tex_name
    img.user_clear()
    bpy.data.images.remove(img)

    if tmat.users == 0:
        bpy.data.materials.remove(tmat)

    # print('INFO : end Bake ' + img.filepath_raw )
    print("________________________________________")

    if saved_img_path:
        return saved_img_path


def AutoNodeInitiate(active=False, operator=None):
    # Checks with bpy.ops.material.check_converter_path
    # if it is possible to write in the output path
    # if it passes procedes with calling AutoNode

    #if CheckImagePath(operator):
    print("AutoNodeInitiate is called")
    check_path = bpy.ops.material.check_converter_path()
    if 'FINISHED' in check_path:
        print("if FINISHED in check_path: is passed!!!")
        CHECK_AUTONODE = True
        AutoNode(active, operator)
    else:
        warning_messages(operator, 'DIR_PATH_CONVERT')


def AutoNode(active=False, operator=None):

    sc = bpy.context.scene

    if active:
        mats = bpy.context.active_object.data.materials
    else:
        mats = bpy.data.materials

    # No Materials for the chosen action abort
    if not mats:
        CHECK_AUTONODE = False
        if operator:
            if active:
                act_obj = bpy.context.active_object
                warning_messages(operator, 'CONV_NO_OBJ_MAT', act_obj.name)
            else:
                warning_messages(operator, 'CONV_NO_SC_MAT')
        return

    for cmat in mats:
        cmat.use_nodes = True
        TreeNodes = cmat.node_tree
        links = TreeNodes.links

        # Don't alter nodes of locked materials
        locked = False
        for n in TreeNodes.nodes:
            if n.type == 'ShaderNodeOutputMaterial':
                if n.label == 'Locked':
                    locked = True
                    break

        if not locked:
            # Convert this material from non-nodes to Cycles nodes

            shader = ''
            shmix = ''
            shtsl = ''
            Add_Emission = ''
            Add_Translucent = ''
            Mix_Alpha = ''
            sT = False

            for n in TreeNodes.nodes:
                TreeNodes.nodes.remove(n)

            # Starting point is diffuse BSDF and output material
            shader = TreeNodes.nodes.new('ShaderNodeBsdfDiffuse')
            shader.location = 0, 470
            shout = TreeNodes.nodes.new('ShaderNodeOutputMaterial')
            shout.location = 200, 400
            links.new(shader.outputs[0], shout.inputs[0])

            sM = True
            for tex in cmat.texture_slots:
                ma_alpha = getattr(getattr(tex, "use", None), "use_map_alpha", None)
                if ma_alpha:
                    sM = False
                    if sc.EXTRACT_ALPHA:
                        if tex.texture.type == 'IMAGE' and tex.texture.use_alpha:
                            if (not
                               os.path.exists(bpy.path.abspath(tex.texture.image.filepath + "_BAKING.jpg")) or
                               sc.EXTRACT_OW):
                                BakingText(tex, 'ALPHA')
                        else:
                            if not tex.texture.type == 'IMAGE':
                                if (not os.path.exists(bpy.path.abspath(tex.texture.name + "_PTEXT.jpg")) or
                                   sc.EXTRACT_OW):
                                    BakingText(tex, 'PTEXT')

            cmat_is_transp = cmat.use_transparency and cmat.alpha < 1

            if cmat_is_transp and cmat.raytrace_transparency.ior == 1 and not cmat.raytrace_mirror.use and sM:
                if not shader.type == 'ShaderNodeBsdfTransparent':
                    print("INFO:  Make TRANSPARENT shader node " + cmat.name)
                    #warning_messages(operator)
                    TreeNodes.nodes.remove(shader)
                    shader = TreeNodes.nodes.new('ShaderNodeBsdfTransparent')
                    shader.location = 0, 470
                    links.new(shader.outputs[0], shout.inputs[0])

            if not cmat.raytrace_mirror.use and not cmat_is_transp:
                if not shader.type == 'ShaderNodeBsdfDiffuse':
                    print("INFO:  Make DIFFUSE shader node" + cmat.name)
                    #warning_messages(operator)
                    TreeNodes.nodes.remove(shader)
                    shader = TreeNodes.nodes.new('ShaderNodeBsdfDiffuse')
                    shader.location = 0, 470
                    links.new(shader.outputs[0], shout.inputs[0])

            if cmat.raytrace_mirror.use and cmat.raytrace_mirror.reflect_factor > 0.001 and cmat_is_transp:
                if not shader.type == 'ShaderNodeBsdfGlass':
                    print("INFO:  Make GLASS shader node" + cmat.name)
                    #warning_messages(operator)
                    TreeNodes.nodes.remove(shader)
                    shader = TreeNodes.nodes.new('ShaderNodeBsdfGlass')
                    #warning_messages(operator)
                    shader.location = 0, 470
                    links.new(shader.outputs[0], shout.inputs[0])

            if cmat.raytrace_mirror.use and not cmat_is_transp and cmat.raytrace_mirror.reflect_factor > 0.001:
                if not shader.type == 'ShaderNodeBsdfGlossy':
                    print("INFO:  Make MIRROR shader node" + cmat.name)
                    #warning_messages(operator)
                    TreeNodes.nodes.remove(shader)
                    shader = TreeNodes.nodes.new('ShaderNodeBsdfGlossy')
                    shader.location = 0, 520
                    links.new(shader.outputs[0], shout.inputs[0])

            if cmat.emit > 0.001:
                if (not shader.type == 'ShaderNodeEmission' and not
                   cmat.raytrace_mirror.reflect_factor > 0.001 and not cmat_is_transp):
                    print("INFO:  Mix EMISSION shader node" + cmat.name)
                    #warning_messages(operator)
                    TreeNodes.nodes.remove(shader)
                    shader = TreeNodes.nodes.new('ShaderNodeEmission')
                    shader.location = 0, 450
                    links.new(shader.outputs[0], shout.inputs[0])
                else:
                    if not Add_Emission:
                        print("INFO:  Add EMISSION shader node" + cmat.name)
                        #warning_messages(operator)
                        shout.location = 550, 330
                        Add_Emission = TreeNodes.nodes.new('ShaderNodeAddShader')
                        Add_Emission.location = 370, 490

                        shem = TreeNodes.nodes.new('ShaderNodeEmission')
                        shem.location = 180, 380

                        links.new(Add_Emission.outputs[0], shout.inputs[0])
                        links.new(shem.outputs[0], Add_Emission.inputs[1])
                        links.new(shader.outputs[0], Add_Emission.inputs[0])

                        shem.inputs['Color'].default_value = (cmat.diffuse_color.r,
                                                              cmat.diffuse_color.g,
                                                              cmat.diffuse_color.b, 1)
                        shem.inputs['Strength'].default_value = cmat.emit

            if cmat.translucency > 0.001:
                print("INFO:  Add BSDF_TRANSLUCENT shader node" + cmat.name)
                #warning_messages(operator)
                shout.location = 770, 330
                Add_Translucent = TreeNodes.nodes.new('ShaderNodeAddShader')
                Add_Translucent.location = 580, 490

                shtsl = TreeNodes.nodes.new('ShaderNodeBsdfTranslucent')
                shtsl.location = 400, 350

                links.new(Add_Translucent.outputs[0], shout.inputs[0])
                links.new(shtsl.outputs[0], Add_Translucent.inputs[1])

                if Add_Emission:
                    links.new(Add_Emission.outputs[0], Add_Translucent.inputs[0])
                    pass
                else:
                    links.new(shader.outputs[0], Add_Translucent.inputs[0])
                    pass
                shtsl.inputs['Color'].default_value = cmat.translucency, cmat.translucency, cmat.translucency, 1

            shader.inputs['Color'].default_value = cmat.diffuse_color.r, cmat.diffuse_color.g, cmat.diffuse_color.b, 1

            if shader.type == 'ShaderNodeBsdfDiffuse':
                shader.inputs['Roughness'].default_value = cmat.specular_intensity

            if shader.type == 'ShaderNodeBsdfGlossy':
                shader.inputs['Roughness'].default_value = 1 - cmat.raytrace_mirror.gloss_factor

            if shader.type == 'ShaderNodeBsdfGlass':
                shader.inputs['Roughness'].default_value = 1 - cmat.raytrace_mirror.gloss_factor
                shader.inputs['IOR'].default_value = cmat.raytrace_transparency.ior

            if shader.type == 'ShaderNodeEmission':
                shader.inputs['Strength'].default_value = cmat.emit

            for tex in cmat.texture_slots:
                sT = False
                pText = ''
                if tex:
                    if tex.use:
                        if tex.texture.type == 'IMAGE':
                            img = tex.texture.image
                            shtext = TreeNodes.nodes.new('ShaderNodeTexImage')
                            shtext.location = -200, 400
                            shtext.image = img
                            sT = True

                        if not tex.texture.type == 'IMAGE':
                            if sc.EXTRACT_PTEX:
                                print('INFO : Extract Procedural Texture  ')
                                if (not os.path.exists(bpy.path.abspath(tex.texture.name + "_PTEXT.jpg")) or
                                   sc.EXTRACT_OW):
                                    baked_name = BakingText(tex, 'PTEX')
                                    print("tex.texture.name:", tex.texture.name)
                                    print("baked_name is:", baked_name)
                                try:
                                    for image in bpy.data.images:
                                        print("image.name", image.name)

                                    #if baked_name in image.name:
                                    print("image name is :", image.name)
                                    img = bpy.data.images.load(baked_name)
                                    #if os.path.exists(bpy.path.abspath(tex.texture.name + "_PTEXT.jpg")):
                                    #img = bpy.data.images.load(bpy.path.abspath(tex.texture.name + "_PTEXT.jpg"))
                                    shtext = TreeNodes.nodes.new('ShaderNodeTexImage')
                                    shtext.location = -200, 400
                                    shtext.image = img
                                    sT = True
                                except (ValueError, KeyError, IndexError):
                                    print("Failure to load baked image")

                if sT:
                    if tex.use_map_color_diffuse:
                        links.new(shtext.outputs[0], shader.inputs[0])

                    if tex.use_map_emit:
                        if not Add_Emission:
                            print("INFO:  Mix EMISSION + Texture shader node " + cmat.name)
                            #warning_messages(operator)

                            intensity = 0.5 + (tex.emit_factor / 2)

                            shout.location = 550, 330
                            Add_Emission = TreeNodes.nodes.new('ShaderNodeAddShader')
                            Add_Emission.name = "Add_Emission"
                            Add_Emission.location = 370, 490

                            shem = TreeNodes.nodes.new('ShaderNodeEmission')
                            shem.location = 180, 380

                            links.new(Add_Emission.outputs[0], shout.inputs[0])
                            links.new(shem.outputs[0], Add_Emission.inputs[1])
                            links.new(shader.outputs[0], Add_Emission.inputs[0])

                            shem.inputs['Color'].default_value = (cmat.diffuse_color.r,
                                                                  cmat.diffuse_color.g,
                                                                  cmat.diffuse_color.b, 1)
                            shem.inputs['Strength'].default_value = intensity * 2

                        links.new(shtext.outputs[0], shem.inputs[0])

                    if tex.use_map_mirror:
                        links.new(shader.inputs[0], shtext.outputs[0])

                    if tex.use_map_translucency:
                        if not Add_Translucent:
                            print("INFO:  Add Translucency + Texture shader node " + cmat.name)
                            #warning_messages(operator)

                            intensity = 0.5 + (tex.emit_factor / 2)

                            shout.location = 550, 330
                            Add_Translucent = TreeNodes.nodes.new('ShaderNodeAddShader')
                            Add_Translucent.name = "Add_Translucent"
                            Add_Translucent.location = 370, 290

                            shtsl = TreeNodes.nodes.new('ShaderNodeBsdfTranslucent')
                            shtsl.location = 180, 240

                            links.new(shtsl.outputs[0], Add_Translucent.inputs[1])

                            if Add_Emission:
                                links.new(Add_Translucent.outputs[0], shout.inputs[0])
                                links.new(Add_Emission.outputs[0], Add_Translucent.inputs[0])
                                pass
                            else:
                                links.new(Add_Translucent.outputs[0], shout.inputs[0])
                                links.new(shader.outputs[0], Add_Translucent.inputs[0])

                        links.new(shtext.outputs[0], shtsl.inputs[0])

                    if tex.use_map_alpha:
                        if not Mix_Alpha:
                            print("INFO:  Mix Alpha + Texture shader node " + cmat.name)
                            #warning_messages(operator)

                            shout.location = 750, 330
                            Mix_Alpha = TreeNodes.nodes.new('ShaderNodeMixShader')
                            Mix_Alpha.name = "Add_Alpha"
                            Mix_Alpha.location = 570, 290
                            sMask = TreeNodes.nodes.new('ShaderNodeBsdfTransparent')
                            sMask.location = 250, 180
                            tMask = TreeNodes.nodes.new('ShaderNodeTexImage')
                            tMask.location = -200, 250

                            if tex.texture.type == 'IMAGE':
                                imask = bpy.data.images.load(img.filepath)
                            else:
                                imask = bpy.data.images.load(img.name)

                            tMask.image = imask
                            links.new(Mix_Alpha.inputs[0], tMask.outputs[1])
                            links.new(shout.inputs[0], Mix_Alpha.outputs[0])
                            links.new(sMask.outputs[0], Mix_Alpha.inputs[1])

                            if not Add_Emission and not Add_Translucent:
                                links.new(Mix_Alpha.inputs[2], shader.outputs[0])

                            if Add_Emission and not Add_Translucent:
                                links.new(Mix_Alpha.inputs[2], Add_Emission.outputs[0])

                            if Add_Translucent:
                                links.new(Mix_Alpha.inputs[2], Add_Translucent.outputs[0])

                    if tex.use_map_normal:
                        t = TreeNodes.nodes.new('ShaderNodeRGBToBW')
                        t.location = -0, 300
                        links.new(t.outputs[0], shout.inputs[2])
                        links.new(shtext.outputs[0], t.inputs[0])
    bpy.context.scene.render.engine = 'CYCLES'


class mllock(bpy.types.Operator):
    bl_idname = "ml.lock"
    bl_label = "Lock"
    bl_description = "Lock/unlock this material against modification by conversions"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        cmat = bpy.context.selected_objects[0].active_material
        TreeNodes = cmat.node_tree
        for n in TreeNodes.nodes:
            if n.type == 'ShaderNodeOutputMaterial':
                if n.label == 'Locked':
                    n.label = ''
                else:
                    n.label = 'Locked'
        return {'FINISHED'}


class mlrefresh(bpy.types.Operator):
    bl_idname = "ml.refresh"
    bl_label = "Convert All Materials"
    bl_description = "Convert All Materials in the scene from non-nodes to Cycles"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        AutoNodeInitiate(False, self)

        if CHECK_AUTONODE is True:
            bpy.ops.object.editmode_toggle()
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
            bpy.ops.object.editmode_toggle()

        return {'FINISHED'}


class mlrefresh_active(bpy.types.Operator):
    bl_idname = "ml.refresh_active"
    bl_label = "Convert All Materials From Active Object"
    bl_description = "Convert all Active Object's Materials from non-nodes to Cycles"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        AutoNodeInitiate(True, self)

        if CHECK_AUTONODE is True:
            bpy.ops.object.editmode_toggle()
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
            bpy.ops.object.editmode_toggle()
        return {'FINISHED'}


class mlrestore(bpy.types.Operator):
    bl_idname = "ml.restore"
    bl_label = "Restore"
    bl_description = ("Switch Back to Blender Internal \n"
                      "Use Nodes Off")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        AutoNodeOff(self)
        return {'FINISHED'}


def register():
    bpy.utils.register_module(__name__)
    pass


def unregister():
    bpy.utils.unregister_module(__name__)
    pass

if __name__ == "__main__":
    register()
