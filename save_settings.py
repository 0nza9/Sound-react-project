"""Write the live audiofilein1 / audioAnalysis values back into audio_setup.py.

Tweak the song and the audioAnalysis knobs by hand in TouchDesigner, then run this
(Text DAT -> Run Script) to persist them.
"""

PARENT_PATH = '/project1'
TARGET = 'f:/touchdesigner code/audio_setup.py'
POP_TARGET = 'f:/touchdesigner code/pop_setup.py'

# constant name in pop_setup.py -> (operator, parameter label)
MAPPINGS = [
    ('MAP_LOW', 'noise2', 'Translate 4D'),
    ('MAP_FMSD', 'noise1', 'Translate 4D'),
    ('MAP_SNARE', 'math1', 'Multiply'),
]


def collect():
    parent = op(PARENT_PATH)
    song = parent.op('audiofilein1').par.file.eval()
    comp = parent.op('audioAnalysis')

    values = {}
    for par in comp.customPars:
        if par.page.name == 'Controls':
            value = par.eval()
            if isinstance(value, float):
                value = round(value, 4)
            values[par.label] = value
    return song, values


def rewrite(song, values):
    with open(TARGET, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')

    out = []
    in_block = False
    for line in lines:
        if line.startswith('AUDIO_FILE = '):
            out.append('AUDIO_FILE = ' + repr(song))
            continue
        if line.startswith('ANALYSIS_SETTINGS = {'):
            out.append('ANALYSIS_SETTINGS = {')
            for label, value in values.items():
                out.append('    ' + repr(label) + ': ' + repr(value) + ',')
            out.append('}')
            in_block = True
            continue
        if in_block:
            if line.startswith('}'):
                in_block = False
            continue
        out.append(line)

    with open(TARGET, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))


def collect_mappings():
    parent = op(PARENT_PATH)
    found = {}
    for const, op_name, label in MAPPINGS:
        node = parent.op(op_name)
        if node is None:
            print('skipped', const, '- no operator', op_name)
            continue
        par = next((p for p in node.pars() if p.label == label), None)
        if par is None:
            print('skipped', const, '- no parameter', label, 'on', op_name)
            continue
        if not par.expr:
            print('skipped', const, '-', op_name, label, 'has no expression')
            continue
        found[const] = par.expr
    return found


def rewrite_mappings(found):
    with open(POP_TARGET, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')

    out = []
    for line in lines:
        const = next((c for c in found if line.startswith(c + ' = ')), None)
        if const is not None:
            out.append(const + ' = ' + repr(found[const]))
            continue
        out.append(line)

    with open(POP_TARGET, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))


def save():
    song, values = collect()
    rewrite(song, values)
    print('saved', len(values), 'settings and song ->', TARGET)
    print('song:', song)

    found = collect_mappings()
    if found:
        rewrite_mappings(found)
        print('saved', len(found), 'mappings ->', POP_TARGET)
        for const, expr in found.items():
            print('   ', const, '=', expr)


if __name__ == '__main__' or 'op' in globals():
    save()
