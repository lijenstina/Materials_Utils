import bpy


MAT_SPEC_NAME = "materials_specials"

def warning_messages(operator=None, warn='DEFAULT', object_name="", is_mat=None, fake=""):
    # Enter warning messages to the message dictionary
    # warn - if nothing passed falls back to DEFAULT
    # a list of strings can be passed and concatenated in obj_name too
    # is_mat a switch to change to materials or textures for obj_name('MAT','TEX', 'FILE', None)
    # fake - optional string that can be passed
    # MAX_COUNT - max members of an list to be displayed
    obj_name = ""
    MAX_COUNT = 6
    gramma_s, gramma_p = " - has ", " - have "

    if is_mat:
        if is_mat in {'MAT'}:
            gramma_s, gramma_p = " - Material has ", " - Materials have "
        elif is_mat in {'TEX'}:
            gramma_s, gramma_p = " - Texture has ", " - Textures have "
        elif is_mat in {'FILE'}:
            gramma_s, gramma_p = " - File ", " - Files "

    # pass the show_warnings bool to enable/disable them
    addon = bpy.context.user_preferences.addons[MAT_SPEC_NAME]
    show_warn = (addon.preferences.show_warnings if addon else False)
    if show_warn and operator:
        if object_name:
            if type(object_name) is list:
                obj_name = ", ".join(object_name)
                if (1 < len(object_name) <= MAX_COUNT):
                    obj_name = obj_name + gramma_p
                elif (len(object_name) > MAX_COUNT):
                    abbrevation = ("(Multiple)" if is_mat else "(Multiple Objects)")
                    obj_name = abbrevation + gramma_p
                elif (len(object_name) == 1):
                    obj_name = obj_name + gramma_s
            else:
                obj_name = object_name + gramma_s

        message = {
            'EMPTY': "" + fake,
            'DEFAULT': "No editable selected objects, could not finish",
            'RMV_EDIT': obj_name + "Unable to remove material slot in edit mode",
            'A_OB_MIX_NO_MAT': obj_name + "No Material applied. Object type can't have materials",
            'A_MAT_NAME_EDIT': obj_name + " been applied to selection",
            'C_OB_NO_MAT': obj_name + "No Materials. Unused material slots are "
            "not cleaned",
            'C_OB_MIX_NO_MAT': obj_name + "No Materials or an Object type that "
            "can't have Materials (Clean Material Slots)",
            'R_OB_NO_MAT': obj_name + "No Materials. Nothing to remove",
            'R_NO_SL_MAT': "No Selection. Material slots are not removed",
            'R_ALL_SL_MAT': "All materials removed from selected objects",
            'R_ALL_NO_MAT': "Object(s) have no materials to remove",
            'R_ACT_MAT': obj_name + "Removed active Material",
            'R_ACT_MAT_ALL': obj_name + "Removed all Material from the Object",
            'SL_MAT_BY_NAME': "Objects with the Material " + obj_name + "been selected",
            'OB_CANT_MAT': obj_name + "Object type that can't have Materials",
            'REP_MAT_NONE': "Replace Material: No materials replaced",
            'FAKE_SET_ON': obj_name + "set Fake user " + fake,
            'FAKE_SET_OFF': obj_name + "disabled Fake user " + fake,
            'FAKE_NO_MAT': "Fake User Settings: Object(s) with no Materials or no changes needed",
            'CPY_MAT_MIX_OB': "Copy Materials to others: Some of the Object types can't have Materials",
            'TEX_MAT_NO_SL': "Texface to Material: No Selected Objects",
            'TEX_MAT_NO_CRT': obj_name + "not met the conditions for the tool (UVs, Active Images) ",
            'MAT_TEX_NO_SL': "Material to Texface: No Selected Objects",
            'MAT_TEX_NO_MESH': obj_name + "not met the conditions for the tool (Mesh)",
            'MAT_TEX_NO_MAT': obj_name + "not met the conditions for the tool (Material)",
            'BI_SW_NODES_OFF': "Switching to Blender Render, Use Nodes disabled",
            'BI_SW_NODES_ON': "Switching to Blender Render, Use Nodes enabled",
            'CYC_SW_NODES_ON': "Switching back to Cycles, Use Nodes enabled",
            'TEX_RENAME_F': obj_name + "no Images assigned, skipping",
            'NO_TEX_RENAME': "No Textures in Data, nothing to rename",
            'TEX_D_T_ERROR': obj_name + "or Directory without writing privileges",
            'TEX_PATH_ERROR': obj_name + "Missing Path(s)",
            'DIR_PATH_W_ERROR': "ERROR: Directory without writing privileges",
            'DIR_PATH_N_ERROR': "ERROR: Directory not existing",
            'DIR_PATH_A_ERROR': "ERROR: Directory not accessible",
            'DIR_PATH_W_OK': "Directory has writing privileges",
            'MAT_LINK_ERROR': obj_name + "not be renamed or set as Base(s)",
            'MAT_LINK_NO_NAME': "No Base name given, No changes applied",
            'MOVE_SLOT_UP': obj_name + "been moved on top of the stack",
            'MOVE_SLOT_DOWN': obj_name + "been moved to the bottom of the stack",
            'MAT_TRNSP_BACK': obj_name + "been set with Alpha connected to Front/Back Geometry node",
            }

        operator.report({'INFO'}, message[warn])
