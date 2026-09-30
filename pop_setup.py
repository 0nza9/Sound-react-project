"""TouchDesigner setup for the POP particle chain.

Run audio_setup first (null1 / speed1 must exist), then run this the same way.
Parameters are set by on-screen label; anything that can't be applied is printed.
"""

PARENT_PATH = '/project1'
FEEDBACK_TOX = 'f:/touchdesigner code/feedback.tox'
BLOOM_TOX = 'f:/touchdesigner code/bloom.tox'

# Audio -> visual mappings, rewritten by save_settings.py
MAP_LOW = "op('speed1')['mid']*0.5"
MAP_FMSD = "op('speed1')['fmsd']"
MAP_SNARE = "op('null1')['snare']*0.5"


def E(text):
    return ('expr', text)


def _set(par, value):
    if isinstance(value, tuple) and len(value) == 2 and value[0] == 'expr':
        par.expr = value[1]
        return
    if isinstance(value, (tuple, list)):
        for p, v in zip(par.tuplet, value):
            p.val = v
        return
    if par.isMenu and isinstance(value, str):
        labels = list(par.menuLabels)
        lowered = [m.lower() for m in labels]
        wanted = value.lower()
        if wanted in lowered:
            par.menuIndex = lowered.index(wanted)
            return
    par.val = value


def apply(node, settings, pars=None):
    by_label = {}
    for p in (pars if pars is not None else node.pars()):
        by_label.setdefault(p.label, p)
    missing = []
    for label, value in settings.items():
        par = by_label.get(label)
        if par is None:
            missing.append(label)
            continue
        try:
            _set(par, value)
        except Exception as e:
            missing.append(f'{label} ({e})')
    if missing:
        print(f'{node.name}: not applied ->', missing)


def sequence(node, key, blocks):
    seq = getattr(node.seq, key, None)
    if seq is None:
        for s in node.seq:
            if s.name.lower() == key.lower():
                seq = s
                break
    if seq is None:
        names = [s.name for s in node.seq]
        print(f'{node.name}: sequence "{key}" not found, available ->', names)
        return
    seq.numBlocks = len(blocks)
    for i, settings in enumerate(blocks):
        apply(node, settings, pars=list(seq[i].par))


def make(parent, optype, name):
    return parent.op(name) or parent.create(optype, name)


def wire(node, *sources):
    for i, src in enumerate(sources):
        try:
            node.inputConnectors[i].connect(src)
        except Exception:
            try:
                node.inputConnectors[i].connect(src.outputConnectors[0])
            except Exception as e:
                print(f'{node.name}: could not connect input {i} ->', e)


def build():
    parent = op(PARENT_PATH)
    for needed in ('null1', 'speed1', 'null2'):
        if parent.op(needed) is None:
            print(f'warning: {needed} not found, run audio_setup first')

    keyboard = make(parent, 'keyboardinCHOP', 'keyboardin1')
    apply(keyboard, {
        'Active': 1, 'Keys': '1', 'Modifier Keys': 'Ignore',
        'Channel Names': 'by Key Name', 'Sample Rate': 60,
    })

    chopto = make(parent, 'choptoPOP', 'chopto1')
    apply(chopto, {
        'CHOP': 'null2', 'Connectivity': 'Point Primitives',
        'Specify Position': 1, 'Start Position': (-1, 0, 0), 'End Position': (1, 0, 0),
        'Closed': 0, 'Channels Selection': 'Specify Channels',
        'Channel Scope': '*', 'Attribute Scope': 'P(0) P(1)',
    })

    particle = make(parent, 'particlePOP', 'particle1')
    wire(particle, chopto)
    apply(particle, {
        'Create Point Primitives': 1, 'Point Id Reuse': 'Reuse Point Ids in Loop',
        'Maximum Particles': 5000, 'Emission from': 'Birth Rate', 'Birth Rate': 100,
        'Randomize Input Points': 1, 'Life Expect': 10, 'Life Variance (Fraction)': 0,
        'Random Seed': 0, 'Enable Time Integration': 1, 'Jitter Births During Frame': 0,
        'Jitter Birth Position': 0, 'Initial Velocity': (0, 0, 0), 'Initial Mass': 1,
        'Initial Drag': 0, 'Velocity Damping': 0, 'Play': 1, 'Speed': 1, 'Pre-Roll': 0,
    })

    rnd = make(parent, 'randomPOP', 'random1')
    wire(rnd, particle)
    apply(rnd, {
        'Extra Points per Source Point': 0, 'Type': 'Uniform', 'Random Size': 3,
        'Seed': 6.57, 'Parameter Size': 1, 'Exponent': 1,
        'Value A': -0.001, 'Value B': 0.001, 'Clamp Value': 0,
        'Combine Operation': 'Set', 'Output Attribute Scope': 'vel',
        'Override Automatic Attribute': 1, 'Attribute Type': 'float', 'Components': 3,
        'Attribute Class': 'Point', 'Compute Point Normals': 0,
    })

    null3 = make(parent, 'nullPOP', 'null3')
    wire(null3, rnd)

    feedback = make(parent, 'feedbackPOP', 'feedback1')
    wire(feedback, null3)
    apply(feedback, {
        'Start': E("op('keyboardin1')['k1']"), 'Play': 1, 'Pre-Roll': 0,
        'Use Memory Limit': 1, 'Input Multiplier': 100,
    })
    merge = make(parent, 'mergePOP', 'merge1')
    wire(merge, feedback, null3)
    apply(merge, {'Unique Group Name': 0, 'Entity': 'Points'})

    mm1 = make(parent, 'mathmixPOP', 'mathmix1')
    wire(mm1, merge)
    apply(mm1, {'Attribute Class': 'Point', 'Angle Units': 'Degrees'})
    sequence(mm1, 'comb', [
        {'Operation': 'A + B', 'Scope A': 'P', 'Scope B': 'vel', 'Result Scope': 'P'},
    ])

    mm2 = make(parent, 'mathmixPOP', 'mathmix2')
    wire(mm2, mm1)
    apply(mm2, {'Attribute Class': 'Point', 'Angle Units': 'Degrees'})
    sequence(mm2, 'vec', [{'Name': 'origin', 'Type': 'float3', 'Value': (0, 0, 0)}])
    sequence(mm2, 'comb', [
        {'Operation': 'A - B', 'Scope A': 'origin', 'Scope B': 'P', 'Result Scope': 'len'},
        {'Operation': 'length(A)', 'Scope A': 'len', 'Result Scope': 'len'},
    ])

    noise2 = make(parent, 'noisePOP', 'noise2')
    wire(noise2, mm2)
    apply(noise2, {
        'Noise Lookup Attribute': 'P', 'Type': 'Simplex 4D (GPU)', 'Noise Size': 3,
        'Seed': 1, 'Period': 1, 'Harmonics': 2, 'Harmonic Spread': 2, 'Harmonic Gain': 0.7,
        'Parameter Size': 1, 'Amplitude': 0.1, 'Exponent': 1, 'Offset': 0,
        'Positive Only': 0, 'Attribute Class': 'Point',
        'Translate 4D': E(MAP_LOW),
        'Combine Operation': 'Add', 'Combine Attribute Scope': 'P', 'Mode': 'Performance',
    })

    noise1 = make(parent, 'noisePOP', 'noise1')
    wire(noise1, noise2)
    apply(noise1, {
        'Noise Lookup Attribute': 'P', 'Type': 'Simplex 4D (GPU)', 'Noise Size': 3,
        'Seed': 1.83, 'Period': 0.81, 'Harmonics': 3, 'Harmonic Spread': 9,
        'Harmonic Gain': 0.365, 'Parameter Size': 1, 'Amplitude': 0.205, 'Exponent': 1.49,
        'Offset': 0, 'Positive Only': 0, 'Attribute Class': 'Point',
        'Translate 4D': E(MAP_FMSD),
        'Combine Operation': 'Add', 'Combine Attribute Scope': 'P', 'Mode': 'Performance',
    })

    math1 = make(parent, 'mathPOP', 'math1')
    wire(math1, noise2)
    apply(math1, {
        'Attribute Class': 'Point', 'Input Attribute Scope': 'len', 'Angle Units': 'Degrees',
        'Parameter Size': 1, 'Multiply': E(MAP_SNARE),
        'Output Attribute Scope': 'c',
    })

    mm3 = make(parent, 'mathmixPOP', 'mathmix3')
    wire(mm3, math1, noise1)
    apply(mm3, {'Attribute Class': 'Point', 'Angle Units': 'Degrees'})
    sequence(mm3, 'comb', [
        {'Operation': 'mix(A, B, C)', 'Scope A': 'P', 'Scope B': 'in1_P', 'Scope C': 'c',
         'Result Scope': 'P'},
    ])

    twist = make(parent, 'twistPOP', 'twist1')
    wire(twist, mm3)
    apply(twist, {
        'Attribute Class': 'Point', 'Input Attribute Scope': 'P',
        'Operation': 'Twist', 'Primary Axis': 'Y Axis', 'Pivot': (0, 0, 0),
        'Strength': 224, 'Rolloff': 0.95,
    })

    delete = make(parent, 'deletePOP', 'delete1')
    wire(delete, twist)
    apply(delete, {
        'Operation': 'Delete Selected', 'Entity': 'Points',
        'Line Strip Behavior': 'Delete Point of Line Strip',
        'Copy Topology Info Back to CPU': 0,
    })
    sequence(delete, 'attr', [
        {'Attribute': 'len(0)', 'Function': '>', 'Value': 3, 'Invert': 0},
    ])

    endfeedback = make(parent, 'nullPOP', 'endfeedback')
    wire(endfeedback, delete)
    apply(feedback, {'Target Feedback Loop POP': 'endfeedback'})

    return build_render(parent, endfeedback)


def build_render(parent, points_in):
    sprite = make(parent, 'pointspriteMAT', 'pointsprite1')
    apply(sprite, {
        'Color': (0.4208, 0.587, 0.8), 'Alpha': 1,
        'Point Scale Attribute': 'PointScale', 'Constant Point Size': 1,
        'Sizing Model': 'Constant/Attenuate', 'Attenuate Point Scale': 0,
    })

    geo = make(parent, 'geometryCOMP', 'geo1')
    torus = geo.op('torus1')
    if torus is not None:
        torus.destroy()
    in_pop = geo.op('in1')
    if in_pop is None:
        try:
            in_pop = geo.create('inPOP', 'in1')
        except Exception as e:
            print('geo1: could not create in1 ->', e)
    if in_pop is not None:
        in_pop.render = True
        in_pop.display = True
    wire(geo, points_in)
    apply(geo, {'Material': 'pointsprite1', 'Render': 1})

    light = make(parent, 'lightCOMP', 'light1')
    apply(light, {
        'Translate': (0, 0, 10), 'Light Color': (1, 1, 1), 'Dimmer': 1,
        'Light Type': 'Point Light', 'Distance-Attenuated': 0,
    })

    cam = make(parent, 'cameraCOMP', 'cam1')
    apply(cam, {
        'Translate': (0, 0, 5), 'Projection': 'Perspective',
        'Viewing Angle Method': 'Horizontal FOV', 'FOV Angle': 45,
        'Near': 0.1, 'Far': 1000,
    })

    render = make(parent, 'renderTOP', 'render1')
    apply(render, {
        'Camera(s)': 'cam1', 'Geometry': '*', 'Lights': '*', 'Anti-Alias': '4x',
        'Background Color': (0, 0, 0), 'Render Mode': '2D',
        'Transparency': 'Sorted Draw with Blending',
        'Resolution': (1280, 720), 'Pixel Format': '32-bit float (RGBA)',
    })

    return build_post(parent, render)


def find_palette_tox(name, fallback=''):
    """Locate a stock Palette component inside the TouchDesigner install."""
    import glob
    import os

    roots = []
    try:
        roots.append(os.path.join(app.installFolder, 'Samples', 'Palette'))
        roots.append(app.installFolder)
    except Exception:
        pass

    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        hits = glob.glob(os.path.join(root, '**', name + '.tox'), recursive=True)
        if hits:
            return hits[0]
    return fallback


def load_tox(parent, name, path):
    """Load a Palette component, unwrapping the help/icon package it ships in."""
    comp = parent.op(name)
    if comp is not None:
        return comp

    found = find_palette_tox(name, path)
    if not found:
        raise RuntimeError(name + ' not found in the Palette; set its _TOX path')
    print(name, 'loaded from', found)

    wrapper = parent.loadTox(found)
    inner = wrapper.op(name)
    if inner is None:
        candidates = [c for c in wrapper.children
                      if c.name not in ('help', 'icon')
                      and (len(c.inputConnectors) or len(c.outputConnectors))]
        if candidates:
            inner = candidates[0]
        else:
            print(name, 'wrapper children ->',
                  [(c.name, c.type, len(c.inputConnectors), len(c.outputConnectors))
                   for c in wrapper.children])

    if inner is None:
        wrapper.name = name
        return wrapper

    comp = parent.copy(inner, name=name + '_unwrap')
    wrapper.destroy()
    comp.name = name
    return comp


def build_post(parent, image_in):
    fb = load_tox(parent, 'feedback', FEEDBACK_TOX)
    wire(fb, image_in)
    apply(fb, {'Opacity': 0.9, 'Dry / Wet Mix': 1}, pars=list(fb.customPars))

    bloom = load_tox(parent, 'bloom', BLOOM_TOX)
    wire(bloom, fb)
    apply(bloom, {
        'Blur Size': 2, 'Iterations': 6, 'Threshold': 0.73, 'Intensity': 2.96,
        'Gamma': 1.11, 'Contrast': 1.05, 'Bloom Level': 0.421, 'Glow Level': 0.593,
        'Glow Color': (0.071, 1, 1), 'Ramp Glow Level': 0.464,
        'Input Level (Mix Out)': 1, 'Blur Type': 'Hanning', 'Pre-Shrink': 1,
        'Sample Step': 1, 'Temporal Smooth': 0,
    }, pars=list(bloom.customPars))

    key = make(parent, 'rgbkeyTOP', 'rgbkey1')
    wire(key, bloom)
    apply(key, {
        'Red Min': 0, 'Red Max': 1, 'Red Soft Low': 0, 'Red Soft High': 0,
        'Green Min': 0, 'Green Max': 1, 'Green Soft Low': 0, 'Green Soft High': 0,
        'Blue Min': 0, 'Blue Max': 1, 'Blue Soft Low': 0, 'Blue Soft High': 0,
        'Invert New Alpha': 0, 'RGB Output': 'Source RGB * New Alpha',
        'Alpha Output': 'New Alpha',
    })

    null4 = make(parent, 'nullTOP', 'null4')
    wire(null4, key)

    window = make(parent, 'windowCOMP', 'window1')
    apply(window, {
        'Window Operator': 'null4', 'Justify and Offset To...': 'Specify Display',
        'Display': 0, 'Justify Horizontal': 'Left', 'Justify Vertical': 'Bottom',
        'Opening Size': 'Automatic from Panel COMP/TOP', 'Borders': 1,
        'Always on Top': 0, 'Allow Viewer Interaction': 0,
        'Window Pixel Format': 'SDR 8-Bit fixed', 'V-Sync Mode': 'Enabled',
        'Draw Window': 1,
    })

    return window


if __name__ == '__main__' or 'op' in globals():
    build()
