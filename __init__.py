# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
#  (c) 2015 meta-androcto, parts based on work by Saidenka, Materials Utils by MichaleW,
#           lijenstina, codemanx, Materials Conversion: Silvio Falcinelli, johnzero7#,
#           link to base names: Sybren, texture renamer: Yadoob

bl_info = {
    "name": "Materials Specials",
    "author": "Community",
    "version": (0, 2, 1),
    "blender": (2, 75, 0),
    "location": "Materials Specials Menu/Shift Q",
    "description": "Extended Specials: Materials Properties",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6"
    "/Py/Scripts",
    "tracker_url": "",
    "category": "Materials"}

if "bpy" in locals():
    import importlib
    importlib.reload(material_converter)
    importlib.reload(materials_cycles_converter)
    importlib.reload(texture_rename)
    importlib.reload(warning_messages_utils)
else:
    from . import material_converter
    from . import materials_cycles_converter
    from . import texture_rename
    from . import warning_messages_utils

import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from .warning_messages_utils import warning_messages


def fake_user_set(fake_user='ON', materials='UNUSED', operator=None):
    warn_mesg, w_mesg = '', ""
    if materials == 'ALL':
        mats = (mat for mat in bpy.data.materials if mat.library is None)
        w_mesg = "(All Materials in this .blend file)"
    elif materials == 'UNUSED':
        mats = (mat for mat in bpy.data.materials if mat.library is None and mat.users == 0)
        w_mesg = "(Unused Materials - Active/Selected Objects)"
    else:
        mats = []
        if materials == 'ACTIVE':
            objs = [bpy.context.active_object]
            w_mesg = "(All Materials on Active Object)"
        elif materials == 'SELECTED':
            objs = bpy.context.selected_objects
            w_mesg = "(All Materials on Selected Objects)"
        elif materials == 'SCENE':
            objs = bpy.context.scene.objects
            w_mesg = "(All Scene Objects)"
        else:
            # used materials
            objs = bpy.data.objects
            w_mesg = "(All Used Materials)"

        mats = (mat for ob in objs if hasattr(ob.data, "materials") for mat in ob.data.materials if mat.library is None)

    # collect mat names for warning_messages
    matnames = []

    if fake_user == 'ON':
        warn_mesg = 'FAKE_SET_ON'
    elif fake_user == 'OFF':
        warn_mesg = 'FAKE_SET_OFF'

    for mat in mats:
        mat.use_fake_user = (fake_user == 'ON')
        matnames.append(mat.name)

    if operator:
        if matnames:
            warning_messages(operator, warn_mesg, matnames, 'MAT', w_mesg)
        else:
            warning_messages(operator, 'FAKE_NO_MAT')

    for area in bpy.context.screen.areas:
        if area.type in ('PROPERTIES', 'NODE_EDITOR', 'OUTLINER'):
            area.tag_redraw()


def replace_material(m1, m2, all_objects=False, update_selection=False, operator=None):
    # replace material named m1 with material named m2
    # m1 is the name of original material
    # m2 is the name of the material to replace it with
    # 'all' will replace throughout the blend file

    matorg = bpy.data.materials.get(m1)
    matrep = bpy.data.materials.get(m2)

    if matorg != matrep and None not in (matorg, matrep):
        # store active object

        if all_objects:
            objs = bpy.data.objects
        else:
            objs = bpy.context.selected_editable_objects

        for ob in objs:
            if ob.type == 'MESH':

                match = False

                for m in ob.material_slots:
                    if m.material == matorg:
                        m.material = matrep
                        # don't break the loop as the material can be
                        # ref'd more than once

                        # Indicate which objects were affected
                        if update_selection:
                            ob.select = True
                            match = True

                if update_selection and not match:
                    ob.select = False
    else:
        if operator:
            warning_messages(operator, "REP_MAT_NONE")


def select_material_by_name(find_mat_name):
    # in object mode selects all objects with material find_mat_name
    # in edit mode selects all polygons with material find_mat_name

    find_mat = bpy.data.materials.get(find_mat_name)

    if find_mat is None:
        return

    # check for editmode
    editmode = False

    scn = bpy.context.scene

    # set selection mode to polygons
    scn.tool_settings.mesh_select_mode = False, False, True

    actob = bpy.context.active_object
    if actob.mode == 'EDIT':
        editmode = True
        bpy.ops.object.mode_set()

    if not editmode:
        objs = bpy.data.objects
        for ob in objs:
            if included_object_types(ob):
                ms = ob.material_slots
                for m in ms:
                    if m.material == find_mat:
                        ob.select = True
                        # the active object may not have the mat!
                        # set it to one that does!
                        scn.objects.active = ob
                        break
                    else:
                        ob.select = False

            # deselect non-meshes
            else:
                ob.select = False

    else:
        # it's editmode, so select the polygons
        ob = actob
        ms = ob.material_slots

        # same material can be on multiple slots
        slot_indeces = []
        i = 0
        # found = False  # UNUSED
        for m in ms:
            if m.material == find_mat:
                slot_indeces.append(i)
                # found = True  # UNUSED
            i += 1
        me = ob.data
        for f in me.polygons:
            if f.material_index in slot_indeces:
                f.select = True
            else:
                f.select = False
        me.update()

    if editmode:
        bpy.ops.object.mode_set(mode='EDIT')


def mat_to_texface(operator=None):
    # assigns the first image in each material to the polygons in the active
    # uvlayer for all selected objects

    # check for editmode
    editmode = False

    actob = bpy.context.active_object
    if actob.mode == 'EDIT':
        editmode = True
        bpy.ops.object.mode_set()

    # collect object names for warning messages
    message_a = []
    # Flag if there are non MESH objects selected
    mixed_obj = 0

    for ob in bpy.context.selected_editable_objects:
        if ob.type == 'MESH':
            # get the materials from slots
            ms = ob.material_slots

            # build a list of images, one per material
            images = []
            # get the textures from the mats
            for m in ms:
                if m.material is None:
                    continue
                gotimage = False
                textures = zip(m.material.texture_slots, m.material.use_textures)
                for t, enabled in textures:
                    if enabled and t is not None:
                        tex = t.texture
                        if tex.type == 'IMAGE':
                            img = tex.image
                            images.append(img)
                            gotimage = True
                            break

                if not gotimage:
                    images.append(None)

            # check materials for warning messages
            mats = ob.material_slots.keys()
            if operator and not mats and mixed_obj == 0:
                message_a.append(ob.name)

            # now we have the images
            # apply them to the uvlayer
            me = ob.data

            # got uvs?
            if not me.uv_textures:
                scn = bpy.context.scene
                scn.objects.active = ob
                bpy.ops.mesh.uv_texture_add()
                scn.objects.active = actob

            # get active uvlayer
            for t in me.uv_textures:
                if t.active:
                    uvtex = t.data
                    for f in me.polygons:
                        # check that material had an image!
                        if images and images[f.material_index] is not None:
                            uvtex[f.index].image = images[f.material_index]
                        else:
                            uvtex[f.index].image = None
            me.update()
        else:
            message_a.append(ob.name)
            mixed_obj = 1

    if editmode:
        bpy.ops.object.mode_set(mode='EDIT')

    if operator:
        if message_a:
            if mixed_obj == 1:
                warning_messages(operator, 'MAT_TEX_NO_MESH', message_a)
            else:
                warning_messages(operator, 'MAT_TEX_NO_MAT', message_a)


def assignmatslots(ob, matlist):
    # given an object and a list of material names
    # removes all material slots from the object
    # adds new ones for each material in matlist
    # adds the materials to the slots as well.

    scn = bpy.context.scene
    ob_active = bpy.context.active_object
    scn.objects.active = ob

    for s in ob.material_slots:
        bpy.ops.object.material_slot_remove()

    # re-add them and assign material
    i = 0
    if matlist:
        for m in matlist:
            mat = bpy.data.materials[m]
            ob.data.materials.append(mat)
            i += 1

    # restore active object:
    scn.objects.active = ob_active


def cleanmatslots(operator=None):
    # check for edit mode
    editmode = False
    actob = bpy.context.active_object

    if actob.mode == 'EDIT':
        editmode = True
        bpy.ops.object.mode_set()

    # is active object selected ?
    selected = (True if actob.select is True else False)

    if selected is False:
        actob.select = True

    objs = bpy.context.selected_editable_objects
    # collect all object names for warning_messages
    message_a = []
    # Flag if there are non MESH objects selected
    mixed_obj = 0

    for ob in objs:
        if ob.type == 'MESH':
            mats = ob.material_slots.keys()

            # if mats is empty then then mats[faceindex] will be out of range
            if mats:
                # check the polygons on the mesh to build a list of used materials
                usedMatIndex = []  # we'll store used materials indices here
                faceMats = []
                me = ob.data
                for f in me.polygons:
                    # get the material index for this face...
                    faceindex = f.material_index

                    # indices will be lost: Store face mat use by name
                    currentfacemat = mats[faceindex]
                    faceMats.append(currentfacemat)

                    # check if index is already listed as used or not
                    found = False
                    for m in usedMatIndex:
                        if m == faceindex:
                            found = True
                            # break

                    if found is False:
                        # add this index to the list
                        usedMatIndex.append(faceindex)

                # re-assign the used mats to the mesh and leave out the unused
                ml = []
                mnames = []
                for u in usedMatIndex:
                    ml.append(mats[u])
                    # we'll need a list of names to get the face indices...
                    mnames.append(mats[u])

                assignmatslots(ob, ml)

                # restore face indices:
                i = 0
                for f in me.polygons:
                    matindex = mnames.index(faceMats[i])
                    f.material_index = matindex
                    i += 1
            else:
                message_a.append(ob.name)
                continue
        else:
            message_a.append(ob.name)
            if mixed_obj < 1:
                mixed_obj += 1
            continue

    if message_a and operator:
        mess = 'C_OB_NO_MAT'
        if mixed_obj == 1:
            mess = 'C_OB_MIX_NO_MAT'
        warning_messages(operator, mess, message_a)

    # restore selection state
    if selected is False:
        actob.select = False

    if editmode:
        bpy.ops.object.mode_set(mode='EDIT')


# separate edit mode mesh function
# (faster than iterating through all faces)
def assign_mat_mesh_edit(matname="Default", operator=None):
    actob = bpy.context.active_object

    found = False
    for m in bpy.data.materials:
        if m.name == matname:
            target = m
            found = True
            break
    if not found:
        target = bpy.data.materials.new(matname)

    if (actob.type in {'MESH'} and actob.mode in {'EDIT'}):
        # check material slots for matname material
        found = False
        i = 0
        mats = actob.material_slots
        for m in mats:
            if m.name == matname:
                found = True
                # make slot active
                actob.active_material_index = i
                break
            i += 1

        if not found:
            # the material is not attached to the object
            actob.data.materials.append(target)

        # is selected ?
        selected = (True if actob.select is True else False)

        if selected is False:
            actob.select = True

        # activate the chosen material
        actob.active_material_index = i

        # assign the material to the object
        bpy.ops.object.material_slot_assign()

        actob.data.update()

        # restore selection state
        if selected is False:
            actob.select = False

        if operator:
            warning_messages(operator, 'A_MAT_NAME_EDIT', matname, 'MAT')


def assign_mat(matname="Default", operator=None):
    # get active object so we can restore it later
    actob = bpy.context.active_object

    # is active object selected ?
    selected = (True if actob.select is True else False)

    if selected is False:
        actob.select = True

    # check if material exists, if it doesn't then create it
    found = False
    for m in bpy.data.materials:
        if m.name == matname:
            target = m
            found = True
            break
    if not found:
        target = bpy.data.materials.new(matname)

    # if objectmode then set all polygons
    editmode = False
    allpolygons = True
    if actob.mode == 'EDIT':
        editmode = True
        allpolygons = False
        bpy.ops.object.mode_set()

    objs = bpy.context.selected_editable_objects

    # collect non mesh object names
    message_a = []

    for ob in objs:
        # skip the objects that can't have mats
        if not included_object_types(ob.type):
            message_a.append(ob.name)
            continue
        else:
            # set the active object to our object
            scn = bpy.context.scene
            scn.objects.active = ob

            if ob.type in {'CURVE', 'SURFACE', 'FONT', 'META'}:
                found = False
                i = 0
                for m in bpy.data.materials:
                    if m.name == matname:
                        found = True
                        index = i
                        break
                    i += 1
                    if not found:
                        index = i - 1
                targetlist = [index]
                assignmatslots(ob, targetlist)

            elif ob.type == 'MESH':
                # check material slots for matname material
                found = False
                i = 0
                mats = ob.material_slots
                for m in mats:
                    if m.name == matname:
                        found = True
                        index = i
                        # make slot active
                        ob.active_material_index = i
                        break
                    i += 1

                if not found:
                    index = i
                    # the material is not attached to the object
                    ob.data.materials.append(target)

                # now assign the material:
                me = ob.data
                if allpolygons:
                    for f in me.polygons:
                        f.material_index = index
                elif allpolygons is False:
                    for f in me.polygons:
                        if f.select:
                            f.material_index = index
                me.update()

    # restore the active object
    bpy.context.scene.objects.active = actob

    # restore selection state
    if selected is False:
        actob.select = False

    if editmode:
        bpy.ops.object.mode_set(mode='EDIT')

    if message_a and operator:
        warning_messages(operator, 'A_OB_MIX_NO_MAT', message_a)


def check_texture(img, mat):
    # finds a texture from an image
    # makes a texture if needed
    # adds it to the material if it isn't there already

    tex = bpy.data.textures.get(img.name)

    if tex is None:
        tex = bpy.data.textures.new(name=img.name, type='IMAGE')

    tex.image = img

    # see if the material already uses this tex
    # add it if needed
    found = False
    for m in mat.texture_slots:
        if m and m.texture == tex:
            found = True
            break
    if not found and mat:
        mtex = mat.texture_slots.add()
        mtex.texture = tex
        mtex.texture_coords = 'UV'
        mtex.use_map_color_diffuse = True


def texface_to_mat(operator=None):
    # editmode check here!
    editmode = False
    ob = bpy.context.object
    if ob.mode == 'EDIT':
        editmode = True
        bpy.ops.object.mode_set()

    for ob in bpy.context.selected_editable_objects:

        faceindex = []
        unique_images = []
        # collect object names for warning messages
        message_a = []

        # check if object has UV and texture data and active image in Editor
        if check_texface_to_mat(ob):
            # get the texface images and store indices
            for f in ob.data.uv_textures.active.data:
                if f.image:
                    img = f.image
                    # build list of unique images
                    if img not in unique_images:
                        unique_images.append(img)
                    faceindex.append(unique_images.index(img))
                else:
                    img = None
                    faceindex.append(None)
        else:
            message_a.append(ob.name)
            continue

        # check materials for images exist; create if needed
        matlist = []

        for i in unique_images:
            if i:
                try:
                    m = bpy.data.materials[i.name]
                except:
                    m = bpy.data.materials.new(name=i.name)
                    continue

                finally:
                    matlist.append(m.name)
                    # add textures if needed
                    check_texture(i, m)

        # set up the object material slots
        assignmatslots(ob, matlist)

        # set texface indices to material slot indices..
        me = ob.data

        i = 0
        for f in faceindex:
            if f is not None:
                me.polygons[i].material_index = f
            i += 1
    if editmode:
        bpy.ops.object.mode_set(mode='EDIT')

    if operator and message_a:
        warning_messages(operator, "TEX_MAT_NO_CRT", message_a)


def remove_materials(operator=None, setting="SLOT"):
    # Remove material slots from active object
    # SLOT - removes the object's active material
    # ALL - removes the all the object's materials
    actob = bpy.context.active_object

    if actob:
        if not included_object_types(actob.type):
            if operator:
                warning_messages(operator, 'OB_CANT_MAT', actob.name)
        else:
            if (hasattr(actob.data, "materials") and
               len(actob.data.materials) > 0):
                if setting == "SLOT":
                    bpy.ops.object.material_slot_remove()
                elif setting == "ALL":
                    for mat in actob.data.materials:
                        try:
                            bpy.ops.object.material_slot_remove()
                        except:
                            pass
                if operator:
                    warn_mess = 'R_ACT_MAT'
                    if setting == "ALL":
                        warn_mess = 'R_ACT_MAT_ALL'
                    warning_messages(operator, warn_mess, actob.name)
            elif operator:
                warning_messages(operator, 'R_OB_NO_MAT', actob.name)


def remove_materials_all(operator=None):
    # Remove material slots from all selected objects
    warn_msg = 'R_ALL_SL_MAT'
    # counter for material slots warning messages
    mat_count = 0

    for ob in bpy.context.selected_editable_objects:
        if not included_object_types(ob.type):
            continue
        else:
            # code from blender stackexchange (by CoDEmanX)
            ob.active_material_index = 0

            if (hasattr(ob.data, "materials") and
               len(ob.material_slots) >= 1):
                mat_count += 1

            for i in range(len(ob.material_slots)):
                bpy.ops.object.material_slot_remove({'object': ob})

    if operator:
        if mat_count == 0:
            warn_msg = 'R_ALL_NO_MAT'
        warning_messages(operator, warn_msg)


def CyclesNodeOn(operator=None):
    mats = bpy.data.materials
    for cmat in mats:
        cmat.use_nodes = True
    bpy.context.scene.render.engine = 'CYCLES'
    if operator:
        warning_messages(operator, 'CYC_SW_NODES_ON')


# -----------------------------------------------------------------------------
# Operator Classes #

class VIEW3D_OT_show_mat_preview(bpy.types.Operator):
    bl_label = "Preview Active Material"
    bl_idname = "view3d.show_mat_preview"
    bl_description = ("Show the preview of Active Material \n"
                      "and context related settings")
    bl_options = {'REGISTER', 'UNDO'}

    is_not_undo = False     # prevent drawing props on undo

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and
                context.object.active_material is not None and
                included_object_types(context.object.type))

    def invoke(self, context, event):
        self.is_not_undo = True
        return context.window_manager.invoke_props_dialog(self, width=200)

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        prw_size = size_preview()

        if self.is_not_undo is True:
            if ob and hasattr(ob, "active_material"):

                mat = ob.active_material
                is_opaque = (True if (ob and hasattr(ob, "show_transparent") and
                             ob.show_transparent is True)
                             else False)
                is_opaque_bi = (True if (mat and hasattr(mat, "use_transparency") and
                                mat.use_transparency is True)
                                else False)
                is_mesh = (True if ob.type == 'MESH' else False)

                if size_type_is_preview():
                    layout.template_ID_preview(ob, "active_material", new="material.new",
                                               rows=prw_size['Width'], cols=prw_size['Height'])
                else:
                    layout.template_ID(ob, "active_material", new="material.new")
                layout.separator()

                if not c_render_engine("Other"):
                    layout.prop(mat, "use_nodes", icon='NODETREE')

                if c_need_of_viewport_colors():
                    color_txt = ("Viewport Color:" if c_render_engine("Cycles") else "Diffuse")
                    spec_txt = ("Viewport Specular:" if c_render_engine("Cycles") else "Specular")
                    col = layout.column(align=True)
                    col.label(color_txt)
                    col.prop(mat, "diffuse_color", text="")
                    if c_render_engine("BI"):
                        # Blender Render
                        col.prop(mat, "diffuse_intensity", text="Intensity")
                    col.separator()

                    col.label(spec_txt)
                    col.prop(mat, "specular_color", text="")
                    col.prop(mat, "specular_hardness")

                    if (c_render_engine("BI") and not c_context_use_nodes()):
                        # Blender Render
                        col.separator()
                        col.prop(mat, "use_transparency")
                        col.separator()
                        if is_opaque_bi:
                            col.prop(mat, "transparency_method", text="")
                            col.separator()
                            col.prop(mat, "alpha")
                    elif (c_render_engine("Cycles") and is_mesh):
                        # Cycles
                        col.separator()
                        col.prop(ob, "show_transparent", text="Transparency")
                        if is_opaque:
                            col.separator()
                            col.prop(mat, "alpha")
                            col.separator()
                            col.label("Viewport Alpha:")
                            col.prop(mat.game_settings, "alpha_blend", text="")
                    layout.separator()
                else:
                    other_render = ("*Unavailable with this Renderer*" if c_render_engine("Other")
                                    else "*Unavailable in this Context*")
                    no_col_label = ("*Only available in Solid Shading*" if c_render_engine("Cycles")
                                    else other_render)
                    layout.label(no_col_label, icon="INFO")
        else:
            layout.label(text="**Only Undo is available**", icon="INFO")

    def check(self, context):
        if self.is_not_undo is True:
            return True

    def execute(self, context):
        self.is_not_undo = False
        return {'FINISHED'}


class VIEW3D_OT_copy_material_to_selected(bpy.types.Operator):
    bl_idname = "view3d.copy_material_to_selected"
    bl_label = "Copy Materials to others"
    bl_description = ("Copy Material From Active to Selected objects \n"
                      "Works on Object's Data linked Materials")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None and
                included_object_types(context.active_object.type) and
                context.object.active_material is not None and
                context.selected_editable_objects)

    def execute(self, context):
        if check_is_excluded_obj_types(context):
            warning_messages(self, 'CPY_MAT_MIX_OB')
        bpy.ops.object.material_slot_copy()
        return {'FINISHED'}


class VIEW3D_OT_texface_to_material(bpy.types.Operator):
    bl_idname = "view3d.texface_to_material"
    bl_label = "Texface Images to Material/Texture"
    bl_description = ("Create texture materials for images assigned in UV editor \n"
                      "Needs an UV Unwrapped Mesh and an image active in the  \n"
                      "UV/Image Editor for each Selected Object")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if context.selected_editable_objects:
            texface_to_mat(self)
            return {'FINISHED'}
        else:
            warning_messages(self, 'TEX_MAT_NO_SL')
            return {'CANCELLED'}


class VIEW3D_OT_assign_material(bpy.types.Operator):
    bl_idname = "view3d.assign_material"
    bl_label = "Assign Material"
    bl_description = "Assign a material to the selection"
    bl_options = {'REGISTER', 'UNDO'}

    is_edit = False

    matname = StringProperty(
            name='Material Name',
            description='Name of Material to Assign',
            default="",
            maxlen=63,
            )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        actob = context.active_object
        mn = self.matname

        if (actob.type in {'MESH'} and actob.mode in {'EDIT'}):
            assign_mat_mesh_edit(mn, self)
        else:
            assign_mat(mn, self)

        if use_cleanmat_slots():
            cleanmatslots()

        mat_to_texface()
        return {'FINISHED'}


class VIEW3D_OT_clean_material_slots(bpy.types.Operator):
    bl_idname = "view3d.clean_material_slots"
    bl_label = "Clean Material Slots"
    bl_description = ("Removes any unused material slots \n"
                      "from selected objects in Object mode")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    # materials can't be removed in Edit mode
    def poll(cls, context):
        return (context.active_object is not None and
                not context.object.mode == 'EDIT')

    def execute(self, context):
        cleanmatslots(self)
        return {'FINISHED'}


class VIEW3D_OT_material_to_texface(bpy.types.Operator):
    bl_idname = "view3d.material_to_texface"
    bl_label = "Material Images to Texface"
    bl_description = ("Transfer material assignments to UV editor \n"
                      "Works on a Mesh Object with a Material and Texture\n"
                      "assigned. Used primarily with MultiTexture Shading")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        if context.selected_editable_objects:
            mat_to_texface(self)
            return {'FINISHED'}
        else:
            warning_messages(self, "MAT_TEX_NO_SL")
            return {'CANCELLED'}


class VIEW3D_OT_material_remove_slot(bpy.types.Operator):
    bl_idname = "view3d.material_remove_slot"
    bl_label = "Remove Active Slot (Active Object)"
    bl_description = ("Remove active material slot from active object\n"
                      "Can't be used in Edit Mode")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    # materials can't be removed in Edit mode
    def poll(cls, context):
        return (context.active_object is not None and
                not context.object.mode == 'EDIT')

    def execute(self, context):
        if context.selected_editable_objects:
            remove_materials(self, "SLOT")
            return {'FINISHED'}
        else:
            warning_messages(self, 'R_NO_SL_MAT')
            return {'CANCELLED'}


class VIEW3D_OT_material_remove_object(bpy.types.Operator):
    bl_idname = "view3d.material_remove_object"
    bl_label = "Remove all Slots (Active Object)"
    bl_description = ("Remove all material slots from active object\n"
                      "Can't be used in Edit Mode")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    # materials can't be removed in Edit mode
    def poll(cls, context):
        return (context.active_object is not None and
                not context.object.mode == 'EDIT')

    def execute(self, context):
        if context.selected_editable_objects:
            remove_materials(self, "ALL")
            return {'FINISHED'}
        else:
            warning_messages(self, 'R_NO_SL_MAT')
            return {'CANCELLED'}


class VIEW3D_OT_material_remove_all(bpy.types.Operator):
    bl_idname = "view3d.material_remove_all"
    bl_label = "Remove All Material Slots"
    bl_description = ("Remove all material slots from all selected objects \n"
                      "Can't be used in Edit Mode")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    # materials can't be removed in Edit mode
    def poll(cls, context):
        return (context.active_object is not None and
                not context.object.mode == 'EDIT')

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        if context.selected_editable_objects:
            remove_materials_all(self)
            return {'FINISHED'}
        else:
            warning_messages(self, 'R_NO_SL_MAT')
            return {'CANCELLED'}


class VIEW3D_OT_select_material_by_name(bpy.types.Operator):
    bl_idname = "view3d.select_material_by_name"
    bl_label = "Select Material By Name"
    bl_description = "Select geometry with this material assigned to it"
    bl_options = {'REGISTER', 'UNDO'}
    matname = StringProperty(
            name='Material Name',
            description='Name of Material to Select',
            maxlen=63,
            )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        mn = self.matname
        select_material_by_name(mn)
        warning_messages(self, 'SL_MAT_BY_NAME', mn)
        return {'FINISHED'}


class VIEW3D_OT_replace_material(bpy.types.Operator):
    bl_idname = "view3d.replace_material"
    bl_label = "Replace Material"
    bl_description = "Replace a material by name"
    bl_options = {'REGISTER', 'UNDO'}

    matorg = StringProperty(
            name="Original",
            description="Material to replace",
            maxlen=63,
            )
    matrep = StringProperty(
            name="Replacement",
            description="Replacement material",
            maxlen=63,
            )
    all_objects = BoolProperty(
            name="All objects",
            description="Replace for all objects in this blend file",
            default=True,
            )
    update_selection = BoolProperty(
            name="Update Selection",
            description="Select affected objects and deselect unaffected",
            default=True,
            )

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "matorg", bpy.data, "materials")
        layout.prop_search(self, "matrep", bpy.data, "materials")
        layout.prop(self, "all_objects")
        layout.prop(self, "update_selection")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        replace_material(self.matorg, self.matrep, self.all_objects, self.update_selection, self)
        return {'FINISHED'}


class VIEW3D_OT_fake_user_set(bpy.types.Operator):
    bl_idname = "view3d.fake_user_set"
    bl_label = "Set Fake User"
    bl_description = "Enable/disable fake user for materials"
    bl_options = {'REGISTER', 'UNDO'}

    fake_user = EnumProperty(
            name="Fake User",
            description="Turn fake user on or off",
            items=(('ON', "On", "Enable fake user"), ('OFF', "Off", "Disable fake user")),
            default='ON'
            )

    materials = EnumProperty(
            name="Materials",
            description="Which materials of objects to affect",
            items=(('ACTIVE', "Active object", "Materials of active object only"),
                   ('SELECTED', "Selected objects", "Materials of selected objects"),
                   ('SCENE', "Scene objects", "Materials of objects in current scene"),
                   ('USED', "Used", "All materials used by objects"),
                   ('UNUSED', "Unused", "Currently unused materials"),
                   ('ALL', "All", "All materials in this blend file")),
            default='UNUSED'
            )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "fake_user", expand=True)
        layout.prop(self, "materials")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        fake_user_set(self.fake_user, self.materials, self)
        return {'FINISHED'}


class MATERIAL_OT_mlrestore(bpy.types.Operator):
    bl_idname = "cycles.restore"
    bl_label = "Restore Cycles"
    bl_description = "Switch Back to Cycles Nodes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        CyclesNodeOn(self)
        return {'FINISHED'}


class MATERIAL_OT_set_transparent_back_side(bpy.types.Operator):
    bl_idname = "material.set_transparent_back_side"
    bl_label = "Transparent back (BI)"
    bl_description = "Creates BI nodes transparently mesh background"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if (not obj):
            return False
        mat = context.material
        if (not mat):
            return False
        if (mat.node_tree):
            if (len(mat.node_tree.nodes) == 0):
                return True
        if (not mat.use_nodes):
            return True
        return False

    def execute(self, context):
        mat = context.material
        mat.use_nodes = True
        if (mat.node_tree):
            for node in mat.node_tree.nodes:
                if (node):
                    mat.node_tree.nodes.remove(node)

        mat.use_transparency = True
        node_mat = mat.node_tree.nodes.new('ShaderNodeMaterial')
        node_out = mat.node_tree.nodes.new('ShaderNodeOutput')
        node_geo = mat.node_tree.nodes.new('ShaderNodeGeometry')
        node_mat.material = mat
        node_out.location = [node_out.location[0] + 500, node_out.location[1]]
        node_geo.location = [node_geo.location[0] + 150, node_geo.location[1] - 150]
        mat.node_tree.links.new(node_mat.outputs[0], node_out.inputs[0])
        mat.node_tree.links.new(node_geo.outputs[8], node_out.inputs[1])

        return {'FINISHED'}


class MATERIAL_OT_move_slot_top(bpy.types.Operator):
    bl_idname = "material.move_material_slot_top"
    bl_label = "Slot to the top"
    bl_description = "Move the active material slot on top"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if (not obj):
            return False
        if (len(obj.material_slots) <= 2):
            return False
        if (obj.active_material_index <= 0):
            return False
        return True

    def execute(self, context):
        activeObj = context.active_object

        for i in range(activeObj.active_material_index):
            bpy.ops.object.material_slot_move(direction='UP')

        active_mat = context.object.active_material
        if active_mat and hasattr(active_mat, "name"):
            warning_messages(self, 'MOVE_SLOT_UP', active_mat.name, 'MAT')

        return {'FINISHED'}


class MATERIAL_OT_move_slot_bottom(bpy.types.Operator):
    bl_idname = "material.move_material_slot_bottom"
    bl_label = "Slots to the bottom"
    bl_description = "Move the active material slot to the bottom"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if (not obj):
            return False
        if (len(obj.material_slots) <= 2):
            return False
        if (len(obj.material_slots) - 1 <= obj.active_material_index):
            return False
        return True

    def execute(self, context):
        activeObj = context.active_object
        lastSlotIndex = len(activeObj.material_slots) - 1

        for i in range(lastSlotIndex - activeObj.active_material_index):
            bpy.ops.object.material_slot_move(direction='DOWN')

        active_mat = context.object.active_material
        if active_mat and hasattr(active_mat, "name"):
            warning_messages(self, 'MOVE_SLOT_DOWN', active_mat.name, 'MAT')

        return {'FINISHED'}


class MATERIAL_OT_link_to_base_names(bpy.types.Operator):
    bl_idname = "material.link_to_base_names"
    bl_label = "Merge Base Names"
    bl_description = ("Replace .001, .002 slots with Original \n"
                      "Material/Name on All Materials/Objects")
    bl_options = {'REGISTER', 'UNDO'}

    mat_keep = StringProperty(name="Material to keep",
                              default="")
    is_auto = BoolProperty(name="Auto Rename/Replace",
                           description=("Automatically Replace names "
                                        "by stripping numerical suffix"),
                           default=False)
    mat_error = []          # collect mat for warning messages
    is_not_undo = False     # prevent drawing props on undo
    check_no_name = True    # check if no name is passed

    def draw(self, context):
        layout = self.layout
        if self.is_not_undo is True:
            boxee = layout.box()
            boxee.prop_search(self, "mat_keep", bpy.data, "materials")
            boxee.enabled = (True if self.is_auto is False else False)
            layout.separator()

            boxs = layout.box()
            boxs.prop(self, "is_auto", text="Auto Rename/Replace", icon="SYNTAX_ON")
        else:
            layout.label(text="**Only Undo is available**", icon="INFO")

    def invoke(self, context, event):
        self.is_not_undo = True
        return context.window_manager.invoke_props_dialog(self)

    def replace_name(self):
        # use the chosen material as a base one
        # check if there is a name
        self.check_no_name = (False if self.mat_keep in {""} else True)

        if self.check_no_name is True:
            for mat in bpy.data.materials:
                name = mat.name
                if name == self.mat_keep:
                    try:
                        base, suffix = name.rsplit('.', 1)
                        num = int(suffix, 10)
                        self.mat_keep = base
                        mat.name = self.mat_keep
                        return
                    except ValueError:
                        if name not in self.mat_error:
                            self.mat_error.append(name)
                        return
        return

    def split_name(self, material):
        name = material.name

        if '.' not in name:
            return name, None

        base, suffix = name.rsplit('.', 1)

        try:
            num = int(suffix, 10)
        except ValueError:
            # Not a numeric suffix
            if name not in self.mat_error:
                self.mat_error.append(name)
            return name, None

        if self.is_auto is False:
            if base == self.mat_keep:
                return base, suffix
            else:
                return name, None

        return base, suffix

    def fixup_slot(self, slot):
        if not slot.material:
            return

        base, suffix = self.split_name(slot.material)

        if suffix is None:
            return

        try:
            base_mat = bpy.data.materials[base]
        except KeyError:
            print('Base material %r not found' % base)
            return

        slot.material = base_mat

    def check(self, context):
        if self.is_not_undo is True:
            return True

    def main_loop(self, context):
        for ob in context.scene.objects:
            for slot in ob.material_slots:
                self.fixup_slot(slot)

    def execute(self, context):
        if self.is_auto is False:
            self.replace_name()
            if self.check_no_name is True:
                self.main_loop(context)
            else:
                warning_messages(self, 'MAT_LINK_NO_NAME')
                self.is_not_undo = False
                return {'CANCELLED'}

        self.main_loop(context)

        if use_cleanmat_slots():
            cleanmatslots()

        if self.mat_error:
            warning_messages(self, 'MAT_LINK_ERROR', self.mat_error, 'MAT')

        self.is_not_undo = False
        return {'FINISHED'}


class VIEW3D_OT_material_remove(bpy.types.Operator):
    """Remove all material slots from active objects"""
    bl_idname = "view3d.material_remove"
    bl_label = "Remove All Material Slots (Material Utils)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        remove_materials()
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# menu classes #
class VIEW3D_MT_assign_material(bpy.types.Menu):
    bl_label = "Assign Material"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_REGION_WIN'

        for material_name in bpy.data.materials.keys():
            layout.operator("view3d.assign_material",
                            text=material_name,
                            icon='MATERIAL_DATA').matname = material_name
        layout.separator()
        layout.operator("view3d.assign_material",
                        text="Add New",
                        icon='ZOOMIN')


class VIEW3D_MT_select_material(bpy.types.Menu):
    bl_label = "Select by Material"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_REGION_WIN'

        ob = context.object
        layout.label
        if ob.mode == 'OBJECT':
            # show all used materials in entire blend file
            for material_name, material in bpy.data.materials.items():
                if material.users > 0:
                    layout.operator("view3d.select_material_by_name",
                                    text=material_name,
                                    icon='MATERIAL_DATA',
                                    ).matname = material_name
        elif ob.mode == 'EDIT':
            # show only the materials on this object
            mats = ob.material_slots.keys()
            for m in mats:
                layout.operator("view3d.select_material_by_name",
                                text=m,
                                icon='MATERIAL_DATA').matname = m


class VIEW3D_MT_remove_material(bpy.types.Menu):
    bl_label = "Remove Materials"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_REGION_WIN'

        layout.operator("view3d.material_remove_slot", icon='COLOR_GREEN')
        layout.operator("view3d.material_remove_object", icon='COLOR_RED')

        if use_remove_mat_all():
            layout.separator()
            layout.operator("view3d.material_remove_all",
                            text="Remove Material Slots "
                            "(All Selected Objects)",
                            icon='CANCEL')


class VIEW3D_MT_delete_material(bpy.types.Menu):
    bl_label = "Clean Slots"
    bl_idname = "VIEW3D_MT_delete_material"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_REGION_WIN'
        layout.separator()
        layout.label(text="Selected Object Only")
        layout.operator("view3d.clean_material_slots",
                        text="Clean Material Slots",
                        icon='CANCEL')
        layout.operator("view3d.material_remove",
                        text="Remove Material Slots",
                        icon='CANCEL')
        self.layout.operator("material.link_to_base_names", icon='CANCEL', text="Merge Base Names")


class VIEW3D_MT_master_material(bpy.types.Menu):
    bl_label = "Material Specials Menu"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_REGION_WIN'

        if use_mat_preview():
            layout.operator("view3d.show_mat_preview", icon="VISIBLE_IPO_ON")
        layout.separator()

        layout.menu("VIEW3D_MT_assign_material", icon='ZOOMIN')
        layout.menu("VIEW3D_MT_select_material", icon='HAND')
        layout.operator("material.link_to_base_names", icon="INFO")

        if c_render_engine("Cycles"):
            # Cycles
            layout.operator("view3d.clean_material_slots",
                            text="Clean Material Slots",
                            icon='COLOR_BLUE')
            layout.operator("view3d.replace_material",
                            text='Replace Material',
                            icon='ARROW_LEFTRIGHT')
            layout.menu("VIEW3D_MT_remove_material", icon="COLORSET_10_VEC")

            layout.separator()
            layout.menu("VIEW3D_MT_delete_material", icon="COLOR_RED")

            layout.separator()
            layout.operator("view3d.fake_user_set",
                            text='Set Fake User',
                            icon='UNPINNED')

            layout.separator()
            # layout.label(text="Switch To Blender Render")
            layout.operator("ml.restore", text='BI Nodes Off', icon="APPEND_BLEND")
            layout.operator("xps_tools.restore_bi_materials_all", text='BI Nodes On', icon="APPEND_BLEND")

        elif c_render_engine("BI"):
            # Blender Internal
            layout.operator("view3d.replace_material",
                            text='Replace Material',
                            icon='ARROW_LEFTRIGHT')
            layout.operator("view3d.copy_material_to_selected", icon="COPY_ID")
            layout.operator("view3d.replace_material",
                            text='Replace Material',
                            icon='ARROW_LEFTRIGHT')

            layout.separator()
            layout.menu("VIEW3D_MT_delete_material", icon="COLOR_RED")

            layout.separator()
            layout.operator("view3d.fake_user_set",
                            text='Set Fake User',
                            icon='UNPINNED')
            layout.separator()
            layout.operator("object.rename",
                            text='Rename Image As Texture',
                            icon='TEXTURE')
            self.layout.separator()
            layout.operator("view3d.material_to_texface",
                            text="Material to Texface",
                            icon='MATERIAL_DATA')
            layout.operator("view3d.texface_to_material",
                            text="Texface to Material",
                            icon='TEXTURE_SHADED')
            layout.separator()
            # layout.label(text="Switch To Cycles Render")
            layout.operator("ml.refresh_active", text='Convert Active to Cycles', icon='NODE_INSERT_OFF')
            layout.operator("ml.refresh", text='Convert All to Cycles', icon='NODE_INSERT_ON')
            layout.operator("cycles.restore", text='Back to Cycles Nodes', icon='NODETREE')


# Specials Menu's #

def menu_func(self, context):
    layout = self.layout
    layout.operator_context = 'INVOKE_REGION_WIN'

    if context.scene.render.engine == "CYCLES":
        # Cycles
        layout.separator()
        layout.menu("VIEW3D_MT_assign_material", icon='ZOOMIN')
        layout.menu("VIEW3D_MT_select_material", icon='HAND')
        layout.operator("view3d.replace_material",
                        text='Replace Material',
                        icon='ARROW_LEFTRIGHT')

        layout.separator()
        layout.menu("VIEW3D_MT_delete_material", icon="COLOR_RED")

        layout.separator()
        layout.operator("view3d.fake_user_set",
                        text='Set Fake User',
                        icon='UNPINNED')
        layout.separator()
        layout.operator("object.rename",
                        text='Rename Image As Texture',
                        icon='TEXTURE')
        layout.separator()
        layout.label(text="Switch To Blender Render")
        layout.operator("ml.restore", text='BI Nodes Off', icon='APPEND_BLEND')
        layout.operator("xps_tools.restore_bi_materials_all", text='BI Nodes On', icon='APPEND_BLEND')

    elif context.scene.render.engine == "BLENDER_RENDER":
        # Blender Internal
        layout.separator()
        layout.menu("VIEW3D_MT_assign_material", icon='ZOOMIN')
        layout.menu("VIEW3D_MT_select_material", icon='HAND')
        layout.operator("view3d.replace_material",
                        text='Replace Material',
                        icon='ARROW_LEFTRIGHT')

        layout.separator()
        layout.menu("VIEW3D_MT_delete_material", icon="COLOR_RED")

        layout.separator()
        layout.operator("view3d.fake_user_set",
                        text='Set Fake User',
                        icon='UNPINNED')
        layout.separator()
        layout.operator("object.rename",
                        text='Rename Image As Texture',
                        icon='TEXTURE')
        self.layout.separator()
        layout.operator("view3d.material_to_texface",
                        text="Material to Texface",
                        icon='MATERIAL_DATA')
        layout.operator("view3d.texface_to_material",
                        text="Texface to Material",
                        icon='TEXTURE_SHADED')

        self.layout.separator()
        self.layout.operator("material.set_transparent_back_side", icon='TEXTURE_DATA', text="Transparent back (BI)")

        layout.separator()
        layout.label(text="Switch To Cycles Render")
        layout.operator("ml.refresh_active", text='Convert Active to Cycles', icon='NODE_INSERT_OFF')
        layout.operator("ml.refresh", text='Convert All to Cycles', icon='NODE_INSERT_ON')
        layout.operator("cycles.restore", text='Back to Cycles Nodes', icon='NODETREE')


def menu_move(self, context):
    layout = self.layout
    layout.operator_context = 'INVOKE_REGION_WIN'

    if context.scene.render.engine == "CYCLES":
        # Cycles
        self.layout.separator()
        self.layout.operator("material.move_material_slot_top", icon='TRIA_UP', text="Slot to top")
        self.layout.operator("material.move_material_slot_bottom", icon='TRIA_DOWN', text="Slot to bottom")

    elif context.scene.render.engine == "BLENDER_RENDER":
        # Blender Internal
        self.layout.separator()
        self.layout.operator("material.move_material_slot_top", icon='TRIA_UP', text="Slot to top")
        self.layout.operator("material.move_material_slot_bottom", icon='TRIA_DOWN', text="Slot to bottom")


# -----------------------------------------------------------------------------
# Addon Preferences

class VIEW3D_MT_material_utils_pref(bpy.types.AddonPreferences):
    bl_idname = __name__

    show_warnings = bpy.props.BoolProperty(
        name="Enable Warning messages",
        default=False,
        description="Show warning messages \n"
                    "when an action is executed or failed.\n \n"
                    "Advisable if you don't know how the tool works",
    )

    show_remove_mat = bpy.props.BoolProperty(
        name="Enable Remove all Materials",
        default=False,
        description="Enable Remove all Materials \n"
                    "for all Selected Objects \n \n"
                    "Use with care - if you want to keep materials after \n"
                    "closing \ reloading Blender Set Fake User for them",
    )

    show_mat_preview = bpy.props.BoolProperty(
        name="Enable Material Preview",
        default=True,
        description="Material Preview of the Active Object \n"
                    "Contains the preview of the active Material, \n"
                    "Use nodes, Color, Specular and Transparency \n"
                    "settings depending on the Context and Preferences",
    )

    set_cleanmatslots = bpy.props.BoolProperty(
        name="Enable Auto Clean",
        default=True,
        description="Enable Automatic Removal of unused Material Slots \n"
                    "called together with the Assign Material menu option. \n \n"
                    "Apart from preference and the cases when it affects \n"
                    "adding materials, enabling it can have some \n"
                    "performance impact on very dense meshes",
    )

    set_preview_size = bpy.props.EnumProperty(
        name="Preview Menu Size",
        description="Set the preview menu size \n"
                    "depending on the number of materials \n"
                    "in the scene (width and height)",
        items=(('2x2', "Size 2x2", "Width 2 Height 2"),
               ('2x3', "Size 2x3", "Width 3 Height 2"),
               ('3x3', "Size 3x3", "Width 3 Height 3"),
               ('3x4', "Size 3x4", "Width 4 Height 3"),
               ('4x4', "Size 4x4", "Width 4 Height 4"),
               ('5x5', "Size 5x5", "Width 5 Height 5"),
               ('6x6', "Size 6x6", "Width 6 Height 6"),
               ('0x0', "List", "Display as a List")),
        default='3x3',
    )

    set_preview_type = bpy.props.EnumProperty(
        name="Preview Menu Type",
        description="Set the the Preview menu type \n",
        items=(('LIST', "Classic",
                " Display as a Classic List like in Blender Propreties. \n \n"
                " Preview of Active Material not available"),
               ('PREVIEW', "Preview Display",
                " Display as a preview of Thumbnails \n"
                " It can have some performance issues with \n"
                " scenes containing a lot of materials \n \n"
                " Preview of Active Material available")),
        default='PREVIEW',
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        split = box.split(align=True)
        col = split.column()

        col.prop(self, "show_warnings")
        rowa = split.row()
        rowa.alignment = 'RIGHT'
        rowa.prop(self, "set_cleanmatslots")
        col.prop(self, "show_remove_mat")

        boxie = box.box()
        row = boxie.row()
        row.prop(self, "show_mat_preview")
        rowsy = row.split()
        rowsy.enabled = (True if self.show_mat_preview else False)
        rowsy.alignment = 'CENTER'
        rowsy.prop(self, "set_preview_type", text="")
        rowsa = rowsy.row()
        rowsa.enabled = (True if self.set_preview_type in {'PREVIEW'} else False)
        rowsa.alignment = 'CENTER'
        rowsa.prop(self, "set_preview_size", text="")


# -----------------------------------------------------------------------------
# utility functions:

def included_object_types(objects):
    # Pass the bpy.data.objects.type to avoid needless assigning/removing
    # included - type that can have materials
    included = ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META']

    obj = objects
    if (obj and obj in included):
        return True
    return False


def check_is_excluded_obj_types(contxt):
    # pass the context to check if selected objects have excluded types
    if contxt and contxt.selected_editable_objects:
        for obj in contxt.selected_editable_objects:
            if not included_object_types(obj.type):
                return True
    return False


def check_texface_to_mat(obj):
    # check for data presence
    if obj:
        if hasattr(obj.data, "uv_textures"):
            if hasattr(obj.data.uv_textures, "active"):
                if hasattr(obj.data.uv_textures.active, "data"):
                    return True
    return False


def c_context_mat_preview():
    # returns the type of viewport shading
    # because using the optional UI elements the context is lost it needs this check
    areas = bpy.context.screen.areas

    for area in areas:
        if area.type == 'VIEW_3D':
            return area.spaces.active.viewport_shade
    return "NONE"


def c_context_use_nodes():
    # checks if Use Nodes is ticked on
    actob = bpy.context.active_object
    u_node = (actob.active_material.use_nodes if hasattr(actob, "active_material") else False)

    if u_node:
        return True
    return False


def c_render_engine(cyc=None):
    # returns the active Renderer if not cyc is used
    # valid cyc inputs "Cycles", "BI", "Other"
    scene = bpy.context.scene
    render_engine = scene.render.engine

    if cyc:
        if cyc == "Cycles" and render_engine == 'CYCLES':
            return True
        elif cyc == "BI" and render_engine == 'BLENDER_RENDER':
            return True
        elif cyc == "Other" and render_engine not in ['CYCLES', 'BLENDER_RENDER']:
            return True
        return False
    return render_engine


def c_need_of_viewport_colors():
    # check the context where using Viewport color and friends are needed
    # Cycles and BI are supported
    if c_render_engine("Cycles"):
        if c_context_use_nodes():
            if c_context_mat_preview() == 'SOLID':
                return True
        elif c_context_mat_preview() in ('SOLID', 'TEXTURED', 'MATERIAL'):
            return True
    elif c_render_engine("BI"):
        if not c_context_use_nodes():
            return True
    return False


def use_remove_mat_all():
    pref = bpy.context.user_preferences.addons[__name__].preferences
    show_rmv_mat = pref.show_remove_mat

    if show_rmv_mat:
        return True
    return False


def use_mat_preview():
    pref = bpy.context.user_preferences.addons[__name__].preferences
    show_mat_prw = pref.show_mat_preview

    if show_mat_prw:
        return True
    return False


def use_cleanmat_slots():
    pref = bpy.context.user_preferences.addons[__name__].preferences
    use_mat_clean = pref.set_cleanmatslots

    if use_mat_clean:
        return True
    return False


def size_preview():
    pref = bpy.context.user_preferences.addons[__name__].preferences
    set_size_prw = pref.set_preview_size

    cell_w = int(set_size_prw[0])
    cell_h = int(set_size_prw[-1])
    cell_tbl = {'Width': cell_w, 'Height': cell_h}

    return cell_tbl


def size_type_is_preview():
    pref = bpy.context.user_preferences.addons[__name__].preferences
    set_prw_type = pref.set_preview_type

    if set_prw_type in {'PREVIEW'}:
        return True
    return False


def register():
    bpy.utils.register_module(__name__)

    warning_messages_utils.MAT_SPEC_NAME = __name__

    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        kmi = km.keymap_items.new('wm.call_menu', 'Q', 'PRESS', shift=True)
        kmi.properties.name = "VIEW3D_MT_master_material"

    bpy.types.MATERIAL_MT_specials.prepend(menu_move)
    bpy.types.MATERIAL_MT_specials.append(menu_func)


def unregister():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps["3D View"]
        for kmi in km.keymap_items:
            if kmi.idname == 'wm.call_menu':
                if kmi.properties.name == "VIEW3D_MT_master_material":
                    km.keymap_items.remove(kmi)
                    break

    bpy.types.MATERIAL_MT_specials.remove(menu_move)
    bpy.types.MATERIAL_MT_specials.remove(menu_func)
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
