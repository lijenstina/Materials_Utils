bl_info = {"name": "Texture Renamer", "category": "Material"}

import bpy
from bpy.props import StringProperty
from . import warning_messages_utils
from .warning_messages_utils import warning_messages


class SimpleOp(bpy.types.Operator):
    bl_idname = "object.rename"
    bl_label = "Texture Renamer"
    bl_description = ("Replace the Texture names pattern with \n"
                      "the attached Image ones. \n"
                      "Works on all Textures (Including Brushes) \n \n"
                      "The First field - the name pattern to replace \n"
                      "The Second - searches for existing names \n")
    bl_options = {'REGISTER', 'UNDO'}

    def_name = "Texture"    # default name
    is_not_undo = False     # prevent drawing props on undo
    named = StringProperty(name="Search for name",
                           default=def_name)

    def draw(self, context):
        layout = self.layout
        if self.is_not_undo is True:
            box = layout.box()

            box.prop(self, "named", text="Name pattern", icon="SYNTAX_ON")
            layout.separator()

            boxs = layout.box()
            boxs.prop_search(self, "named", bpy.data, "textures")
        else:
            layout.label(text="**Only Undo is available**", icon="INFO")

    def invoke(self, context, event):
        self.is_not_undo = True
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        errors = []     # collect texture names without images attached
        tex_count = 0   # check if there is textures at all

        for texture in bpy.data.textures:
            try:
                if texture and self.named in texture.name and texture.type == "IMAGE":
                    tex_count += 1
                    textname = ""
                    img = (bpy.data.textures[texture.name].image if bpy.data.textures[texture.name] else None)
                    if not img:
                        errors.append(str(texture.name))
                    for word in img.name:
                        if word != ".":
                            textname = textname + word
                        else:
                            break
                    texture.name = textname
                if texture.type != "IMAGE":  # rename specific textures as clouds, environnement map,...
                    texture.name = texture.type.lower()
            except:
                continue

        if tex_count == 0:
            warning_messages(self, 'NO_TEX_RENAME')
        elif errors:
            warning_messages(self, 'TEX_RENAME_F', errors, 'TEX')

        # reset name to default
        self.named = self.def_name

        self.is_not_undo = False

        return {'FINISHED'}


class HWPl(bpy.types.Panel):
    # Creates a Panel in the scene context of the properties editor
    bl_label = "Texture Rename"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "texture"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.rename")


def register():
    bpy.utils.register_class(HWPl)
    bpy.utils.register_class(SimpleOp)


def unregister():
    bpy.utils.unregister_class(HWPl)
    bpy.utils.unregister_class(SimpleOp)

if __name__ == "__main__":
    register()
