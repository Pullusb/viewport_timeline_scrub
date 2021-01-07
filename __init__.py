import numpy as np
from time import time
import bpy
import gpu
import bgl
import blf
from gpu_extras.batch import batch_for_shader

bl_info = {
    "name": "Viewport Scrub Timeline",
    "description": "Scrub on timeline from viewport and snap to nearest keyframe",
    "author": "Samuel Bernou",
    "version": (0, 4, 0),
    "blender": (2, 91, 0),
    "location": "View3D",
    "warning": "",
    "doc_url": "https://github.com/Pullusb/scrub_timeline",
    "category": "Object"}

'''
- question
Most important:
for the shortcut:
    use a "on press" key (without pressing key, currently used)
    use shortcut + mouse press ? (complex do right clic + left clic press with a tablet pen...)

Currently use only GP keys:
  Does it need to have a separate "mode" for GP keys and Objects keys

Other:
Should it disable onion skin like normal scrubbing does
Should it pause playback lauched during play ?
Snap on key by default ?

- drawbacks
add an undo step containing timeline move. If not, a ctrl+Z after a new stroke move back timeline)

# TODO
- user chosen keymap in preferences ! most difficult
- change dot per inch according to user prefs
- Check possible defaut shortcut with GP team, Lison, Mathieu

HUD
- OK Use an horizontal ruler display for frame move (stuck on bottom or top)
- OK vertical thin line for current position
- OK snap to showed keyframe
- OK show text
- OK prefs to customize appeareance
- OK add frame offset value as text
- OK prefs conditions for activate only parts of HUD
- add source frame as text ? (draw depending on timeline HUD placement)
- display marks for start and end ?
- display marks for keyframes ?

-- ideas
- Use also in other editors with a per editor behavior (difficult to find a cross editor shortcuts):
  - on 3D view (active layer key only)
  - on GP dopesheet : all layers keys (or only active same as above)
  - on object dopesheet : considering all object keys

# allowed_key = ('NONE', 'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE', 'BUTTON4MOUSE', 'BUTTON5MOUSE', 'BUTTON6MOUSE', 'BUTTON7MOUSE', 'PEN', 'ERASER', 'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TRACKPADPAN', 'TRACKPADZOOM', 'MOUSEROTATE', 'MOUSESMARTZOOM', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE', 'EVT_TWEAK_L', 'EVT_TWEAK_M', 'EVT_TWEAK_R', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'LEFT_CTRL', 'LEFT_ALT', 'LEFT_SHIFT', 'RIGHT_ALT', 'RIGHT_CTRL', 'RIGHT_SHIFT', 'OSKEY', 'APP', 'GRLESS', 'ESC', 'TAB', 'RET', 'SPACE', 'LINE_FEED', 'BACK_SPACE', 'DEL', 'SEMI_COLON', 'PERIOD', 'COMMA', 'QUOTE', 'ACCENT_GRAVE', 'MINUS', 'PLUS', 'SLASH', 'BACK_SLASH', 'EQUAL', 'LEFT_BRACKET', 'RIGHT_BRACKET', 'LEFT_ARROW', 'DOWN_ARROW', 'RIGHT_ARROW', 'UP_ARROW', 'NUMPAD_2', 'NUMPAD_4', 'NUMPAD_6', 'NUMPAD_8', 'NUMPAD_1', 'NUMPAD_3', 'NUMPAD_5', 'NUMPAD_7', 'NUMPAD_9', 'NUMPAD_PERIOD', 'NUMPAD_SLASH', 'NUMPAD_ASTERIX', 'NUMPAD_0', 'NUMPAD_MINUS', 'NUMPAD_ENTER', 'NUMPAD_PLUS', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12', 'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F20', 'F21', 'F22', 'F23', 'F24', 'PAUSE', 'INSERT', 'HOME', 'PAGE_UP', 'PAGE_DOWN', 'END', 'MEDIA_PLAY', 'MEDIA_STOP', 'MEDIA_FIRST', 'MEDIA_LAST', 'TEXTINPUT', 'WINDOW_DEACTIVATE', 'TIMER', 'TIMER0', 'TIMER1', 'TIMER2', 'TIMER_JOBS', 'TIMER_AUTOSAVE', 'TIMER_REPORT', 'TIMERREGION', 'NDOF_MOTION', 'NDOF_BUTTON_MENU', 'NDOF_BUTTON_FIT', 'NDOF_BUTTON_TOP', 'NDOF_BUTTON_BOTTOM', 'NDOF_BUTTON_LEFT', 'NDOF_BUTTON_RIGHT', 'NDOF_BUTTON_FRONT', 'NDOF_BUTTON_BACK', 'NDOF_BUTTON_ISO1', 'NDOF_BUTTON_ISO2', 'NDOF_BUTTON_ROLL_CW', 'NDOF_BUTTON_ROLL_CCW', 'NDOF_BUTTON_SPIN_CW', 'NDOF_BUTTON_SPIN_CCW', 'NDOF_BUTTON_TILT_CW', 'NDOF_BUTTON_TILT_CCW', 'NDOF_BUTTON_ROTATE', 'NDOF_BUTTON_PANZOOM', 'NDOF_BUTTON_DOMINANT', 'NDOF_BUTTON_PLUS', 'NDOF_BUTTON_MINUS', 'NDOF_BUTTON_ESC', 'NDOF_BUTTON_ALT', 'NDOF_BUTTON_SHIFT', 'NDOF_BUTTON_CTRL', 'NDOF_BUTTON_1', 'NDOF_BUTTON_2', 'NDOF_BUTTON_3', 'NDOF_BUTTON_4', 'NDOF_BUTTON_5', 'NDOF_BUTTON_6', 'NDOF_BUTTON_7', 'NDOF_BUTTON_8', 'NDOF_BUTTON_9', 'NDOF_BUTTON_10', 'NDOF_BUTTON_A', 'NDOF_BUTTON_B', 'NDOF_BUTTON_C', 'ACTIONZONE_AREA', 'ACTIONZONE_REGION', 'ACTIONZONE_FULLSCREEN')
'''

def nearest(array, value):
    '''
    Get a numpy array and a target value
    Return closest val found in array to passed value
    '''
    idx = (np.abs(array - value)).argmin()
    return array[idx]


""" def draw_timeline(self, context):
    # Draw HUD only once and disable when leaving
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')  # initiate shader
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glLineWidth(1)

    for line in self.hud_lines:
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": line})
        shader.bind()
        shader.uniform_float("color", self.color_timeline)  # grey-light
        batch.draw(shader)

    # restore opengl defaults
    bgl.glDisable(bgl.GL_BLEND) """


def draw_callback_px(self, context):
    '''Draw callback use by modal to draw in viewport'''
    ## lines and shaders
    # 50% alpha, 2 pixel width line
    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')  # initiate shader
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glLineWidth(1)
    # bgl.glLineWidth(2)

    # - # Draw HUD
    if self.use_hud_time_line:
        for line in self.hud_lines:
            batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": line})
            shader.bind()
            shader.uniform_float("color", self.color_timeline)  # grey-light
            batch.draw(shader)

    # Show current frame line
    if self.use_hud_time_cursor:
        current = [(self.cursor_x, 0), (self.cursor_x, context.area.height)]
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": current})
        # batch = batch_for_shader(shader, 'LINES', {"pos": self.hud_lines})
        shader.bind()
        shader.uniform_float("color", self.color_cursor)  # light red
        batch.draw(shader)

    # restore opengl defaults
    bgl.glDisable(bgl.GL_BLEND)

    # text
    font_id = 0

    # TODO change dot per inch according to user prefs
    if self.use_hud_frame_current:
        # - # Display current frame
        blf.position(font_id, self.mouse[0]+10, self.mouse[1]+10, 0)
        # Id, Point size of the font, dots per inch value to use for drawing.
        blf.size(font_id, 30, self.dpi) # 72
        # blf.color(font_id, 0.9, 0.3, 0.3, 0.6)
        blf.color(font_id, *self.color_text)
        blf.draw(font_id, f'{self.new_frame}')


    # - # Display frame offset
    if self.use_hud_frame_offset:
        blf.position(font_id, self.mouse[0]+10, self.mouse[1]+40, 0)
        blf.size(font_id, 16, self.dpi) # 72
        # blf.color(font_id, *self.color_text)
        sign = '+' if self.offset > 0 else ''
        blf.draw(font_id, f'{sign}{self.offset}')

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
        return context.object and context.space_data.type == 'VIEW_3D'

    def invoke(self, context, event):
        prefs = get_addon_prefs()
        # if context.mode not in ('PAINT_GPENCIL', 'EDIT_GPENCIL'):
        #     return {"CANCELLED"}

        if context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "Work only in Viewport")
            return {'CANCELLED'}

        self.key = prefs.keycode

        self.dpi = context.preferences.system.dpi
        ## hud prefs
        self.color_timeline = prefs.color_timeline
        self.color_cursor = prefs.color_cursor
        self.color_text = prefs.color_cursor
        self.use_hud_time_line = prefs.use_hud_time_line
        self.use_hud_time_cursor = prefs.use_hud_time_cursor
        self.use_hud_frame_current = prefs.use_hud_frame_current
        self.use_hud_frame_offset = prefs.use_hud_frame_offset

        self.px_step = prefs.pixel_step
        # global keycode
        # self.key = keycode
        self.snap_on = False
        self.mouse = (event.mouse_region_x, event.mouse_region_y)
        self.init_mouse_x = self.cursor_x = event.mouse_region_x  # event.mouse_x
        self.init_frame = context.scene.frame_current
        self.offset = 0
        self.pos = []



        ob = context.object

        # if context.space_data.type == 'DOPESHEET'

        # action_name = (ob.animation_data.action.name if ob.animation_data is not None and ob.animation_data.action is not None else "")

        # if len(action_name):
        #     actions = bpy.data.actions[action_name]

        #     # Iterate through action curve
        #     for fcu in actions.fcurves:
        #         for keyframe in fcu.keyframe_points:
        #             if keyframe.co.x not in self.pos:
        #                 self.pos.append(keyframe.co.x)

        if ob.type == 'GPENCIL':
            # elif type(ob.data) is bpy.types.GreasePencil:
            gpl = ob.data.layers
            layer = gpl.active
            if layer is None:
                self.report({'ERROR'}, "No active layer in current object")
                return {'CANCELLED'}

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
        frame_height = 30

        height = context.area.height
        if prefs.hud_position == 'BOTTOM':
            self.hud_lines = [((x, 0), (x, frame_height)) for x in hud_pos_x]
            self.hud_lines += [((self.init_mouse_x, 0),
                                (self.init_mouse_x, init_height))]

        elif prefs.hud_position == 'TOP':
            self.hud_lines = [((x, height), (x, height - frame_height - 30))
                              for x in hud_pos_x]
            self.hud_lines += [((self.init_mouse_x, height),
                                (self.init_mouse_x, height - init_height - 30))]

        else:  # MOUSE
            # - At mouse pos
            my = event.mouse_region_y  # event.mouse_y
            self.hud_lines = [((x, my - (frame_height/2)),
                               (x, my + (frame_height/2))) for x in hud_pos_x]
            self.hud_lines += [((self.init_mouse_x, my - (init_height/2)),
                                (self.init_mouse_x, my + (init_height/2)))]
            # -# H line
            # leftmost = self.init_mouse_x - (left*self.px_step)
            # rightmost = self.init_mouse_x + (right*self.px_step)
            # self.hud_lines += [((leftmost, my), (rightmost, my))]
            self.hud_lines += [((0, my), (width, my))]

        args = (self, context)  # HUD
        # TODO check if possible to draw timeline only once

        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_px, args, 'WINDOW', 'POST_PIXEL')  # HUD
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _exit_modal(self, context):
        if self.hud:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            context.area.tag_redraw()
        # print(f'Stopped {time()}')

    # snap_on : bpy.props.BoolProperty(default=False)

    def modal(self, context, event):
        # -# /TESTER - keycode printer (flood console but usefull to know a keycode name)
        # , 'LEFTMOUSE'# avoid flood of mouse move.
        # if event.type not in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TIMER_REPORT'}:
        #     print('key:', event.type, 'value:', event.value)
        #     if event.value == 'PRESS':
        #         self.report({'INFO'}, event.type)
        # -#  TESTER/
       
        ## snap if using right mouse
        if event.type == 'RIGHTMOUSE':
            if event.value == "PRESS":
                self.snap_on = True
            else:
                self.snap_on = False

            # self.new_frame = nearest(self.pos, self.new_frame)
            # self.offset = self.new_frame - self.init_frame
            # context.scene.frame_current = self.new_frame

        if event.type == 'MOUSEMOVE':
            # - calculate frame offset from pixel offset
            # - get mouse.x and add it to initial frame num
            self.mouse = (event.mouse_region_x, event.mouse_region_y)
            px_offset = (event.mouse_x - self.init_mouse_x)
            # int to overtake frame before change, use round to snap to closest (not blender style)
            self.offset = int(px_offset / self.px_step)
            self.new_frame = self.init_frame + self.offset

            if event.ctrl or self.snap_on:
                # snap mode
                self.new_frame = nearest(self.pos, self.new_frame)

            # context.scene.frame_set(self.new_frame)
            context.scene.frame_current = self.new_frame

            # - # follow exactly mouse
            # self.cursor_x = event.mouse_x

            # recalculate offset to snap cursor to frame
            self.offset = self.new_frame - self.init_frame
            # calculate cursor pixel position from frame offset
            self.cursor_x = self.init_mouse_x + (self.offset * self.px_step)


        # if event.type in {'RIGHTMOUSE', 'ESC'}:
        if event.type == 'ESC':
            # context.scene.frame_set(self.init_frame)
            context.scene.frame_current = self.init_frame
            return {'CANCELLED'}

        if event.type == self.key and event.value == "RELEASE":
            # - trigger key release
            self._exit_modal(context)
            return {'FINISHED'}

        if event.type == 'LEFTMOUSE':
            # print('leftmouse')
            if event.value == "RELEASE":
                # print('touch release')
                # - clic release...
                self._exit_modal(context)
                # - ? check left or right select ? (tablet is always left when draw anyway)
                return {'FINISHED'}

        # return {'PASS_THROUGH'}
        return {"RUNNING_MODAL"}

    # def draw(self, context):
    #     layout = self.layout
    #     layout.prop(self, "shift")


# --- addon prefs


class GPTS_addon_prefs(bpy.types.AddonPreferences):
    bl_idname = __name__

    keycode: bpy.props.StringProperty(
        name="Shortcut",
        description="Shortcut to trigger the scrub in viewport during press",
        default="F5",
    )

    # options (set) – Enumerator in ['HIDDEN', 'SKIP_SAVE', 'ANIMATABLE', 'LIBRARY_EDITABLE', 'PROPORTIONAL','TEXTEDIT_UPDATE'].
    pixel_step: bpy.props.IntProperty(
        name="Frame Interval On Screen",
        description="Pixel steps on screen that represent a frame intervals",
        default=10,
        min=1,
        max=500,
        soft_min=2,
        soft_max=100,
        step=1,
        subtype='PIXEL')

    use_hud: bpy.props.BoolProperty(
        name='Display HUD',
        description="Display overlays with timeline information when scrubbing time in viewport",
        default=True)

    use_hud_time_line: bpy.props.BoolProperty(
        name='Timeline',
        description="Display a static marks to represent timeline overlay when scrubbing time in viewport",
        default=True)
    
    use_hud_time_cursor: bpy.props.BoolProperty(
        name='Current Time',
        description="Display a vertical line to show position in time",
        default=True)
    
    use_hud_frame_current: bpy.props.BoolProperty(
        name='Text Frame Current',
        description="Display the current frame as text above mouse cursor",
        default=True)
    
    use_hud_frame_offset: bpy.props.BoolProperty(
        name='Text Frame Offset',
        description="Display frame offset from initial position as text above mouse cursor",
        default=True)

    hud_position: bpy.props.EnumProperty(
        items=(('MOUSE', "Mouse Cursor",
                "Display timeline at mouse position", 'MOUSE_MOVE', 0),
               ('TOP', "Viewport Top",
                "Display timeline at the top of the viewport", 'TRIA_UP_BAR', 1),
               ('BOTTOM', "Viewport Bottom",
                "Display timeline at the bottom of the viewport", 'TRIA_DOWN_BAR', 2),
               ),
        name='Timeline Display Position',
        default='MOUSE',
        description='Choose HUD position to display temporary timeline intervals')

    color_timeline: bpy.props.FloatVectorProperty(
        name="Timeline Color",
        subtype='COLOR',
        size=4,
        default=(0.5, 0.5, 0.5, 0.6),
        min=0.0, max=1.0,
        description="Color of the temporary timeline"
    )

    color_cursor: bpy.props.FloatVectorProperty(
        name="Cusor Color",
        subtype='COLOR',
        size=4,
        default=(0.9, 0.3, 0.3, 0.8),
        min=0.0, max=1.0,
        description="Color of the temporary line cursor and text"
    )

    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True
        # row = layout.row(align=True)

        layout.prop(self, 'keycode')
        # Make a keycode capture system or find a way to display keymap with full_event=True
        layout.prop(self, 'pixel_step')
        
        layout.prop(self, 'use_hud')
        
        col = layout.column()
        row = col.row()
        row.prop(self, 'color_timeline')
        row.prop(self, 'color_cursor', text='Cursor And Text Color')
        col.label(text='Show:')
        row = col.row()
        row.prop(self, 'use_hud_time_line')
        row.prop(self, 'use_hud_time_cursor')
        row = col.row()
        row.prop(self, 'use_hud_frame_current')
        row.prop(self, 'use_hud_frame_offset')
        col.prop(self, 'hud_position', text='Display Timeline At')
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

    kmi = km.keymap_items.new(
        'animation.time_scrub', type=prefs.keycode, value='PRESS')
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
    # GPTS_PGT_settings,
    GPTS_addon_prefs,
    GPTS_OT_time_scrub,
    # GPTS_PT_proj_panel,
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
