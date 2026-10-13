"""Experimental ModernGL GPU renderer for an educational, non-clinical eye atlas.

Run: pip install -r requirements-3d.txt
     python -m ophthosim.gl_preview

This is an independent technical feasibility prototype, not a 3D surgery
interaction mode. Importing this module requires NO pygame/OpenGL driver:
dependencies are loaded only when a window is requested.
"""
from __future__ import annotations

from array import array
import argparse
from dataclasses import dataclass
import json
import math
from typing import Iterable

from .geometry import Mesh, anterior_eye_meshes
from .mesh_raycast import TriangleHit, build_index, pick_indexed
from .tool3d import stylus_mesh
from .iol3d import foldable_iol_mesh
from .iol_pick3d import deformed_iol_mesh
from .capsule3d import capsule_indicator_meshes
from .vision3d import VisualFeedback
from .contact3d import ContactGuide, guide_ring_mesh

VERTEX_SHADER = """
#version 330
in vec3 in_position;
in vec3 in_normal;
uniform float u_yaw;
uniform float u_pitch;
uniform float u_aspect;
uniform float u_zoom;
uniform vec3 u_offset;
uniform float u_iol_mode;
uniform float u_iol_fold;
uniform vec2 u_scene_shift;
out vec3 v_normal;
void main() {
    float cy = cos(u_yaw), sy = sin(u_yaw);
    float cp = cos(u_pitch), sp = sin(u_pitch);
    mat3 ry = mat3(cy, 0.0, -sy, 0.0, 1.0, 0.0, sy, 0.0, cy);
    mat3 rx = mat3(1.0, 0.0, 0.0, 0.0, cp, sp, 0.0, -sp, cp);
    mat3 rotation = rx * ry;
    vec3 local_pos = in_position;
    // Synthetic fold/unfold effect only; not a deformable IOL material model.
    if (u_iol_mode > 0.5) {
        local_pos.x = mix(0.24 * in_position.x, in_position.x, u_iol_fold);
        local_pos.z += (1.0 - u_iol_fold) * 0.30 * abs(in_position.x);
    }
    vec3 p = rotation * (local_pos + u_offset);
    // View-only eye motion in camera plane. This is not tool or tissue physics.
    p.xy += u_scene_shift;
    v_normal = normalize(rotation * in_normal);
    float distance = u_zoom - p.z;
    const float near_plane = 0.5;
    const float far_plane = 16.0;
    float A = (far_plane + near_plane) / (far_plane - near_plane);
    float B = -2.0 * far_plane * near_plane / (far_plane - near_plane);
    gl_Position = vec4(p.x * 2.3 / u_aspect, p.y * 2.3,
                       A * distance + B, distance);
}
"""
FRAGMENT_SHADER = """
#version 330
in vec3 v_normal;
uniform vec3 u_tint;
uniform float u_alpha;
out vec4 fragColor;
void main() {
    vec3 light = normalize(vec3(-0.35, 0.45, 0.82));
    float diffuse = max(0.0, dot(normalize(v_normal), light));
    float level = 0.31 + 0.69 * diffuse;
    fragColor = vec4(u_tint * level, u_alpha);
}
"""
UI_VERTEX_SHADER = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""
UI_FRAGMENT_SHADER = """
#version 330
uniform sampler2D u_hud;
in vec2 v_uv;
out vec4 fragColor;
void main() {
    fragColor = texture(u_hud, v_uv);
}
"""


def bounded_float(value: object, lower: float, upper: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("A finite numeric value is required")
    try:
        v = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("A finite numeric value is required") from exc
    if not math.isfinite(v) or not lower <= v <= upper:
        raise ValueError("Value out of renderer bounds")
    return v


def pack_mesh(mesh: Mesh) -> tuple[bytes, bytes, int]:
    """Interleave position/normal float32 and triangle uint32 for ModernGL."""
    mesh.validate()
    if len(mesh.vertices) > 100_000 or len(mesh.faces) > 200_000:
        raise ValueError("Mesh exceeds rendering budget")
    vertex_data = array("f")
    indices = array("I")
    for point, normal in zip(mesh.vertices, mesh.normals):
        vertex_data.extend((*point, *normal))
    for face in mesh.faces:
        indices.extend(face)
    if len(vertex_data) != 6 * len(mesh.vertices):
        raise ValueError("Unexpected mesh packing length")
    return vertex_data.tobytes(), indices.tobytes(), len(indices)


@dataclass(frozen=True, slots=True)
class AnatomyAppearance:
    """Renderer-facing synthetic state, not anatomical/clinical measurement."""
    opacity: float = 1.0
    cortex: float = 1.0
    iol_alignment: float = 1.0
    iol_deployment: float = 1.0
    capsule_damage: float = 0.0
    capsule_present: bool = False

    def check(self) -> None:
        bounded_float(self.opacity, 0., 1.)
        bounded_float(self.cortex, 0., 1.)
        bounded_float(self.iol_alignment, 0., 1.)
        bounded_float(self.iol_deployment, 0., 1.)
        bounded_float(self.capsule_damage, 0., 1.)
        if type(self.capsule_present) is not bool:
            raise ValueError("Capsule visual flag must be a boolean")


@dataclass(slots=True)
class View:
    yaw: float = .23
    pitch: float = .12
    zoom: float = 3.6
    phase: str = "CATARACT"
    iol_deployment: float = 1.0

    def key(self, key: str) -> None:
        """Deterministic camera and state changes; no surgical consequences."""
        if key == "left":
            self.yaw = max(-1.2, self.yaw - .08)
        elif key == "right":
            self.yaw = min(1.2, self.yaw + .08)
        elif key == "up":
            self.pitch = min(.8, self.pitch + .08)
        elif key == "down":
            self.pitch = max(-.8, self.pitch - .08)
        elif key == "zoom_in":
            self.zoom = max(2.6, self.zoom - .12)
        elif key == "zoom_out":
            self.zoom = min(5.0, self.zoom + .12)
        elif key == "toggle":
            self.phase = "IOL" if self.phase == "CATARACT" else "CATARACT"
        elif key == "fold":
            # Standalone educational atlas: static three-position display.
            self.iol_deployment = ({1.0: 0.0, 0.0: .5, .5: 1.0}
                                   .get(self.iol_deployment, 1.0))

    def check(self) -> None:
        bounded_float(self.yaw, -1.2, 1.2)
        bounded_float(self.pitch, -.8, .8)
        bounded_float(self.zoom, 2.6, 5.0)
        bounded_float(self.iol_deployment, 0., 1.)
        if self.phase not in {"CATARACT", "IOL"}:
            raise ValueError("Invalid atlas state")


def atlas_meshes(phase: str) -> dict[str, Mesh]:
    """Select a non-clinical optical model for the GPU demo."""
    if phase not in {"CATARACT", "IOL"}:
        raise ValueError("Invalid atlas phase")
    all_meshes = anterior_eye_meshes()
    return {
        "sclera": all_meshes["sclera"],
        "iris": all_meshes["iris"],
        "lens": all_meshes["lens"] if phase == "CATARACT" else foldable_iol_mesh(),
        "cornea": all_meshes["cornea"],
    }


def offline_check() -> dict[str, object]:
    """Reproducible geometry pack smoke test, no GL context required."""
    meshes = atlas_meshes("CATARACT")
    report = {}
    for name, mesh in meshes.items():
        vb, ib, count = pack_mesh(mesh)
        report[name] = {
            "vertices": len(mesh.vertices), "triangles": count // 3,
            "vertex_bytes": len(vb), "index_bytes": len(ib),
        }
    return {"status": "cpu-geometry-ok", "gpu_tested": False, "meshes": report}


class GPUEyePreview:
    """Single Pygame-owned OpenGL context; ModernGL owns all GL rendering."""

    TINTS = {
        "sclera": (.57, .69, .75),
        "iris": (.12, .48, .52),
        "lens": (.83, .76, .60),
        "cornea": (.66, .87, .96),
    }

    def __init__(self, pygame, moderngl, size=(1280, 720)):
        self.pg = pygame
        self.gl = moderngl
        self.size = size
        # One OpenGL window; do not software-blit into an OPENGL display.
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK,
                                        pygame.GL_CONTEXT_PROFILE_CORE)
        self.window = pygame.display.set_mode(size, pygame.OPENGL | pygame.DOUBLEBUF |
                                              pygame.RESIZABLE)
        pygame.display.set_caption("OphthoSim-AI | Experimental 3D GPU Atlas")
        self.ctx = moderngl.create_context(require=330)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.CULL_FACE)
        self.scene_shader = self.ctx.program(vertex_shader=VERTEX_SHADER,
                                             fragment_shader=FRAGMENT_SHADER)
        self.hud_shader = self.ctx.program(vertex_shader=UI_VERTEX_SHADER,
                                           fragment_shader=UI_FRAGMENT_SHADER)
        quad = array("f", (-1, -1, 0, 0,
                            1, -1, 1, 0,
                           -1,  1, 0, 1,
                            1,  1, 1, 1))
        self.quad_buffer = self.ctx.buffer(quad.tobytes())
        self.quad_vao = self.ctx.vertex_array(self.hud_shader,
                               [(self.quad_buffer, "2f 2f", "in_pos", "in_uv")])
        self.font = pygame.font.SysFont("segoeui", 20)
        self.font_big = pygame.font.SysFont("segoeui", 28, bold=True)
        self.hud_texture = None
        self.meshes: dict[str, tuple[object, object, object]] = {}
        self.selection: TriangleHit | None = None
        self.selection_pixel: tuple[int, int] | None = None
        self.set_meshes(atlas_meshes("CATARACT"))
        ring_vertices, ring_indices, _ = pack_mesh(guide_ring_mesh())
        self.contact_vbo = self.ctx.buffer(ring_vertices)
        self.contact_ibo = self.ctx.buffer(ring_indices)
        self.contact_vao = self.ctx.vertex_array(self.scene_shader,
                [(self.contact_vbo, "3f 3f", "in_position", "in_normal")],
                index_buffer=self.contact_ibo)
        # Both state-independent cosmetic meshes live for the GL context.
        # Never allocate a mesh every frame during an alert.
        self.capsule_buffers = {}
        for key, mesh in capsule_indicator_meshes().items():
            vertex_bytes, index_bytes, _ = pack_mesh(mesh)
            vb = self.ctx.buffer(vertex_bytes)
            ib = self.ctx.buffer(index_bytes)
            vao = self.ctx.vertex_array(self.scene_shader,
                     [(vb, "3f 3f", "in_position", "in_normal")],
                     index_buffer=ib)
            self.capsule_buffers[key] = (vao, vb, ib)
        # Allocate one stylized 3D tool; motion uses a shader uniform only.
        tool_vertices, tool_indices, _ = pack_mesh(stylus_mesh())
        self.stylus_vbo = self.ctx.buffer(tool_vertices)
        self.stylus_ibo = self.ctx.buffer(tool_indices)
        self.stylus_vao = self.ctx.vertex_array(self.scene_shader,
                 [(self.stylus_vbo, "3f 3f", "in_position", "in_normal")],
                 index_buffer=self.stylus_ibo)

    def set_meshes(self, meshes: dict[str, Mesh]) -> None:
        for vao, vbo, ibo in self.meshes.values():
            vao.release()
            vbo.release()
            ibo.release()
        self.meshes.clear()
        for name, mesh in meshes.items():
            vertex_bytes, index_bytes, _ = pack_mesh(mesh)
            vbo = self.ctx.buffer(vertex_bytes)
            ibo = self.ctx.buffer(index_bytes)
            vao = self.ctx.vertex_array(self.scene_shader,
                            [(vbo, "3f 3f", "in_position", "in_normal")],
                            index_buffer=ibo)
            self.meshes[name] = vao, vbo, ibo
        # Static triangle BVHs are built only when scene meshes change,
        # never on each pointer event or 60-Hz render cycle.
        self.mesh_indexes = {name:build_index(meshes[name])
                             for name in ("iris", "lens")}
        self._dynamic_iol_signature = None
        self._dynamic_iol_index = None

    def select(self, pos: tuple[int, int], view: View, *,
               appearance: AnatomyAppearance | None = None,
               vision: VisualFeedback | None = None) -> TriangleHit | None:
        """Pick the SAME synthetic positions as the displayed deforming IOL.

        This is a visual inspection feature, not the surgery task's collision
        or force authority. Only iris and IOL/cataract triangles are inspected;
        corneal transparency and depth-buffer culling are not reproduced.
        """
        view.check()
        if appearance is not None:
            if not isinstance(appearance, AnatomyAppearance):
                raise ValueError("Invalid visual appearance")
            appearance.check()
        if vision is not None:
            if not isinstance(vision, VisualFeedback):
                raise ValueError("Invalid visual feedback")
            vision.check()
        if not isinstance(pos,(tuple,list)) or len(pos)!=2:
            raise ValueError("Mouse position must contain two coordinates")
        w, h = self.pg.display.get_window_size()
        indexes=self.mesh_indexes
        if view.phase=="IOL":
            deployment=(appearance.iol_deployment if appearance is not None
                        else view.iol_deployment)
            alignment=(appearance.iol_alignment if appearance is not None
                       else 1.0)
            signature=(deployment,alignment)
            if self._dynamic_iol_signature!=signature:
                deformed=deformed_iol_mesh(deployment,alignment)
                new_index=build_index(deformed)
                self._dynamic_iol_index=new_index
                self._dynamic_iol_signature=signature
            indexes={"iris":self.mesh_indexes["iris"],
                     "lens":self._dynamic_iol_index}
        shift=((vision.motion_x,vision.motion_y) if vision is not None
               else (0.,0.))
        self.selection=pick_indexed(indexes,pos[0],pos[1],w,h,
                        view.yaw,view.pitch,view.zoom,view.phase,
                        scene_shift=shift)
        self.selection_pixel=tuple(pos) if self.selection is not None else None
        return self.selection

    def clear_selection(self) -> None:
        self.selection = None
        self.selection_pixel = None

    def render(self, view: View, fps: float, *, capture: bool = False,
               overlay=None, appearance: AnatomyAppearance | None = None,
               tool_pose: tuple[float, float, float] | None = None,
               vision: VisualFeedback | None = None,
               contact: ContactGuide | None = None) -> bytes | None:
        view.check()
        if appearance is not None:
            appearance.check()
        if vision is not None:
            if not isinstance(vision, VisualFeedback):
                raise ValueError("Invalid visual feedback object")
            vision.check()
        if contact is not None:
            if not isinstance(contact, ContactGuide):
                raise ValueError("Invalid contact preview")
            contact.check()
        if tool_pose is not None:
            if not isinstance(tool_pose, (tuple, list)) or len(tool_pose) != 3:
                raise ValueError("Tool position must have three coordinates")
            tool_pose = tuple(bounded_float(component, -1., 1.)
                              for component in tool_pose)
        w, h = self.pg.display.get_window_size()
        if not (w > 0 and h > 0):
            return None
        self.size = (w, h)
        self.ctx.viewport = (0, 0, w, h)
        self.ctx.clear(.026, .065, .105, 1.0, depth=1.0)
        self.ctx.enable(self.gl.DEPTH_TEST)
        self.ctx.enable(self.gl.CULL_FACE)
        shader = self.scene_shader
        shader["u_yaw"].value = view.yaw
        shader["u_pitch"].value = view.pitch
        shader["u_zoom"].value = view.zoom
        shader["u_aspect"].value = w / h
        shader["u_offset"].value = (0., 0., 0.)
        shader["u_iol_mode"].value = 0.0
        shader["u_iol_fold"].value = 1.0
        shader["u_scene_shift"].value = ((vision.motion_x, vision.motion_y)
                                          if vision is not None else (0.,0.))
        # The closed sclera is only a non-clinical *background globe*. Its
        # front-facing shell would physically occlude the iris and the lens.
        # Disable the depth TEST (not just the depth write-mask), which
        # guarantees it cannot populate the depth buffer. Re-enable both
        # tests and normal culling for the actual iris/lens scene.
        # An anterior globe cutaway would replace this shortcut later.
        self.ctx.disable(self.gl.DEPTH_TEST)
        shader["u_tint"].value = self.TINTS["sclera"]
        shader["u_alpha"].value = 1.0
        self.meshes["sclera"][0].render()
        self.ctx.enable(self.gl.DEPTH_TEST)
        for name in ("iris", "lens"):
            # Actual 3D geometry is deliberately simple: appearance changes
            # communicate *simulated* progress, not biological tissue effects.
            color = self.TINTS[name]
            offset = (0., 0., 0.)
            if name == "lens" and appearance is not None:
                if view.phase == "IOL":
                    displacement = .18 * (1. - appearance.iol_alignment)
                    offset = (displacement, 0., 0.)
                else:
                    opacity = appearance.opacity
                    residual = appearance.cortex
                    if opacity <= .001 and residual <= .001:
                        continue
                    color = (.22 + .61 * opacity,
                             .42 + .34 * opacity,
                             .50 + .10 * opacity)
            shader["u_offset"].value = offset
            shader["u_iol_mode"].value = (1.0 if name == "lens" and view.phase == "IOL" else 0.0)
            shader["u_iol_fold"].value = (appearance.iol_deployment if appearance is not None else view.iol_deployment)
            shader["u_tint"].value = color
            shader["u_alpha"].value = 1.0
            self.meshes[name][0].render()
        shader["u_offset"].value = (0., 0., 0.)
        shader["u_iol_mode"].value = 0.0
        shader["u_iol_fold"].value = 1.0
        if appearance is not None and appearance.capsule_present:
            # A cosmetic visual warning in front of the pupil, not a mesh
            # collision or physically positioned human lens capsule.
            damage = appearance.capsule_damage
            key = "damaged" if damage >= .15 else "intact"
            shader["u_tint"].value = ((.99, .24, .28) if key == "damaged"
                                      else (.22, .82, .72))
            shader["u_alpha"].value = 1.0
            self.capsule_buffers[key][0].render()
        self.ctx.enable(self.gl.BLEND)
        self.ctx.blend_func = self.gl.SRC_ALPHA, self.gl.ONE_MINUS_SRC_ALPHA
        self.ctx.disable(self.gl.CULL_FACE)
        self.ctx.depth_mask = False
        shader["u_tint"].value = self.TINTS["cornea"]
        shader["u_alpha"].value = .24
        self.meshes["cornea"][0].render()
        self.ctx.depth_mask = True
        self.ctx.disable(self.gl.BLEND)
        self.ctx.enable(self.gl.CULL_FACE)
        if tool_pose is not None:
            # Deliberately draw this NON-COLLIDING educational pointer on top
            # of transparent anatomy. Without this overlay pass, its narrow
            # end cap can be hidden by depth/culling in the microscope view.
            # The shader still projects its actual world-space tip position.
            # This display override is not a physically accurate occlusion.
            self.ctx.disable(self.gl.DEPTH_TEST)
            self.ctx.disable(self.gl.CULL_FACE)
            shader["u_scene_shift"].value = (0.,0.)
            shader["u_offset"].value = tool_pose
            shader["u_tint"].value = (.43, .95, .80)
            shader["u_alpha"].value = 1.0
            self.stylus_vao.render()
            shader["u_offset"].value = (0., 0., 0.)
            self.ctx.enable(self.gl.CULL_FACE)
            self.ctx.enable(self.gl.DEPTH_TEST)
        if contact is not None and contact.location is not None:
            # Read-only educational target ring. Painted as a world-positioned
            # overlay, with no physical depth collision or tissue effects.
            shader["u_scene_shift"].value = (0.,0.)
            shader["u_offset"].value = contact.location
            shader["u_iol_mode"].value = 0.0
            shader["u_iol_fold"].value = 1.0
            shader["u_tint"].value = ((.30,.95,.62) if contact.status == "TARGET"
                                      else (.32,.69,.91) if contact.status == "VISITED"
                                      else (.98,.69,.26))
            shader["u_alpha"].value = 1.0
            self.ctx.disable(self.gl.DEPTH_TEST)
            self.ctx.disable(self.gl.CULL_FACE)
            self.contact_vao.render()
            self.ctx.enable(self.gl.CULL_FACE)
            self.ctx.enable(self.gl.DEPTH_TEST)
            shader["u_offset"].value = (0.,0.,0.)
        self.draw_hud(view, fps, w, h, overlay=overlay, vision=vision)
        # Optional readback must occur before swapping. CI uses Mesa software
        # GL; this cannot establish Windows GPU or display-driver correctness.
        image = self.ctx.screen.read(components=3, alignment=1) if capture else None
        self.pg.display.flip()
        return image

    def draw_hud(self, view: View, fps: float, w: int, h: int,
                 *, overlay=None, vision: VisualFeedback | None = None) -> None:
        hud = self.pg.Surface((w, h), self.pg.SRCALPHA)
        if vision is not None:
            # Frosted synthetic view veil; static and bounded, never blinking.
            # This HUD-layer approximation does NOT reproduce tissue optics.
            if vision.haze > 0.:
                center=(w//2,h//2)
                radius=max(1,min(w,h)//3)
                for fraction,alpha_fraction in ((1.,.20),(.82,.31),(.65,.35)):
                    alpha=min(130,round(255*vision.haze*alpha_fraction))
                    self.pg.draw.circle(hud,(208,220,220,alpha),center,
                                        round(radius*fraction))
            if vision.high_contrast:
                self.pg.draw.circle(hud,(245,236,146,235),(w//2,h//2),
                                    max(1,min(w,h)//3)+5,3)
        if overlay is None:
            lines = (
                ("OPHTHOSIM-AI  /  HARDWARE 3D FEASIBILITY", self.font_big, (230, 241, 250)),
                ("EDUCATIONAL SYNTHETIC ANATOMY - NOT CLINICAL", self.font, (245, 202, 136)),
                (f"VIEW: {view.phase}    FOLD: {view.iol_deployment:.0%}    FPS: {fps:.0f}", self.font, (125, 211, 231)),
                ("ARROWS: ORBIT   +/-: ZOOM   SPACE: LENS/IOL   F: FOLD   ESC: EXIT",
                 self.font, (201, 223, 236)),
                ("LEFT CLICK: INSPECT IRIS / LENS (READ-ONLY DEPTH PICKING)",
                 self.font, (245, 202, 136)),
                ((f"MESH FACE: {self.selection.face_index} | {self.selection.name.upper()} | RAY: {self.selection.distance:.2f}"
                  if self.selection is not None else "SELECTED: NONE"),
                 self.font, (128, 221, 174)),
            )
        else:
            lines = (
                ("OPHTHOSIM-AI  /  INTERACTIVE 3D PROTOTYPE", self.font_big, (230, 241, 250)),
                ("SYNTHETIC EDUCATIONAL SURGERY - NOT CLINICAL TRAINING", self.font,
                 (245, 202, 136)),
                (f"ANATOMY: {view.phase}    FPS: {fps:.0f} (measured locally)", self.font,
                 (125, 211, 231)),
            )
        y = 24
        for text, font, color in lines:
            glyph = font.render(text, True, color)
            hud.blit(glyph, (20, y))
            y += 42 if font is self.font_big else 31
        if overlay is not None:
            # The integration overlay observes a simulation snapshot and
            # paints into this one shared GPU-uploaded Pygame HUD texture.
            overlay.draw(self.pg, hud, view, w, h, self.font, self.font_big)
        if self.selection_pixel is not None:
            px, py = self.selection_pixel
            self.pg.draw.circle(hud, (110, 230, 195), (px, py), 12, 2)
            self.pg.draw.line(hud, (110, 230, 195), (px-18,py), (px-5,py), 2)
            self.pg.draw.line(hud, (110, 230, 195), (px+5,py), (px+18,py), 2)
        # Upload one RGBA HUD texture and draw it using the very same GL
        # context. Avoid creating extra Pygame display surfaces.
        if self.hud_texture is None or self.hud_texture.size != (w, h):
            if self.hud_texture is not None:
                self.hud_texture.release()
            self.hud_texture = self.ctx.texture((w, h), 4)
            self.hud_texture.filter = (self.gl.LINEAR, self.gl.LINEAR)
        self.hud_texture.write(self.pg.image.tobytes(hud, "RGBA", True))
        self.hud_texture.use(0)
        self.hud_shader["u_hud"].value = 0
        self.ctx.disable(self.gl.DEPTH_TEST)
        self.ctx.enable(self.gl.BLEND)
        self.ctx.blend_func = self.gl.SRC_ALPHA, self.gl.ONE_MINUS_SRC_ALPHA
        self.quad_vao.render(mode=self.gl.TRIANGLE_STRIP)
        self.ctx.disable(self.gl.BLEND)
        self.ctx.enable(self.gl.DEPTH_TEST)

    def close(self) -> None:
        self.contact_vao.release()
        self.contact_vbo.release()
        self.contact_ibo.release()
        for vao, vbo, ibo in self.capsule_buffers.values():
            vao.release()
            vbo.release()
            ibo.release()
        for vao, vbo, ibo in self.meshes.values():
            vao.release()
            vbo.release()
            ibo.release()
        self.stylus_vao.release()
        self.stylus_vbo.release()
        self.stylus_ibo.release()
        self.quad_vao.release()
        self.quad_buffer.release()
        if self.hud_texture is not None:
            self.hud_texture.release()
        self.scene_shader.release()
        self.hud_shader.release()


def run() -> None:
    try:
        import pygame
        import moderngl
    except ImportError as exc:
        raise SystemExit("Install optional 3D requirements: pip install -r requirements-3d.txt") from exc
    pygame.init()
    atlas = None
    try:
        atlas = GPUEyePreview(pygame, moderngl)
        view = View()
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_LEFT:
                        view.key("left")
                        atlas.clear_selection()
                    elif event.key == pygame.K_RIGHT:
                        view.key("right")
                        atlas.clear_selection()
                    elif event.key == pygame.K_UP:
                        view.key("up")
                        atlas.clear_selection()
                    elif event.key == pygame.K_DOWN:
                        view.key("down")
                        atlas.clear_selection()
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        view.key("zoom_in")
                        atlas.clear_selection()
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        view.key("zoom_out")
                        atlas.clear_selection()
                    elif event.key == pygame.K_SPACE:
                        view.key("toggle")
                        atlas.set_meshes(atlas_meshes(view.phase))
                        atlas.clear_selection()
                    elif event.key == pygame.K_f and view.phase == "IOL":
                        view.key("fold")
                        atlas.clear_selection()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    atlas.select(event.pos, view)
                elif event.type == pygame.VIDEORESIZE:
                    atlas.clear_selection()
            clock.tick(60)
            atlas.render(view, clock.get_fps())
    finally:
        if atlas is not None:
            atlas.close()
        pygame.quit()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experimental ModernGL cataract atlas")
    parser.add_argument("--check", action="store_true",
                        help="CPU-only geometry validation; does not test the GPU")
    args = parser.parse_args(argv)
    if args.check:
        print(json.dumps(offline_check(), indent=2, sort_keys=True))
    else:
        run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
