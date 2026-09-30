"""TouchDesigner setup for audiofilein1 + audioAnalysis.

Run inside TouchDesigner (Text DAT -> Run Script, or textport: op('/project1/audio_setup').run()).
"""

PARENT_PATH = '/project1'
AUDIO_FILE = 'D:/Telechargement/Deep Republik.mp3'
ANALYSIS_TOX = 'f:/touchdesigner code/audioAnalysis.tox'

# Per-song tuning, keyed by the parameter's on-screen label (Controls page).
ANALYSIS_SETTINGS = {
    'Send Audio to Default Out': False,
    'Audio Listen Volume': 0.5,
    'Low Active': True,
    'Low Threshold': 0.0,
    'Low Gain': 3.3636,
    'Low Add': 0.3636,
    'Low Smooth': 0.1636,
    'Mid Active': True,
    'Mid Threshold': 0.034,
    'Mid Gain': 2.9772,
    'Mid Add': 0.5,
    'Mid Smooth': 0.1727,
    'High Active': True,
    'High Threshold': 0.0,
    'High Gain': 2.7272,
    'High Add': 0.2272,
    'High Smooth': 0.0,
    'Kick Active': True,
    'Kick Threshold': 0.0317,
    'Snare Active': True,
    'Snare Threshold': 0.142,
    'Rythm Active': False,
    'Rythm Threshold': 49.459,
    'Slow Spect Density Active': False,
    'Fast Spect Density Active': True,
    'Spectral Centroid Active': False,
    'Enable Mapper': False,
}


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


def load_palette_comp(parent, name, fallback=''):
    """Load a Palette component, unwrapping the help/icon package it ships in."""
    comp = parent.op(name)
    if comp is not None:
        return comp

    path = find_palette_tox(name, fallback)
    if not path:
        raise RuntimeError(name + ' not found in the Palette')
    print(name, 'loaded from', path)

    wrapper = parent.loadTox(path)
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


def setup_audiofilein(parent):
    node = parent.op('audiofilein1') or parent.create(audiofileinCHOP, 'audiofilein1')
    settings = {
        'File': AUDIO_FILE, 'Play': 1, 'Play Mode': 'Sequential', 'Speed': 1,
        'Repeat': 'On', 'Trim': 0, 'Pre-Read Length': 1, 'Mono': 0,
        'Volume': 1, 'Fade In/Out': 1,
    }
    apply_by_label(node, settings)
    return node


def setup_audioanalysis(parent, audio_in):
    comp = load_palette_comp(parent, 'audioAnalysis', ANALYSIS_TOX)

    if comp.inputConnectors:
        comp.inputConnectors[0].connect(audio_in)
    else:
        print('audioAnalysis: no input connector, connect it by hand')

    by_label = {p.label: p for p in comp.customPars}
    missing = []
    for label, value in ANALYSIS_SETTINGS.items():
        par = by_label.get(label)
        if par is None:
            missing.append(label)
            continue
        par.val = value
    if missing:
        print('audioAnalysis: labels not found ->', missing)
    return comp


def apply_by_label(node, settings):
    by_label = {p.label: p for p in node.pars()}
    missing = []
    for label, value in settings.items():
        par = by_label.get(label)
        if par is None:
            missing.append(label)
            continue
        try:
            if par.isMenu and isinstance(value, str):
                labels = [m.lower() for m in par.menuLabels]
                par.menuIndex = labels.index(value.lower())
            else:
                par.val = value
        except Exception as e:
            missing.append(f'{label} ({e})')
    if missing:
        print(f'{node.name}: not applied ->', missing)


def setup_null1(parent, analysis):
    node = parent.op('null1') or parent.create(nullCHOP, 'null1')
    node.inputConnectors[0].connect(analysis.outputConnectors[0])
    apply_by_label(node, {'Cook Type': 'Automatic'})
    return node


def setup_speed1(parent, null_in):
    node = parent.op('speed1') or parent.create(speedCHOP, 'speed1')
    node.inputConnectors[0].connect(null_in)
    apply_by_label(node, {
        'Order': 'First', 'First Constant': 0, 'Limit Type': 'Off',
        'Speed per Sample': 0, 'Reset Value': 0, 'Reset on Start': 1,
    })
    return node


def setup_null2(parent, audio_in):
    node = parent.op('null2') or parent.create(nullCHOP, 'null2')
    node.inputConnectors[0].connect(audio_in)
    return node


def setup_audiodevout(parent, audio_in):
    node = parent.op('audiodevout1') or parent.create(audiodeviceoutCHOP, 'audiodevout1')
    node.inputConnectors[0].connect(audio_in)
    return node


def build():
    parent = op(PARENT_PATH)
    audio_in = setup_audiofilein(parent)
    analysis = setup_audioanalysis(parent, audio_in)
    null1 = setup_null1(parent, analysis)
    speed1 = setup_speed1(parent, null1)
    null2 = setup_null2(parent, audio_in)
    devout = setup_audiodevout(parent, audio_in)
    return audio_in, analysis, null1, speed1, null2, devout


if __name__ == '__main__' or 'op' in globals():
    build()
