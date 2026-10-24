"""ModernGL renderer for the procedural operating room (room3d + screens3d).

Shares the GL context of GPUEyePreview. Lighting is a stylized model: a
hemisphere ambient term, broad ceiling light, the surgical lamp as a warm
spotlight on the patient's head, Blinn-Phong highlights on metal and gamma
correction. Scenes render into a 4x multisample buffer when the driver
allows it. Display only: nothing here reads input or changes the Game.
"""
from __future__ import annotations

from array import array
import math

from .room3d import (CAMERAS, EYE_LIFT, EYE_POS, MATERIALS, SCREENS, Camera, column_major, dynamic_room,
                     eye_disc, lamp_position, static_room, view_projection)

ROOM_VERTEX = """
#version 330
uniform mat4 u_mvp;
in vec3 in_position;
in vec3 in_normal;
out vec3 v_pos;
out vec3 v_normal;
void main() {
    v_pos = in_position;
    v_normal = in_normal;
    gl_Position = u_mvp * vec4(in_position, 1.0);
}
"""
ROOM_FRAGMENT = """
#version 330
uniform vec3 u_color;
uniform float u_spec;
uniform float u_emit;
uniform vec3 u_camera;
uniform vec3 u_lamp;
uniform vec3 u_lamp_dir;
in vec3 v_pos;
in vec3 v_normal;
out vec4 fragColor;
vec3 to_linear(vec3 c) { return pow(c, vec3(2.2)); }
void main() {
    vec3 n = normalize(v_normal);
    vec3 view = normalize(u_camera - v_pos);
    if (dot(n, view) < 0.0) n = -n;
    vec3 base = to_linear(u_color);
    // Hemisphere ambient: bright ceiling, darker floor bounce.
    vec3 sky = vec3(0.62, 0.68, 0.74), ground = vec3(0.20, 0.21, 0.22);
    vec3 light = mix(ground, sky, n.y * 0.5 + 0.5) * 0.55;
    // Broad ceiling panels (soft key from above).
    vec3 key = normalize(vec3(0.25, 1.0, 0.35));
    light += vec3(0.95, 0.97, 1.0) * max(dot(n, key), 0.0) * 0.55;
    // Surgical lamp: warm spotlight towards the operative eye.
    vec3 to_lamp = u_lamp - v_pos;
    float dist = length(to_lamp);
    vec3 l = to_lamp / dist;
    float cone = smoothstep(0.86, 0.97, dot(-l, u_lamp_dir));
    float lamp = cone * max(dot(n, l), 0.0) * 1.9 / (1.0 + 0.25 * dist * dist);
    light += vec3(1.0, 0.96, 0.88) * lamp;
    vec3 colour = base * light;
    // Highlights from the key light and the lamp.
    vec3 h1 = normalize(key + view), h2 = normalize(l + view);
    float shine = pow(max(dot(n, h1), 0.0), 40.0) * 0.35 + pow(max(dot(n, h2), 0.0), 60.0) * cone * 1.4;
    colour += vec3(shine * u_spec);
    colour += base * u_emit;
    // Slight distance haze keeps the far walls behind the table.
    float fog = clamp((length(u_camera - v_pos) - 4.0) / 10.0, 0.0, 0.35);
    colour = mix(colour, vec3(0.42, 0.46, 0.50), fog);
    // Filmic-style exposure curve keeps lamp-lit instruments from clipping.
    colour = vec3(1.0) - exp(-colour * 1.35);
    fragColor = vec4(pow(colour, vec3(1.0 / 2.2)), 1.0);
}
"""
SCREEN_VERTEX = """
#version 330
uniform mat4 u_mvp;
in vec3 in_position;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = u_mvp * vec4(in_position, 1.0);
}
"""
SCREEN_FRAGMENT = """
#version 330
uniform sampler2D u_image;
uniform float u_gain;
uniform float u_round;
in vec2 v_uv;
out vec4 fragColor;
void main() {
    if (u_round > 0.5 && length(v_uv - vec2(0.5)) > 0.5) discard;
    vec3 c = texture(u_image, v_uv).rgb * u_gain;
    // Faint glass reflection towards the top of the panel.
    c += vec3(0.05) * smoothstep(0.55, 1.0, 1.0 - v_uv.y) * (1.0 - u_round);
    fragColor = vec4(c, 1.0);
}
"""


class RoomRenderer:
    """Draws the operating room with the given camera into the current frame."""

    def __init__(self, ctx, moderngl, pygame) -> None:
        from .gl_preview import pack_mesh
        self.ctx = ctx
        self.gl = moderngl
        self.pg = pygame
        self.program = ctx.program(vertex_shader=ROOM_VERTEX, fragment_shader=ROOM_FRAGMENT)
        self.screen_program = ctx.program(vertex_shader=SCREEN_VERTEX,
                                          fragment_shader=SCREEN_FRAGMENT)
        self._pack = pack_mesh
        self.static = {name: self._upload(mesh) for name, mesh in static_room().items()}
        self.dynamic: dict[str, tuple] = {}
        self.dynamic_key: tuple | None = None
        self.textures: dict[str, object] = {}
        self.quads = {name: self._quad(screen.corners()) for name, screen in SCREENS.items()}
        vertices, uvs, faces = eye_disc()
        data = array("f")
        for (x, y, z), (u, v) in zip(vertices, uvs):
            data.extend((x, y + EYE_LIFT, z, u, v))
        index = array("I", [i for face in faces for i in face])
        vb, ib = ctx.buffer(data.tobytes()), ctx.buffer(index.tobytes())
        self.eye = (ctx.vertex_array(self.screen_program, [(vb, "3f 2f", "in_position", "in_uv")],
                                     index_buffer=ib), vb, ib)
        self.fbo = None
        self.fbo_size = None
        self.samples = min(4, getattr(ctx, "max_samples", 0) or 0)

    def _upload(self, mesh) -> tuple:
        vertex_bytes, index_bytes, _ = self._pack(mesh)
        vb = self.ctx.buffer(vertex_bytes)
        ib = self.ctx.buffer(index_bytes)
        vao = self.ctx.vertex_array(self.program, [(vb, "3f 3f", "in_position", "in_normal")],
                                    index_buffer=ib)
        return vao, vb, ib

    def _quad(self, corners) -> tuple:
        bl, br, tl, tr = corners
        data = array("f", (*bl, 0., 1., *br, 1., 1., *tl, 0., 0., *tr, 1., 0.))
        vb = self.ctx.buffer(data.tobytes())
        vao = self.ctx.vertex_array(self.screen_program, [(vb, "3f 2f", "in_position", "in_uv")])
        return vao, vb

    def set_people(self, tool: str | None, active_phase: bool) -> None:
        key = (tool, active_phase)
        if key == self.dynamic_key:
            return
        for vao, vb, ib in self.dynamic.values():
            vao.release(); vb.release(); ib.release()
        self.dynamic = {name: self._upload(mesh) for name, mesh in dynamic_room(*key).items()}
        self.dynamic_key = key

    def set_screens(self, surfaces: dict) -> None:
        """Upload new display contents (pygame surfaces, RGB)."""
        for name, surface in surfaces.items():
            size = surface.get_size()
            texture = self.textures.get(name)
            if texture is None or texture.size != size:
                if texture is not None:
                    texture.release()
                texture = self.textures[name] = self.ctx.texture(size, 3)
                texture.filter = (self.gl.LINEAR, self.gl.LINEAR)
            texture.write(self.pg.image.tobytes(surface, "RGB"))

    def _target(self, w: int, h: int):
        # ctx.screen keeps its creation size; blitting a resized buffer onto
        # it is not portable, so a resized window renders without MSAA.
        if self.samples < 2 or tuple(self.ctx.screen.size) != (w, h):
            return None
        if self.fbo_size != (w, h):
            if self.fbo is not None:
                self.fbo.release()
            colour = self.ctx.renderbuffer((w, h), 4, samples=self.samples)
            depth = self.ctx.depth_renderbuffer((w, h), samples=self.samples)
            self.fbo = self.ctx.framebuffer(color_attachments=[colour], depth_attachment=depth)
            self.fbo_size = (w, h)
        return self.fbo

    def draw(self, camera: Camera | str, w: int, h: int) -> None:
        """Render into the default framebuffer (via the MSAA buffer if any)."""
        if isinstance(camera, str):
            camera = CAMERAS[camera]
        ctx = self.ctx
        target = self._target(w, h)
        screen_fb = ctx.screen
        if target is not None:
            target.use()
        ctx.viewport = (0, 0, w, h)
        ctx.clear(.42, .46, .50, 1.0, depth=1.0)
        ctx.enable(self.gl.DEPTH_TEST)
        ctx.disable(self.gl.CULL_FACE)
        ctx.disable(self.gl.BLEND)
        mvp = column_major(view_projection(camera, w / h))
        lamp = lamp_position()
        d = tuple(e - l for e, l in zip(EYE_POS, lamp))
        length = math.sqrt(sum(c * c for c in d))
        p = self.program
        p["u_mvp"].value = mvp
        p["u_camera"].value = camera.eye
        p["u_lamp"].value = lamp
        p["u_lamp_dir"].value = tuple(c / length for c in d)
        for buffers in (self.static, self.dynamic):
            for name, (vao, _vb, _ib) in buffers.items():
                colour, spec, emit = MATERIALS[name]
                p["u_color"].value = colour
                p["u_spec"].value = spec
                p["u_emit"].value = emit
                vao.render()
        sp = self.screen_program
        sp["u_mvp"].value = mvp
        sp["u_image"].value = 0
        for name, (vao, _vb) in self.quads.items():
            texture = self.textures.get(name)
            if texture is None:
                continue
            texture.use(0)
            sp["u_gain"].value = 1.0
            sp["u_round"].value = 0.0
            vao.render(mode=self.gl.TRIANGLE_STRIP)
        if "eye" in self.textures:
            self.textures["eye"].use(0)
            sp["u_gain"].value = 1.08
            sp["u_round"].value = 1.0
            self.eye[0].render()
        if target is not None:
            ctx.copy_framebuffer(screen_fb, target)
            screen_fb.use()
        ctx.viewport = (0, 0, w, h)

    def release(self) -> None:
        for buffers in (self.static, self.dynamic):
            for vao, vb, ib in buffers.values():
                vao.release(); vb.release(); ib.release()
        for vao, vb in self.quads.values():
            vao.release(); vb.release()
        for item in self.eye:
            item.release()
        for texture in self.textures.values():
            texture.release()
        if self.fbo is not None:
            self.fbo.release()
        self.program.release()
        self.screen_program.release()
