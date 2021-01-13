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
    "version": (0, 6, 1),
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

        self.ts_mouse_shortcut = prefs.ts_mouse_shortcut
        self.ts_mouse_click = prefs.ts_mouse_click
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
        self.snap_mouse_key = 'LEFTMOUSE' if self.ts_mouse_click == 'RIGHTMOUSE' else 'RIGHTMOUSE'

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

        # - Add start and end to snap on ?
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
        # TODO how to trace the grid only once

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
        args = (self, context)  # HUD

        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_px, args, 'WINDOW', 'POST_PIXEL')  # HUD
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _exit_modal(self, context):
        if self.onion_skin is not None:
            self.active_space_data.overlay.use_gpencil_onion_skin = self.onion_skin
        if self.hud:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            context.area.tag_redraw()

    def modal(self, context, event):
        # -# /TESTER - keycode printer (flood console but usefull to know a keycode name)
        # , 'LEFTMOUSE'# avoid flood of mouse move.
        # if event.type not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TIMER_REPORT'}:
        #     print('key:', event.type, 'value:', event.value)
        #     if event.value == 'PRESS':
        #         self.report({'INFO'}, event.type)
        # -#  TESTER/

        if event.type == 'MOUSEMOVE':
            # - calculate frame offset from pixel offset
            # - get mouse.x and add it to initial frame num
            self.mouse = (event.mouse_region_x, event.mouse_region_y)
            # self.mouse = (event.mouse_x, event.mouse_y)

            px_offset = (event.mouse_region_x - self.init_mouse_x)
            # int to overtake frame before change, use round to snap to closest (not blender style)
            self.offset = int(px_offset / self.px_step)
            self.new_frame = self.init_frame + self.offset

            if self.ts_mouse_shortcut:
                mod_snap = False
                if self.snap_ctrl and event.ctrl:
                    mod_snap = True
                if self.snap_shift and event.shift:
                    mod_snap = True
                if self.snap_alt and event.alt:
                    mod_snap = True

                if self.snap_on or mod_snap:
                    self.new_frame = nearest(self.pos, self.new_frame)

            else:
                if self.snap_on or event.ctrl:
                    self.new_frame = nearest(self.pos, self.new_frame)
                    # snap mode

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

        # - # Mouse
        if self.ts_mouse_shortcut:
            # Snap if pressing NOT used mouse key (right or mid)
            if event.type == self.snap_mouse_key:
                if event.value == "PRESS":
                    self.snap_on = True
                else:
                    self.snap_on = False

            if event.type == self.ts_mouse_click and event.value == 'RELEASE':
                self._exit_modal(context)
                return {'FINISHED'}

        # - # Single press
        else:
            # snap if using right mouse
            if event.type == 'RIGHTMOUSE':
                if event.value == "PRESS":
                    self.snap_on = True
                else:
                    self.snap_on = False

                # self.new_frame = nearest(self.pos, self.new_frame)
                # self.offset = self.new_frame - self.init_frame
                # context.scene.frame_current = self.new_frame

            # if event.type in {'RIGHTMOUSE', 'ESC'}:

            if event.type == self.key and event.value == "RELEASE":
                # - trigger key release
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


class GPTS_addon_prefs(bpy.types.AddonPreferences):
    bl_idname = __name__

    ts_mouse_shortcut: BoolProperty(
        name='Use Mouse & Modifier Shortcut',
        description="Use a trigger shortcut with modifier + mouse pressed",
        default=True,
        update=auto_rebind)

    ts_mouse_click: EnumProperty(
        name="Mouse button",
        description="Click on right/left/middle mouse button in combination with a modifier",
        default='LEFTMOUSE',
        items=(
            ('RIGHTMOUSE', 'Right click',
             'Use click on Right mouse button', 'MOUSE_RMB', 0),
            ('LEFTMOUSE', 'Left click',
             'Use click on Left mouse button', 'MOUSE_LMB', 1),
            ('MIDDLEMOUSE', 'Mid click',
             'Use click on Mid mouse button', 'MOUSE_MMB', 2),
        ),
        update=auto_rebind)

    ts_use_shift: BoolProperty(
        name="combine with shift",
        description="add shift",
        default=False,
        update=auto_rebind)

    ts_use_alt: BoolProperty(
        name="combine with alt",
        description="add alt",
        default=True,
        update=auto_rebind)

    ts_use_ctrl: BoolProperty(
        name="combine with ctrl",
        description="add ctrl",
        default=True,
        update=auto_rebind)

    keycode: StringProperty(
        name="Shortcut",
        description="Shortcut to trigger the scrub in viewport during press",
        default="F5",
    )

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
        # row = layout.row(align=True)
        box = layout.box()

        box.prop(self, "ts_mouse_shortcut")  # , expand=True
        if self.ts_mouse_shortcut:
            row = box.row()
            # row.operator("prefs.rebind_shortcut", text='Bind/Rebind shortcuts', icon='FILE_REFRESH')#EVENT_SPACEKEY
            row = box.row(align=True)
            row.prop(self, "ts_use_ctrl", text='Ctrl')  # , expand=True
            row.prop(self, "ts_use_alt", text='Alt')  # , expand=True
            row.prop(self, "ts_use_shift", text='Shift')  # , expand=True
            row.prop(self, "ts_mouse_click", text='')  # expand=True

            snap_text = 'Snap to keyframes: '

            snap_text += 'Left Mouse' if self.ts_mouse_click == 'RIGHTMOUSE' else 'Right Mouse'
            if not self.ts_use_ctrl:
                snap_text += ' or Ctrl'
            if not self.ts_use_shift:
                snap_text += ' or Shift'
            if not self.ts_use_alt:
                snap_text += ' or Alt'

            box.label(text=snap_text, icon='SNAP_ON')  # DECORATE_KEYFRAME
            if not self.ts_use_ctrl and not self.ts_use_alt and not self.ts_use_shift:
                box.label(
                    text="Recommanded to choose at least one modifier to combine with click (default: Ctrl+Alt)", icon="ERROR")
        else:
            box.prop(self, 'keycode')
            box.label(text='Snap to keyframes: Right Mouse or Ctrl',
                      icon='SNAP_ON')  # DECORATE_KEYFRAME
        layout.prop(self, 'evaluate_gp_obj_key')
        # Make a keycode capture system or find a way to display keymap with full_event=True
        layout.prop(self, 'pixel_step')

        layout.prop(self, 'use_hud')

        col = layout.column()
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

    if prefs.ts_mouse_shortcut:
        kmi = km.keymap_items.new(
            'animation.time_scrub',
            type=prefs.ts_mouse_click, value="PRESS",
            alt=prefs.ts_use_alt, ctrl=prefs.ts_use_ctrl, shift=prefs.ts_use_shift, any=False)
    else:

        kmi = km.keymap_items.new(
            'animation.time_scrub',
            type=prefs.keycode, value='PRESS')
        kmi.repeat = False
        # kmi = km.keymap_items.new(
        #     name="name",
        #     idname="animation.time_scrub",
        #     type="F",
        #     value="PRESS",
        #     shift=True,
        #     ctrl=True,
        #     alt = False,
        #     oskey=False
        #     )
    addon_keymaps.append((km, kmi))


def unregister_keymaps():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

# --- REGISTER ---


classes = (
    GPTS_addon_prefs,
    GPTS_OT_time_scrub,
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
