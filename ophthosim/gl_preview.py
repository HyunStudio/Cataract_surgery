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
from .picking3d import SurfaceHit, pick_anatomy

VERTEX_SHADER = """
#version 330
in vec3 in_position;
in vec3 in_normal;
uniform float u_yaw;
uniform float u_pitch;
uniform float u_aspect;
uniform float u_zoom;
out vec3 v_normal;
void main() {
    float cy = cos(u_yaw), sy = sin(u_yaw);
    float cp = cos(u_pitch), sp = sin(u_pitch);
    mat3 ry = mat3(cy, 0.0, -sy, 0.0, 1.0, 0.0, sy, 0.0, cy);
    mat3 rx = mat3(1.0, 0.0, 0.0, 0.0, cp, sp, 0.0, -sp, cp);
    mat3 rotation = rx * ry;
    vec3 p = rotation * in_position;
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


@dataclass(slots=True)
class View:
    yaw: float = .23
    pitch: float = .12
    zoom: float = 3.6
    phase: str = "CATARACT"

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

    def check(self) -> None:
        bounded_float(self.yaw, -1.2, 1.2)
        bounded_float(self.pitch, -.8, .8)
        bounded_float(self.zoom, 2.6, 5.0)
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
        "lens": all_meshes["lens" if phase == "CATARACT" else "iol"],
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
        self.selection: SurfaceHit | None = None
        self.selection_pixel: tuple[int, int] | None = None
        self.set_meshes(atlas_meshes("CATARACT"))

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

    def select(self, pos: tuple[int, int], view: View) -> SurfaceHit | None:
        """Anatomy inspection only. Mouse picks must not mutate surgery state."""
        view.check()
        w, h = self.pg.display.get_window_size()
        if len(pos) != 2:
            raise ValueError("Mouse position must contain two coordinates")
        self.selection = pick_anatomy(pos[0], pos[1], w, h,
                                      view.yaw, view.pitch, view.zoom, view.phase)
        self.selection_pixel = pos if self.selection is not None else None
        return self.selection

    def clear_selection(self) -> None:
        self.selection = None
        self.selection_pixel = None

    def render(self, view: View, fps: float, *, capture: bool = False) -> bytes | None:
        view.check()
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
        # The closed-globe placeholder would otherwise occlude the iris and
        # lens in depth testing. Paint it as a background that doesn't write
        # depth, then draw anterior structures with normal depth semantics.
        # A future scleral cutaway mesh should replace this atlas shortcut.
        self.ctx.depth_mask = False
        shader["u_tint"].value = self.TINTS["sclera"]
        shader["u_alpha"].value = 1.0
        self.meshes["sclera"][0].render()
        self.ctx.depth_mask = True
        for name in ("iris", "lens"):
            shader["u_tint"].value = self.TINTS[name]
            shader["u_alpha"].value = 1.0
            self.meshes[name][0].render()
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
        self.draw_hud(view, fps, w, h)
        # Optional readback must occur before swapping. CI uses Mesa software
        # GL; this cannot establish Windows GPU or display-driver correctness.
        image = self.ctx.screen.read(components=3, alignment=1) if capture else None
        self.pg.display.flip()
        return image

    def draw_hud(self, view: View, fps: float, w: int, h: int) -> None:
        hud = self.pg.Surface((w, h), self.pg.SRCALPHA)
        lines = (
            ("OPHTHOSIM-AI  /  HARDWARE 3D FEASIBILITY", self.font_big, (230, 241, 250)),
            ("EDUCATIONAL SYNTHETIC ANATOMY - NOT CLINICAL", self.font, (245, 202, 136)),
            (f"VIEW: {view.phase}    FPS: {fps:.0f} (measured locally)", self.font, (125, 211, 231)),
            ("ARROWS: ORBIT   +/-: ZOOM   SPACE: LENS/IOL   ESC: EXIT",
             self.font, (201, 223, 236)),
            ("LEFT CLICK: INSPECT IRIS / LENS (READ-ONLY DEPTH PICKING)",
             self.font, (245, 202, 136)),
            ((f"SELECTED: {self.selection.name.upper()}  DEPTH: {self.selection.distance:.2f}" 
              if self.selection is not None else "SELECTED: NONE"),
             self.font, (128, 221, 174)),
        )
        y = 24
        for text, font, color in lines:
            glyph = font.render(text, True, color)
            hud.blit(glyph, (20, y))
            y += 42 if font is self.font_big else 31
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
        for vao, vbo, ibo in self.meshes.values():
            vao.release()
            vbo.release()
            ibo.release()
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
