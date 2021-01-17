import numpy as np
from time import time
import bpy
import gpu
import bgl
import blf
from gpu_extras.batch import batch_for_shader

from bpy.props import (BoolProperty,
                       StringProperty,
                       IntProperty,
                       FloatVectorProperty,
                       IntProperty,
                       PointerProperty,
                       EnumProperty)

bl_info = {
    "name": "Viewport Scrub Timeline",
    "description": "Scrub on timeline from viewport and snap to nearest keyframe",
    "author": "Samuel Bernou",
    "version": (0, 7, 1),
    "blender": (2, 91, 0),
    "location": "View3D > shortcut key chosen in addon prefs",
    "warning": "Work in progress (stable)",
    "doc_url": "https://github.com/Pullusb/scrub_timeline",
    "category": "Object"}


def nearest(array, value):
    '''
    Get a numpy array and a target value
    Return closest val found in array to passed value
    '''
    idx = (np.abs(array - value)).argmin()
    return array[idx]


def draw_callback_px(self, context):
    '''Draw callback use by modal to draw in viewport'''
    if context.area != self.current_area:
        return
    ## lines and shaders
    # 50% alpha, 2 pixel width line

    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')  # initiate shader
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glLineWidth(1)

    # - # Draw HUD
    if self.use_hud_time_line:
        shader.bind()
        shader.uniform_float("color", self.color_timeline)
        self.batch_timeline.draw(shader)

    # - # Display keyframes
    bgl.glLineWidth(3)
    shader.bind()
    shader.uniform_float("color", self.color_timeline)
    self.batch_keyframes.draw(shader)

    # - # Display keyframe as diamonds
    # for k in self.key_diamonds:
    #     batch = batch_for_shader(shader, 'TRIS', {"pos": k}, indices=self.indices)
    #     shader.bind()
    #     # shader.uniform_float("color", list(self.color_timeline[:3]) + [1]) # timeline color full opacity
    #     # shader.uniform_float("color", self.color_timeline)
    #     # shader.uniform_float("color", (0.8, 0.8, 0.8, 0.8)) # grey
    #     shader.uniform_float("color", (0.9, 0.69, 0.027, 1.0)) # yellow-ish
    #     # shader.uniform_float("color",(1.0, 0.515, 0.033, 1.0)) # orange 'selected keyframe'
    #     batch.draw(shader)

    # - # Show current frame line
    if self.use_hud_playhead:
        bgl.glLineWidth(1)
        # -# old full height playhead
        # playhead = [(self.cursor_x, 0), (self.cursor_x, context.area.height)]
        playhead = [(self.cursor_x, self.my + self.playhead_size/2),
                    (self.cursor_x, self.my - self.playhead_size/2)]
        batch = batch_for_shader(shader, 'LINES', {"pos": playhead})
        shader.bind()
        shader.uniform_float("color", self.color_playhead)
        batch.draw(shader)

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)

    # text
    font_id = 0

    # - # Display current frame text
    blf.color(font_id, *self.color_text)
    if self.use_hud_frame_current:
        blf.position(font_id, self.mouse[0]+10, self.mouse[1]+10, 0)
        # Id, Point size of the font, dots per inch value to use for drawing.
        blf.size(font_id, 30, self.dpi)  # 72
        blf.draw(font_id, f'{self.new_frame:.0f}')

    # - # Display frame offset text
    if self.use_hud_frame_offset:
        blf.position(font_id, self.mouse[0]+10,
                     self.mouse[1]+(40*self.ui_scale), 0)
        blf.size(font_id, 16, self.dpi)
        # blf.color(font_id, *self.color_text)
        sign = '+' if self.offset > 0 else ''
        blf.draw(font_id, f'{sign}{self.offset:.0f}')

    # Draw text debug infos at bottom left
    # blf.position(font_id, 15, 30, 0)
    # blf.size(font_id, 20, 72)
    # blf.draw(font_id, f'Infos - mouse coord: {self.mouse}')


class GPTS_OT_time_scrub(bpy.types.Operator):
    bl_idname = "animation.time_scrub"
    bl_label = "Time scrub"
    bl_description = "Quick time scrubbing with a shortcut"
    bl_options = {"REGISTER", "INTERNAL", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.space_data.type in ('VIEW_3D', 'SEQUENCE_EDITOR', 'CLIP_EDITOR')

    def invoke(self, context, event):
        prefs = get_addon_prefs()
        # Gpencil contexts : ('PAINT_GPENCIL', 'EDIT_GPENCIL')
        # if context.space_data.type != 'VIEW_3D':
        #     self.report({'WARNING'}, "Work only in Viewport")
        #     return {'CANCELLED'}

        self.current_area = context.area
        self.key = prefs.keycode
        self.evaluate_gp_obj_key = prefs.evaluate_gp_obj_key

        self.dpi = context.preferences.system.dpi
        self.ui_scale = context.preferences.system.ui_scale
        # hud prefs
        self.color_timeline = prefs.color_timeline
        self.color_playhead = prefs.color_playhead
        self.color_text = prefs.color_playhead
        self.use_hud_time_line = prefs.use_hud_time_line
        self.use_hud_playhead = prefs.use_hud_playhead
        self.use_hud_frame_current = prefs.use_hud_frame_current
        self.use_hud_frame_offset = prefs.use_hud_frame_offset

        self.playhead_size = prefs.playhead_size
        self.lines_size = prefs.lines_size

        self.px_step = prefs.pixel_step
        # global keycode
        # self.key = keycode
        self.snap_on = False
        self.mouse = (event.mouse_region_x, event.mouse_region_y)
        self.init_mouse_x = self.cursor_x = event.mouse_region_x  # event.mouse_x
        self.init_frame = self.new_frame = context.scene.frame_current
        self.offset = 0
        self.pos = []

        # Snap touch control
        self.snap_ctrl = not prefs.ts_use_ctrl
        self.snap_shift = not prefs.ts_use_shift
        self.snap_alt = not prefs.ts_use_alt
        self.snap_mouse_key = 'LEFTMOUSE' if self.key == 'RIGHTMOUSE' else 'RIGHTMOUSE'

        ob = context.object

        if context.space_data.type != 'VIEW_3D':
            ob = None  # do not consider any key

        if ob:  # condition to allow empty scrubing
            if ob.type != 'GPENCIL' or self.evaluate_gp_obj_key:
                # Get objet keyframe position
                anim_data = ob.animation_data
                action = None

                if anim_data:
                    action = anim_data.action
                if action:
                    for fcu in action.fcurves:
                        for kf in fcu.keyframe_points:
                            if kf.co.x not in self.pos:
                                self.pos.append(kf.co.x)

            if ob.type == 'GPENCIL':
                # Get GP frame position
                gpl = ob.data.layers
                layer = gpl.active
                if layer:
                    for frame in layer.frames:
                        if frame.frame_number not in self.pos:
                            self.pos.append(frame.frame_number)

        # - Add start and end to snap on
        if context.scene.use_preview_range:
            play_bounds = [context.scene.frame_preview_start,
                           context.scene.frame_preview_end]
        else:
            play_bounds = [context.scene.frame_start, context.scene.frame_end]

        self.pos += play_bounds
        self.pos = np.asarray(self.pos)

        self.hud = prefs.use_hud
        if not self.hud:
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        # - HUD params

        # line_height = 25 # px
        width = context.area.width
        right = int((width - self.init_mouse_x) / self.px_step)
        left = int(self.init_mouse_x / self.px_step)

        hud_pos_x = []
        for i in range(1, left):
            hud_pos_x.append(self.init_mouse_x - i*self.px_step)
        for i in range(1, right):
            hud_pos_x.append(self.init_mouse_x + i*self.px_step)

        # - list of double coords

        init_height = 60
        frame_height = self.lines_size
        key_height = 14

        self.my = my = event.mouse_region_y  # event.mouse_y

        self.hud_lines = []
        # - # frame marks
        for x in hud_pos_x:
            self.hud_lines.append((x, my - (frame_height/2)))
            self.hud_lines.append((x, my + (frame_height/2)))

        # - # init frame mark
        self.hud_lines += [(self.init_mouse_x, my - (init_height/2)),
                           (self.init_mouse_x, my + (init_height/2))]

        # - # Horizontal line
        self.hud_lines += [(0, my), (width, my)]

        # - #other method with cutted H line
        # leftmost = self.init_mouse_x - (left*self.px_step)
        # rightmost = self.init_mouse_x + (right*self.px_step)
        # self.hud_lines += [(leftmost, my), (rightmost, my)]

        # - # keyframe display
        self.key_lines = []
        for i in self.pos:
            self.key_lines.append(
                (self.init_mouse_x + ((i-self.init_frame) * self.px_step), my - (key_height/2)))
            self.key_lines.append(
                (self.init_mouse_x + ((i-self.init_frame)*self.px_step), my + (key_height/2)))

        # diamond version
        # keysize = 6 # 5 fpr square, 4 or 6 for diamond
        # upper = 0
        # self.key_diamonds = []
        # for i in self.pos:
        #     center = self.init_mouse_x + ((i-self.init_frame)*self.px_step)
        #     self.key_diamonds.append((
        #     (center-keysize, my+upper), (center, my+keysize+upper), # diamond
        #     (center+keysize, my+upper), (center, my-keysize+upper) # diamond
        #     # (center-keysize, my-keysize+upper), (center-keysize, my+keysize+upper), # square
        #     # (center+keysize, my+keysize+upper), (center+keysize, my-keysize+upper) # square
        #     ))
        # self.indices = ((0, 1, 2), (0, 2, 3))

        # Disable Onion skin
        self.active_space_data = context.space_data
        self.onion_skin = None
        if context.space_data.type == 'VIEW_3D':
            self.onion_skin = self.active_space_data.overlay.use_gpencil_onion_skin
            self.active_space_data.overlay.use_gpencil_onion_skin = False

        # - # Prepare batchs to draw static parts

        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')  # initiate shader
        self.batch_timeline = batch_for_shader(
            shader, 'LINES', {"pos": self.hud_lines})

        self.batch_keyframes = batch_for_shader(
            shader, 'LINES', {"pos": self.key_lines})

        args = (self, context)
        self.viewtype = None
        self.spacetype = 'WINDOW'  # is PREVIEW for VSE, needed for handler remove

        if context.space_data.type == 'VIEW_3D':
            self.viewtype = bpy.types.SpaceView3D
            self._handle = bpy.types.SpaceView3D.draw_handler_add(
                draw_callback_px, args, 'WINDOW', 'POST_PIXEL')

        # - # VSE disabling hud : Doesn't get right coordinates in preview window
        elif context.space_data.type == 'SEQUENCE_EDITOR':
            self.viewtype = bpy.types.SpaceSequenceEditor
            self.spacetype = 'PREVIEW'
            self._handle = bpy.types.SpaceSequenceEditor.draw_handler_add(
                draw_callback_px, args, 'PREVIEW', 'POST_PIXEL')

        elif context.space_data.type == 'CLIP_EDITOR':
            self.viewtype = bpy.types.SpaceClipEditor
            self._handle = bpy.types.SpaceClipEditor.draw_handler_add(
                draw_callback_px, args, 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _exit_modal(self, context):
        if self.onion_skin is not None:
            self.active_space_data.overlay.use_gpencil_onion_skin = self.onion_skin

        if self.hud and self.viewtype:
            self.viewtype.draw_handler_remove(self._handle, self.spacetype)
            context.area.tag_redraw()

    def modal(self, context, event):

        if event.type == 'MOUSEMOVE':
            # - calculate frame offset from pixel offset
            # - get mouse.x and add it to initial frame num
            self.mouse = (event.mouse_region_x, event.mouse_region_y)
            # self.mouse = (event.mouse_x, event.mouse_y)

            px_offset = (event.mouse_region_x - self.init_mouse_x)
            # int to overtake frame before change, use round to snap to closest (not blender style)
            self.offset = int(px_offset / self.px_step)
            self.new_frame = self.init_frame + self.offset

            mod_snap = False
            if self.snap_ctrl and event.ctrl:
                mod_snap = True
            if self.snap_shift and event.shift:
                mod_snap = True
            if self.snap_alt and event.alt:
                mod_snap = True

            if self.snap_on or mod_snap:
                self.new_frame = nearest(self.pos, self.new_frame)

            # context.scene.frame_set(self.new_frame)
            context.scene.frame_current = self.new_frame

            # - # follow exactly mouse
            # self.cursor_x = event.mouse_x

            # recalculate offset to snap cursor to frame
            self.offset = self.new_frame - self.init_frame
            # calculate cursor pixel position from frame offset
            self.cursor_x = self.init_mouse_x + (self.offset * self.px_step)
            # self._compute_timeline(context, event)

        if event.type == 'ESC':
            # context.scene.frame_set(self.init_frame)
            context.scene.frame_current = self.init_frame
            self._exit_modal(context)
            return {'CANCELLED'}

        # Snap if pressing NOT used mouse key (right or mid)
        if event.type == self.snap_mouse_key:
            if event.value == "PRESS":
                self.snap_on = True
            else:
                self.snap_on = False

        if event.type == self.key and event.value == 'RELEASE':
            self._exit_modal(context)
            return {'FINISHED'}

        # End modal on right clic release ? (relaunched immediately if main key not released)
        # if event.type == 'LEFTMOUSE':
        #     if event.value == "RELEASE":
        #         self._exit_modal(context)
        #         return {'FINISHED'}

        return {"RUNNING_MODAL"}

# --- addon prefs


def auto_rebind(self, context):
    unregister_keymaps()
    register_keymaps()


class GPTS_OT_set_scrub_keymap(bpy.types.Operator):
    bl_idname = "animation.ts_set_keymap"
    bl_label = "Change keymap"
    bl_description = "Quick time scrubbing with a shortcut"
    bl_options = {"REGISTER", "INTERNAL"}

    def invoke(self, context, event):
        self.prefs = get_addon_prefs()
        self.ctrl = False
        self.shift = False
        self.alt = False

        self.init_value = self.prefs.keycode
        self.prefs.keycode = ''
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        exclude_keys = {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE',
                        'TIMER_REPORT', 'ESC', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}
        exclude_in = ('SHIFT', 'CTRL', 'ALT')
        if event.type == 'ESC':
            self.prefs.keycode = self.init_value
            # self.report({'WARNING'}, 'Cancelled')
            return {'CANCELLED'}

        self.ctrl = event.ctrl
        self.shift = event.shift
        self.alt = event.alt

        if event.type not in exclude_keys and not any(x in event.type for x in exclude_in):
            print('key:', event.type, 'value:', event.value)
            if event.value == 'PRESS':
                self.report({'INFO'}, event.type)
                # set the chosen key
                self.prefs.keycode = event.type
                # -# following condition aren't needed. Just here to avoid unnecessary rebind update (if possible)
                if self.prefs.ts_use_shift != event.shift:  # condition
                    self.prefs.ts_use_shift = event.shift

                if self.prefs.ts_use_alt != event.alt:
                    self.prefs.ts_use_alt = event.alt

                # -# Trigger rebind update with last
                self.prefs.ts_use_ctrl = event.ctrl

                # -# no need to rebind updated by of the modifiers props..
                # auto_rebind()
                return {'FINISHED'}

        return {"RUNNING_MODAL"}


class GPTS_addon_prefs(bpy.types.AddonPreferences):
    bl_idname = __name__

    keycode: StringProperty(
        name="Shortcut",
        description="Shortcut to trigger the scrub in viewport during press",
        default="MIDDLEMOUSE")

    ts_use_shift: BoolProperty(
        name="Combine With Shift",
        description="Add shift",
        default=False,
        update=auto_rebind)

    ts_use_alt: BoolProperty(
        name="Combine With Alt",
        description="Add alt",
        default=True,
        update=auto_rebind)

    ts_use_ctrl: BoolProperty(
        name="Combine With Ctrl",
        description="Add ctrl",
        default=False,
        update=auto_rebind)

    evaluate_gp_obj_key: BoolProperty(
        name='Use Gpencil object keyframes',
        description="Also snap on greasepencil object keyframe (else only active layer frames)",
        default=True)

    # options (set) – Enumerator in ['HIDDEN', 'SKIP_SAVE', 'ANIMATABLE', 'LIBRARY_EDITABLE', 'PROPORTIONAL','TEXTEDIT_UPDATE'].
    pixel_step: IntProperty(
        name="Frame Interval On Screen",
        description="Pixel steps on screen that represent a frame intervals",
        default=10,
        min=1,
        max=500,
        soft_min=2,
        soft_max=100,
        step=1,
        subtype='PIXEL')

    use_hud: BoolProperty(
        name='Display HUD',
        description="Display overlays with timeline information when scrubbing time in viewport",
        default=True)

    use_hud_time_line: BoolProperty(
        name='Timeline',
        description="Display a static marks to represent timeline overlay when scrubbing time in viewport",
        default=True)

    use_hud_playhead: BoolProperty(
        name='Playhead',
        description="Display the playhead as a vertical line to show position in time",
        default=True)

    use_hud_frame_current: BoolProperty(
        name='Text Frame Current',
        description="Display the current frame as text above mouse cursor",
        default=True)

    use_hud_frame_offset: BoolProperty(
        name='Text Frame Offset',
        description="Display frame offset from initial position as text above mouse cursor",
        default=True)

    color_timeline: FloatVectorProperty(
        name="Timeline Color",
        subtype='COLOR',
        size=4,
        default=(0.5, 0.5, 0.5, 0.6),
        min=0.0, max=1.0,
        description="Color of the temporary timeline"
    )

    color_playhead: FloatVectorProperty(
        name="Cusor Color",
        subtype='COLOR',
        size=4,
        default=(0.01, 0.64, 1.0, 0.8),  # red (0.9, 0.3, 0.3, 0.8)
        min=0.0, max=1.0,
        description="Color of the temporary line cursor and text"
    )

    # - # sizes
    playhead_size: IntProperty(
        name="Playhead Size",
        description="Playhead height in pixels",
        default=100,
        min=2,
        max=10000,
        soft_min=10,
        soft_max=5000,
        step=1,
        subtype='PIXEL')

    lines_size: IntProperty(
        name="Frame Lines Size",
        description="Frame lines height in pixels",
        default=10,
        min=1,
        max=10000,
        soft_min=5,
        soft_max=40,
        step=1,
        subtype='PIXEL')

    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True

        # - # General settings
        layout.prop(self, 'evaluate_gp_obj_key')
        # Make a keycode capture system or find a way to display keymap with full_event=True
        layout.prop(self, 'pixel_step')

        # -/ Keymap -
        box = layout.box()
        box.label(text='Keymap:')
        box.operator('animation.ts_set_keymap',
                     text='Click here to change shortcut')

        if self.keycode:
            row = box.row(align=True)
            row.prop(self, 'ts_use_ctrl', text='Ctrl')
            row.prop(self, 'ts_use_alt', text='Alt')
            row.prop(self, 'ts_use_shift', text='Shift')
            # -/Cosmetic-
            icon = None
            if self.keycode == 'LEFTMOUSE':
                icon = 'MOUSE_LMB'
            elif self.keycode == 'MIDDLEMOUSE':
                icon = 'MOUSE_MMB'
            elif self.keycode == 'RIGHTMOUSE':
                icon = 'MOUSE_RMB'
            if icon:
                row.label(text=f'{self.keycode}', icon=icon)
            # -Cosmetic-/
            else:
                row.label(text=f'Key: {self.keycode}')

        else:
            box.label(text='[ NOW TYPE KEY OR CLICK TO USE, WITH MODIFIER ]')

        snap_text = 'Snap to keyframes: '
        snap_text += 'Left Mouse' if self.keycode == 'RIGHTMOUSE' else 'Right Mouse'
        if not self.ts_use_ctrl:
            snap_text += ' or Ctrl'
        if not self.ts_use_shift:
            snap_text += ' or Shift'
        if not self.ts_use_alt:
            snap_text += ' or Alt'
        box.label(text=snap_text, icon='SNAP_ON')
        if self.keycode in ('LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE') and not self.ts_use_ctrl and not self.ts_use_alt and not self.ts_use_shift:
            box.label(
                text="Recommended to choose at least one modifier to combine with clicks (default: Ctrl+Alt)", icon="ERROR")

        # - # HUD/OSD

        box = layout.box()
        box.prop(self, 'use_hud')

        col = box.column()
        row = col.row()
        row.prop(self, 'color_timeline')
        row.prop(self, 'color_playhead', text='Cursor And Text Color')
        col.label(text='Show:')
        row = col.row()
        row.prop(self, 'use_hud_time_line')
        row.prop(self, 'use_hud_playhead')
        row = col.row()
        row.prop(self, 'use_hud_frame_current')
        row.prop(self, 'use_hud_frame_offset')
        row = col.row()
        row.prop(self, 'playhead_size')
        row.prop(self, 'lines_size')
        col.enabled = self.use_hud


def get_addon_prefs():
    import os
    addon_name = os.path.splitext(__name__)[0]
    preferences = bpy.context.preferences
    addon_prefs = preferences.addons[addon_name].preferences
    return addon_prefs

# --- Keymap


addon_keymaps = []


def register_keymaps():
    prefs = get_addon_prefs()
    addon = bpy.context.window_manager.keyconfigs.addon
    # km = addon.keymaps.new(name = "3D View", space_type = "VIEW_3D")
    km = addon.keymaps.new(name="Grease Pencil",
                           space_type="EMPTY", region_type='WINDOW')

    if not prefs.keycode:
        print(r'/!\ Timeline scrub: no keycode entered for keymap')
        return
    kmi = km.keymap_items.new(
        'animation.time_scrub',
        type=prefs.keycode, value='PRESS',
        alt=prefs.ts_use_alt, ctrl=prefs.ts_use_ctrl, shift=prefs.ts_use_shift, any=False)
    kmi.repeat = False
    addon_keymaps.append((km, kmi))


def unregister_keymaps():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

# --- REGISTER ---


classes = (
    GPTS_addon_prefs,
    GPTS_OT_time_scrub,
    GPTS_OT_set_scrub_keymap,
)


def register():
    # other_file.register()
    for cls in classes:
        bpy.utils.register_class(cls)

    # if not bpy.app.background:
    register_keymaps()

    #bpy.types.Scene.pgroup_name = bpy.props.PointerProperty(type = GPTS_PGT_settings)


def unregister():
    # if not bpy.app.background:
    unregister_keymaps()
    # other_file.unregister()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    #del bpy.types.Scene.pgroup_name


if __name__ == "__main__":
    register()
