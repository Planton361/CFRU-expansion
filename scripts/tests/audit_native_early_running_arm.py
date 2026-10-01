#!/usr/bin/env python3
"""#583 ARM/preprocessor/object proof, ROM-free; optional fresh linked object."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

from audit_early_running_lifecycle import ROOT, BASE_SHA, REMOVED, c_function, require, check_source_contract

FLAGS = ['-mthumb', '-mno-thumb-interwork', '-mcpu=arm7tdmi', '-mtune=arm7tdmi',
         '-mno-long-calls', '-march=armv4t', '-Os', '-fira-loop-pressure', '-fipa-pta']


def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True)


def sections(obj):
    result = {}
    for line in run('arm-none-eabi-objdump', '-h', str(obj)).splitlines():
        fields = line.split()
        if len(fields) > 2 and fields[0].isdigit():
            result[fields[1]] = int(fields[2], 16)
    return result


def code(disassembly, name):
    return disassembly.split('<' + name + '>:', 1)[1].split('\n\n', 1)[0]


def check_negative_source_witnesses():
    import audit_early_running_lifecycle as audit
    original = audit.read
    cases = (
        ('src/config.h', '//#define FLAG_RUNNING_ENABLED', '#define FLAG_RUNNING_ENABLED'),
        ('src/config.h', '#define FLAG_AUTO_RUN 0x914', '//#define FLAG_AUTO_RUN 0x914'),
        ('src/config.h', '#define CAN_RUN_IN_BUILDINGS', '//#define CAN_RUN_IN_BUILDINGS'),
        ('src/settings.c', 'void ApplyFreshNewGameSettings(void)',
         'static bool8 sReplacementPending;\nvoid ApplyFreshNewGameSettings(void)'),
        ('src/settings.c', 'VarSet(VAR_WILD_LEVEL_SCALING, 0);',
         'VarSet(VAR_WILD_LEVEL_SCALING, 0); FlagSet(0x82F);'),
        ('assembly/hooks/general_hooks.s', 'ldr r3, =ScriptContext_Init\n\tbl FreshNewGameSettingsCallR3',
         ''),
        ('assembly/hooks/general_hooks.s', '0x8056662 | 1', '0x805665E | 1'),
    )
    for path, old, new in cases:
        current = original(path)
        require(old in current, 'negative witness no longer mutates source')
        try:
            audit.read = lambda name: current.replace(old, new, 1) if name == path else original(name)
            try:
                audit.check_source_contract()
            except AssertionError:
                continue
            raise AssertionError('accepted negative #583 witness: ' + old)
        finally:
            audit.read = original
    print('#583 config/helper/state/hook negative witnesses: PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linked-object', type=Path)
    args = parser.parse_args()
    check_source_contract()
    check_negative_source_witnesses()
    with tempfile.TemporaryDirectory(prefix='cfru-583-arm-') as directory:
        temp = Path(directory)
        macros = run('arm-none-eabi-gcc', *FLAGS, '-E', '-dM', 'src/overworld.c')
        require(not re.search(r'^#define FLAG_RUNNING_ENABLED\b', macros, re.M), 'ARM config retains gate')
        require('#define FLAG_AUTO_RUN 0x914' in macros, 'ARM Auto-Run flag missing')
        require('#define CAN_RUN_IN_BUILDINGS' in macros, 'ARM indoor config missing')
        baseline = temp / 'base'
        (baseline / 'src').mkdir(parents=True)
        # Copy source headers only so ../../src includes resolve within the
        # exact-base fixture and pragma-once identities stay consistent.
        for directory in ('src', 'include'):
            for header in (ROOT / directory).rglob('*.h'):
                relative = header.relative_to(ROOT)
                destination = baseline / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(header.read_bytes())
        for path in ('src/config.h', 'include/new/settings.h'):
            (baseline / path).write_text(run('git', 'show', f'{BASE_SHA}:{path}'))
        sources = {}
        for path in ('src/overworld.c', 'src/read_keys.c', 'src/settings.c', 'src/save.c'):
            preprocessed = run('arm-none-eabi-gcc', *FLAGS, '-E', '-P', path)
            sources[path] = preprocessed
            obj = temp / (Path(path).stem + '.o')
            subprocess.run(['arm-none-eabi-gcc', *FLAGS, '-c', path, '-o', str(obj)], cwd=ROOT, check=True)
            if path in ('src/overworld.c', 'src/settings.c', 'src/save.c'):
                base_source = baseline / path
                base_source.write_text(run('git', 'show', f'{BASE_SHA}:{path}'))
                base_obj = temp / ('base_' + Path(path).stem + '.o')
                subprocess.run(['arm-none-eabi-gcc', *FLAGS, '-c', str(base_source),
                                '-o', str(base_obj)], cwd=ROOT, check=True)
                before, after = sections(base_obj), sections(obj)
                for name, size in after.items():
                    if name.startswith(('.bss', '.data', '.sbss', '.sdata')) or 'ewram' in name.lower():
                        require(size <= before.get(name, 0), 'new runtime data section: ' + path + ':' + name)
                def mutable_symbols(object_path):
                    return {line.split()[-1] for line in run('arm-none-eabi-nm', '--defined-only',
                                                            str(object_path)).splitlines()
                            if line.split()[-2] in tuple('bBcCdDgGsS')}
                require(mutable_symbols(obj) <= mutable_symbols(base_obj), 'new mutable linked-state dependency')
                if path == 'src/settings.c':
                    require(before.get('.bss', 0) == 1 and after.get('.bss', 0) == 0,
                            'old target-invalid byte was not removed')
            disassembly = run('arm-none-eabi-objdump', '-dr', str(obj))
            if path == 'src/overworld.c':
                disabled = c_function(preprocessed, 'static bool8 IsRunningDisabledByFlag(void)')
                require(re.sub(r'\s+', '', disabled).endswith('{return0;}'), 'native disabled branch is not FALSE')
                disallowed = code(disassembly, 'IsRunningDisallowed')
                require('FlagGet' not in disallowed, 'ARM running function still queries progression flag')
                movement = c_function(preprocessed, 'bool8 ShouldPlayerRun(u16 heldKeys)')
                require('VarGet' not in movement and '0x82F' not in movement, 'movement depends on settings/progression')
            elif path == 'src/read_keys.c':
                toggle = c_function(preprocessed, 'bool8 StartLButtonFunc(void)')
                require('0x82F' not in toggle and 'FlagGet(0x914)' in toggle,
                        'L preprocessing retains progression gate or loses Auto-Run')
                require('0000082f' not in code(disassembly, 'StartLButtonFunc').lower(),
                        'L ARM literal retains old flag')
            elif path == 'src/settings.c':
                syms = run('arm-none-eabi-nm', '--defined-only', str(obj))
                require(not re.search(r'\b[bBcCdDgGsS]\b', syms), 'settings object defines mutable data')
                for name, size in sections(obj).items():
                    require(not (size and (name.startswith(('.bss', '.data', '.sbss', '.sdata'))
                                           or 'ewram' in name.lower() or name == 'COMMON')),
                            'settings object acquired writable section: ' + name)
                undefined = run('arm-none-eabi-nm', '--undefined-only', str(obj))
                require('FlagSet' not in undefined and 'FlagClear' not in undefined
                        and 'VarSet' in undefined, 'settings ARM owns unexpected state')
        # Assemble the public CB2_NewGame prefix with symbolic BL relocations.
        # Thumb push=2, BL=4: NewGameInitData returns at +0x12; the 10-byte
        # hook touches 3 BLs, whose end is +0x1e. This is source, not ROM bytes.
        public = temp / 'public_cb2_prefix.s'
        public.write_text('''.text
.thumb
.global PublicCB2NewGamePrefix
PublicCB2NewGamePrefix:
push {lr}
bl FieldClearVBlankHBlankCallbacks
bl StopMapMusic
bl ResetSafariZoneFlag_
bl NewGameInitData
.global PublicLateSettingsStart
PublicLateSettingsStart:
bl ResetInitialPlayerAvatarState
bl PlayTimeCounter_Start
bl ScriptContext_Init
.global PublicLateSettingsReturn
PublicLateSettingsReturn:
bl ScriptContext2_Disable
''')
        obj = temp / 'public_cb2_prefix.o'
        subprocess.run(['arm-none-eabi-as', '-mthumb', str(public), '-o', str(obj)], check=True)
        syms = run('arm-none-eabi-nm', str(obj))
        require('00000012 T PublicLateSettingsStart' in syms
                and '0000001e T PublicLateSettingsReturn' in syms, 'public BPRE hook/return offsets changed')
        require(0x8056644 + 0x12 == 0x8056656 and 0x8056644 + 0x1e == 0x8056662,
                'BPRE late hook arithmetic changed')
        general = temp / 'general_hooks.o'
        subprocess.run(['arm-none-eabi-as', '-mthumb', '-I', 'assembly', '-c',
                        'assembly/hooks/general_hooks.s', '-o', str(general)], cwd=ROOT, check=True)
        hook = code(run('arm-none-eabi-objdump', '-dr', str(general)), 'FreshNewGameSettingsHook')
        require('R_ARM_THM_CALL\tApplyFreshNewGameSettings' in hook,
                'hook ARM helper call missing')
        # The absolute vanilla Thumb addresses must be literal loads + BX,
        # never linker-generated BLX (unsupported on ARM7TDMI).
        general_dump = run('arm-none-eabi-objdump', '-dr', str(general))
        for callee in ('ResetInitialPlayerAvatarState', 'PlayTimeCounter_Start', 'ScriptContext_Init'):
            require('R_ARM_ABS32\t' + callee in general_dump, 'hook ARM Thumb literal missing: ' + callee)
        require('bx\tr3' in code(general_dump, 'FreshNewGameSettingsCallR3'), 'Thumb call trampoline missing')
        require(not any(size for name, size in sections(general).items()
                        if name in ('.bss', '.data', 'ewram_data')), 'hook object acquired data')
        print('#583 full ARM preprocessing, native running/L gates, zero settings data, hook replay/offsets: PASS')
    if args.linked_object:
        linked = args.linked_object.resolve()
        symbols = run('arm-none-eabi-nm', '-S', str(linked))
        require(not any(name in symbols for name in REMOVED), 'linked pending symbol remains')
        require(not any('pending' in line.lower() and line.split()[-2] not in ('t', 'T')
                        for line in symbols.splitlines()), 'linked mutable pending symbol')
        bss = {line.split()[-1]: line.split()[0] for line in symbols.splitlines()
               if line.split()[-1] in ('__bss_start__', '__bss_end__')}
        require(len(bss) == 2 and bss['__bss_start__'] == bss['__bss_end__'], 'linked BSS is not empty')
        require('FreshNewGameSettingsHook' in symbols and 'ApplyFreshNewGameSettings' in symbols,
                'final linked settings owner missing')
        disassembly = run('arm-none-eabi-objdump', '-d', str(linked))
        require('FlagGet' not in code(disassembly, 'IsRunningDisallowed'), 'linked running progression gate')
        late_hook = code(disassembly, 'FreshNewGameSettingsHook')
        require('blx' not in late_hook and late_hook.count('<FreshNewGameSettingsCallR3>') == 3,
                'linked hook has ARM7-incompatible call or missing replay')
        require('bx\tr3' in code(disassembly, 'FreshNewGameSettingsCallR3'), 'linked Thumb replay missing')
        for literal in ('080559e5', '08054839', '08069a81', '08056663'):
            require(literal in disassembly.split('<FreshNewGameSettingsCallR3>:', 1)[1].split('\n\n', 1)[0],
                    'linked replay literal/continuation changed: ' + literal)
        # Inspect the settings object actually used by build.py as well: additionally inspect the object actually used by build.py.
        settings = ROOT / 'build' / (hashlib.md5(b'./src/settings.c').hexdigest()[:8] + '.o')
        require(not re.search(r'\b[bBcCdDgGsS]\b', run('arm-none-eabi-nm', '--defined-only', str(settings))),
                'build-linked settings object has mutable symbols')
        require(not any(size for name, size in sections(linked).items()
                        if 'ewram' in name.lower() or name.startswith('.bss')),
                'new orphan writable output section')
        print('#583 final linked native gate/owner and absent pending/data/orphan symbols: PASS')


if __name__ == '__main__':
    main()
