# Viewport scrub timeline

Move in the timeline directly in viewport and snap to nearest keyframe

## Note : This standalone feature is integrated in native add-on _Grease Pencil Tools_ (Shipped with Blender since 2.93)  
## It is recommended to use Grease pencil tools as it is generally more up to date.


**[Download latest](https://github.com/Pullusb/viewport_timeline_scrub/archive/main.zip)**

<!-- ### [Demo Youtube]() -->

---  

## Description

Pop-up a timeline in viewport so you can reduce mouse travel distance (or work full screen)
Available in following editors: 3D viewport, Movie Clip and VSE

![Viewport scrubbing in time](https://github.com/Pullusb/images_repo/raw/master/Bl_scrub_timeline_preview.gif)

**Viewport timeline** : `Alt + MMB (middle mouse button)` (default)

Use addon preference to customize shortcut, display colors and behavior.

Use designated shortcut in viewport to call the temporary timeline and scrub

**Snap to nearest keyframe** : While scrubbing, use a modifier key not used as trigger or `Right click` (`Left` if you use Right as trigger)


---


<!-- - question
Other:
Should it disable onion skin like normal scrubbing does
Should it pause playback launched during play (and keep stop after) ?
Snap on key by default ?

- drawbacks
add an undo step containing timeline move. If not, a ctrl+Z after a new stroke move back timeline)

### TODO


- HUD: add source frame as text ? (tested... too much information on screen)

-- ideas
- Use directly color from the theme (mainly for cursor user cursor)

- Weird idea : Use also in timeline editor editors with a per editor behavior (difficult to find a cross editor shortcuts):
  - on 3D view (active layer key only)
  - on GP dopesheet : all layers keys (or only active same as above)
  - on object dopesheet : considering all object keys

Done:
- OK vertical thin line for current position
- OK snap to showed keyframe
- OK show text
- OK prefs to customize color appeareance
- OK add frame offset value as text
- OK prefs conditions to activate only parts of HUD
- OK reduce size of frame lines
- OK Change default color
- OK Display marks for start and end
-->

<!-- allowed_key = ('NONE', 'LEFTMOUSE', 'MIDDLEMOUSE', 'RIGHTMOUSE', 'BUTTON4MOUSE', 'BUTTON5MOUSE', 'BUTTON6MOUSE', 'BUTTON7MOUSE', 'PEN', 'ERASER', 'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE', 'TRACKPADPAN', 'TRACKPADZOOM', 'MOUSEROTATE', 'MOUSESMARTZOOM', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'WHEELINMOUSE', 'WHEELOUTMOUSE', 'EVT_TWEAK_L', 'EVT_TWEAK_M', 'EVT_TWEAK_R', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'LEFT_CTRL', 'LEFT_ALT', 'LEFT_SHIFT', 'RIGHT_ALT', 'RIGHT_CTRL', 'RIGHT_SHIFT', 'OSKEY', 'APP', 'GRLESS', 'ESC', 'TAB', 'RET', 'SPACE', 'LINE_FEED', 'BACK_SPACE', 'DEL', 'SEMI_COLON', 'PERIOD', 'COMMA', 'QUOTE', 'ACCENT_GRAVE', 'MINUS', 'PLUS', 'SLASH', 'BACK_SLASH', 'EQUAL', 'LEFT_BRACKET', 'RIGHT_BRACKET', 'LEFT_ARROW', 'DOWN_ARROW', 'RIGHT_ARROW', 'UP_ARROW', 'NUMPAD_2', 'NUMPAD_4', 'NUMPAD_6', 'NUMPAD_8', 'NUMPAD_1', 'NUMPAD_3', 'NUMPAD_5', 'NUMPAD_7', 'NUMPAD_9', 'NUMPAD_PERIOD', 'NUMPAD_SLASH', 'NUMPAD_ASTERIX', 'NUMPAD_0', 'NUMPAD_MINUS', 'NUMPAD_ENTER', 'NUMPAD_PLUS', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12', 'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F20', 'F21', 'F22', 'F23', 'F24', 'PAUSE', 'INSERT', 'HOME', 'PAGE_UP', 'PAGE_DOWN', 'END', 'MEDIA_PLAY', 'MEDIA_STOP', 'MEDIA_FIRST', 'MEDIA_LAST', 'TEXTINPUT', 'WINDOW_DEACTIVATE', 'TIMER', 'TIMER0', 'TIMER1', 'TIMER2', 'TIMER_JOBS', 'TIMER_AUTOSAVE', 'TIMER_REPORT', 'TIMERREGION', 'NDOF_MOTION', 'NDOF_BUTTON_MENU', 'NDOF_BUTTON_FIT', 'NDOF_BUTTON_TOP', 'NDOF_BUTTON_BOTTOM', 'NDOF_BUTTON_LEFT', 'NDOF_BUTTON_RIGHT', 'NDOF_BUTTON_FRONT', 'NDOF_BUTTON_BACK', 'NDOF_BUTTON_ISO1', 'NDOF_BUTTON_ISO2', 'NDOF_BUTTON_ROLL_CW', 'NDOF_BUTTON_ROLL_CCW', 'NDOF_BUTTON_SPIN_CW', 'NDOF_BUTTON_SPIN_CCW', 'NDOF_BUTTON_TILT_CW', 'NDOF_BUTTON_TILT_CCW', 'NDOF_BUTTON_ROTATE', 'NDOF_BUTTON_PANZOOM', 'NDOF_BUTTON_DOMINANT', 'NDOF_BUTTON_PLUS', 'NDOF_BUTTON_MINUS', 'NDOF_BUTTON_ESC', 'NDOF_BUTTON_ALT', 'NDOF_BUTTON_SHIFT', 'NDOF_BUTTON_CTRL', 'NDOF_BUTTON_1', 'NDOF_BUTTON_2', 'NDOF_BUTTON_3', 'NDOF_BUTTON_4', 'NDOF_BUTTON_5', 'NDOF_BUTTON_6', 'NDOF_BUTTON_7', 'NDOF_BUTTON_8', 'NDOF_BUTTON_9', 'NDOF_BUTTON_10', 'NDOF_BUTTON_A', 'NDOF_BUTTON_B', 'NDOF_BUTTON_C', 'ACTIONZONE_AREA', 'ACTIONZONE_REGION', 'ACTIONZONE_FULLSCREEN') -->


## Changelog:

0.8.0

- big update to match advance made in the GP Tools 1.4.0 built-in blender 2.93
- Always snap mode
- Rolling timeline
- fixes

0.7.6

- Now respect "limit to frame range" option if activated

0.7.5

- UI: added keyframe display option and reorganise
- fix: Changed addon pref color to gamma corrected
- code: refactor for easier merge with GP tools
  - renamed props
  - Separate addon prefs draw and properties


0.7.4

- fix: bug when HUD is disabled

0.7.3

- feat: Added native scrub with in timeline editors with addon defined shortcut (Same ops as `shift Right mouse`):
  - `Dopesheet`
  - `Graph Editor`
  - `NLA Editor`
  - `Sequencer`
  - ! not in `Clip Graph Editor` Where the behavior is broken...
- Added preference option to enable/disable shortcut propagation in timeline editors

0.7.2

- fix: VSE display now working as expected (HUD on preview window)
- feat: add bracket style lines to display frame range
- fix: hide the misleading keyframe icon on start/end frame range

0.7.0

- feat: Custom Keymapping change:
  - Modal ops to choose shortcut by pressing it
  - Customisable shortcut allowed (both mouse or keyboard)

- cleanup: Removed all swapping conditions between mouse and key

- UI: rearrange by category

- doc: update infos

0.6.2

- Added support to scrub in VSE and Movie clip editor:
  - Movie clip OK
  - Disable HUD in VSE for now. get wrong screen coordinates in preview window

0.6.1

- feat: Mouse + modifier shortcut (enabled by default):
  - Automatically change snap key to unused modifiers and click

0.6.0

- perf: Improved drawing performance (thanks to [J.Fran Matheu](https://twitter.com/jfranmatheu) for his answers on this)
  - Prepare static drawing batches in invoke
  - Use a more appropriate GPU preset for drawing lines

- UI: Less distractive display 
  - Reduced overall lines heights and changed default playhead color to blue.
  - Exposed lines heights in addon prefs (for testing purpose, might stay if interesting to customize)

- Cleanup: Removed custom timeline placement (top/bottom)

- fix: Overlapping texts when user ui scale is bigger than default

- doc: Marked as WIP in bl_infos


0.5.0

- feat: Display keyframes on timeline

- feat: Consider objects key (non-GP object)

- new pref: Consider GP objet key for snapping/display (defaut=True)

- fix: Allow "empty" scrubbing (when there is no active object)

- fix: Problem with onion skin auto-hide whne using Esc to go back to init frame

- doc: Better readme with demo gif

0.4.2

- fix: display HUD/OSD only in active viewport

- fix: non blocking error with an uninitialized frame variable

- disable onion skin during the modal

0.4.1

- fix: corrected an offset bug in time when viewport used was not leftmost in screen

0.4.0

- Base text overlay dpi according to user settings

- Snap mode on left click + continuous press

0.3.0

- initial commit
