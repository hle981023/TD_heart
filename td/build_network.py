"""Builds the Guardian Heart operator network inside TouchDesigner.

Run this ONCE from a Textport (or a Text DAT's "Run Script"):

    exec(open(project.folder + '/td/build_network.py').read())

It creates `/guardian_heart` containing the full data pipeline
(webcam -> MediaPipe hands -> gesture engine -> null) plus a starter visual
scaffold (two artifacts, camera, light, render). The particle/material polish is
intentionally left for the GUI — see README "Tuning the visuals".

Safe to re-run: it deletes and rebuilds `/guardian_heart`.
"""


def _text_dat(container, name, source_relpath):
    """Create a Text DAT whose contents mirror a file under the project folder."""
    dat = container.create(textDAT, name)  # noqa: F821
    path = project.folder + "/" + source_relpath  # noqa: F821
    with open(path, "r", encoding="utf-8") as handle:
        dat.text = handle.read()
    return dat


def build():
    root = op("/")  # noqa: F821
    existing = root.op("guardian_heart")
    if existing:
        existing.destroy()

    gh = root.create(baseCOMP, "guardian_heart")  # noqa: F821

    # --- data pipeline ------------------------------------------------------
    videoin = gh.create(videodeviceinTOP, "videoin")  # noqa: F821
    try:
        videoin.par.resolutionw = 1280
        videoin.par.resolutionh = 720
    except Exception:
        pass  # parameter names vary by device; set in the GUI if needed.

    hands = gh.create(scriptCHOP, "hands")  # noqa: F821
    hands_cb = _text_dat(gh, "hand_source", "td/hand_source.py")
    hands.par.callbacks = hands_cb.name

    gesture = gh.create(scriptCHOP, "gesture")  # noqa: F821
    gesture_cb = _text_dat(gh, "gesture_engine", "td/gesture_engine.py")
    gesture.par.callbacks = gesture_cb.name
    gesture.inputConnectors[0].connect(hands)

    gesture_out = gh.create(nullCHOP, "gesture_out")  # noqa: F821
    gesture_out.inputConnectors[0].connect(gesture)
    gesture_out.par.cook = True  # keep the null cooking every frame

    # Mirror the preview horizontally so it reads like a reflection.
    preview = gh.create(flipTOP, "preview")  # noqa: F821
    preview.inputConnectors[0].connect(videoin)
    preview.par.flipx = True

    # --- visual scaffold (tune in the GUI) ----------------------------------
    # Two artifacts positioned from the gesture channels. Swap the placeholder
    # SOPs for imported GLBs (File In SOP) to match the web artifacts.
    egg = gh.create(geometryCOMP, "egg")  # noqa: F821
    egg_shape = egg.create(sphereSOP, "shape")  # noqa: F821
    egg_shape.par.rad = 0.5, 0.65, 0.5
    _bind_artifact(egg, "left")

    lock = gh.create(geometryCOMP, "lock")  # noqa: F821
    lock_shape = lock.create(torusSOP, "shape")  # noqa: F821
    _bind_artifact(lock, "right")

    material = gh.create(constantMAT, "artifact_mat")  # noqa: F821
    material.par.colorr, material.par.colorg, material.par.colorb = 1.0, 0.42, 0.68
    egg.par.material = material.name
    lock.par.material = material.name

    cam = gh.create(cameraCOMP, "cam")  # noqa: F821
    cam.par.tz = 6
    light = gh.create(lightCOMP, "key_light")  # noqa: F821
    light.par.tx, light.par.ty, light.par.tz = 3, 4, 6

    render = gh.create(renderTOP, "render")  # noqa: F821
    render.par.camera = cam.name
    render.par.alphabits = 8  # transparent so it can composite over `preview`

    over = gh.create(overTOP, "composite")  # noqa: F821
    over.inputConnectors[0].connect(render)
    over.inputConnectors[1].connect(preview)

    out = gh.create(outTOP, "out")  # noqa: F821
    out.inputConnectors[0].connect(over)

    gh.par.display = True
    gh.showCustomOnly = False
    print("guardian_heart built. Data pipeline: videoin -> hands -> gesture -> gesture_out")
    print("See README 'Tuning the visuals' to add heart particles and swap in GLB artifacts.")


def _bind_artifact(geo, side):
    """Drive a geometry COMP's screen position from the gesture null CHOP.

    Normalized x/y (0..1, top-left origin) map to a small world span; the artifact
    hides when its hand is absent.
    """
    ch = "op('gesture_out')"
    geo.par.tx.expr = f"({ch}['{side}_x'] - 0.5) * 6"
    geo.par.ty.expr = f"(0.5 - {ch}['{side}_y']) * 4"
    geo.par.scale.expr = f"0.6 if {ch}['{side}_valid'] > 0.5 else 0.0"
    # Continuous spin; faster reads well while fusing (see README for the ramp).
    geo.par.ry.expr = "me.time.seconds * 45"


build()
