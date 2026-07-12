"""Builds the Guardian Heart operator network inside TouchDesigner (OSC input).

MediaPipe runs OUTSIDE TD (runner/hand_runner.py) because TD's macOS Python
can't load pip-installed native extensions. This network receives the gesture
data over OSC, so it needs no Python packages — only the built-in OSC In CHOP.

Run ONCE from a Textport (Alt/Opt+T):

    exec(open(project.folder + '/td/build_network.py').read())

Creates `/guardian_heart` with:  oscin -> gesture_out (null) -> two artifacts.
Start runner/hand_runner.py first (or after — channels appear on first message).
Safe to re-run: it deletes and rebuilds `/guardian_heart`.
"""

OSC_PORT = 7000


def build():
    root = op("/")  # noqa: F821
    existing = root.op("guardian_heart")
    if existing:
        existing.destroy()

    gh = root.create(baseCOMP, "guardian_heart")  # noqa: F821

    # --- gesture data over OSC ----------------------------------------------
    oscin = gh.create(oscinCHOP, "oscin")  # noqa: F821
    oscin.par.port = OSC_PORT
    try:
        oscin.par.active = True
        oscin.par.bundated = False  # accept plain messages, not only bundles
    except Exception:
        pass  # parameter names vary slightly by TD version.

    gesture_out = gh.create(nullCHOP, "gesture_out")  # noqa: F821
    gesture_out.inputConnectors[0].connect(oscin)
    gesture_out.par.cook = True

    # --- visual scaffold (tune in the GUI) ----------------------------------
    # Swap the placeholder SOPs for File In SOPs loading the web GLB artifacts.
    egg = gh.create(geometryCOMP, "egg")  # noqa: F821
    egg_shape = egg.create(sphereSOP, "shape")  # noqa: F821
    egg_shape.par.rad = 0.5, 0.65, 0.5
    _bind_artifact(egg, "left")

    lock = gh.create(geometryCOMP, "lock")  # noqa: F821
    lock.create(torusSOP, "shape")  # noqa: F821
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

    out = gh.create(outTOP, "out")  # noqa: F821
    out.inputConnectors[0].connect(render)

    gh.par.display = True
    print(f"guardian_heart built. Listening for OSC on port {OSC_PORT}.")
    print("Start the sensor:  .venv/bin/python runner/hand_runner.py --preview")
    print("Then check guardian_heart/gesture_out — channels update as you move.")


def _bind_artifact(geo, side):
    """Drive a geometry COMP from the gesture null CHOP.

    Normalized x/y (0..1, top-left origin) map to a small world span; the artifact
    hides when its hand is absent. Channels appear once the runner sends OSC.
    """
    ch = "op('gesture_out')"
    geo.par.tx.expr = f"({ch}['{side}_x'] - 0.5) * 6"
    geo.par.ty.expr = f"(0.5 - {ch}['{side}_y']) * 4"
    geo.par.scale.expr = f"0.6 if {ch}['{side}_valid'] > 0.5 else 0.0"
    geo.par.ry.expr = "me.time.seconds * 45"


build()
