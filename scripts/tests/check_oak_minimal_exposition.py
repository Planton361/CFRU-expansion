"""#592 source-only lifecycle/binding audit; never opens game artifacts."""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '78478c728501fe8c70bd84e01e51c6334250a6f0'
PRET = 'e060ab955b5dc9ac1c4904c2cd141683615cf477'
ALLOWED = {'BPRE.ld', 'functionrewrites', 'src/oak_minimal_exposition.c',
           'scripts/tests/check_oak_minimal_exposition.py', 'docs/oak-minimal-exposition.md'}


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True)


def function(source, name):
    match = re.search(r'\b' + name + r'\([^;{}]*\)\s*\{', source)
    assert match, name
    start = match.end()
    depth = 1
    end = start
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end - 1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pret-root', type=Path, required=True)
    args = parser.parse_args()
    pret = args.pret_root.resolve()
    # Read exact Git source objects, regardless of reference worktree state.
    assert git(pret, 'rev-parse', PRET + '^{commit}').strip() == PRET
    oak = git(pret, 'show', PRET + ':src/oak_speech.c')
    new_game = git(pret, 'show', PRET + ':src/new_game.c')
    overworld = git(pret, 'show', PRET + ':src/overworld.c')
    assert git(ROOT, 'merge-base', BASE, 'HEAD').strip() == BASE
    changed = set(git(ROOT, 'diff', BASE, '--name-only').splitlines())
    assert changed <= ALLOWED, changed - ALLOWED
    for path, addition in (
        ('BPRE.ld', 'Task_OakSpeech_FadeOutOak = 0x0812FD78 | 1;\n'),
        ('functionrewrites', '## #592: BPRE Task_OakSpeech_WelcomeToTheWorld; retain OakSpeech_Init.\n'
         'Task_OakSpeech_MinimalExposition 0x0812F880 1 0\n'),
    ):
        current = (ROOT / path).read_text()
        assert current.count(addition) == 1, path
        assert current.replace(addition, '') == git(ROOT, 'show', BASE + ':' + path), path

    replacement = function((ROOT / 'src/oak_minimal_exposition.c').read_text(),
                           'Task_OakSpeech_MinimalExposition')
    assert re.findall(r'\b([A-Za-z_]\w*)\s*\(', replacement) == [
        'if', 'IsTextPrinterActive', 'DestroySprite', 'Task_OakSpeech_FadeOutOak']
    assert 'gPaletteFade->active || IsTextPrinterActive(0)' in replacement
    assert 'DestroySprite(&gSprites[gTasks[taskId].data[4]]);' in replacement
    assert replacement.index('return;') < replacement.index('DestroySprite(')
    assert replacement.index('DestroySprite(') < replacement.index('Task_OakSpeech_FadeOutOak(taskId);')
    assert replacement.index('Task_OakSpeech_FadeOutOak(taskId);') < replacement.index('gTasks[taskId].data[3] = 0;')
    assert re.findall(r'data\[(\d+)\]', replacement) == ['4', '3']
    assert not re.search(r'SaveBlock|playerGender|playerName|rivalName|CB2_NewGame', replacement)

    # Pinned pret's own source history carries the original BPRE labels.
    history_pin = 'fb7ba2161078a822da9698ef801472baf1ee0ed1'
    assert git(pret, 'merge-base', history_pin, PRET).strip() == history_pin
    history = git(pret, 'show', history_pin + ':src/oak_speech.c')
    init = function(history, 'sub_812F7C0')
    assert 'CreateNidoranFSprite(taskId);' in init and 'gTasks[taskId].func = sub_812F880;' in init
    assert 'gTasks[taskId].func = sub_812F944;' in function(history, 'sub_812F880')
    fade = function(history, 'sub_812FD78')
    assert 'sub_813144C(taskId, 2);' in fade and 'gTasks[taskId].func = sub_812FDC0;' in fade
    assert 'data[2] != 0' in function(history, 'sub_812FDC0')
    assert 'gTasks[taskId].func = sub_812FE88;' in function(history, 'sub_812FDC0')

    def edge(start, end):
        assert 'gTasks[taskId].func = ' + end + ';' in function(oak, start), (start, end)

    skipped = ['WelcomeToTheWorld', 'ThisWorld', 'ReleaseNidoranFFromPokeBall',
               'IsInhabitedFarAndWide', 'IStudyPokemon', 'ReturnNidoranFToPokeBall',
               'TellMeALittleAboutYourself']
    retained = ['FadeOutOak', 'AskPlayerGender', 'ShowGenderOptions',
                'HandleGenderInput', 'ClearGenderWindows', 'LoadPlayerPic',
                'YourNameWhatIsIt', 'FadeOutForPlayerNamingScreen', 'DoNamingScreen']
    chain = ['Init'] + skipped + retained
    for start, end in zip(chain, chain[1:]):
        edge('Task_OakSpeech_' + start, 'Task_OakSpeech_' + end)
    init = function(oak, 'Task_OakSpeech_Init')
    for call in ['MallocAndDecompress', 'LoadBgTiles', 'CreateNidoranFSprite',
                 'LoadTrainerPic', 'CreatePikachuOrPlatformSprites', 'PlayBGM',
                 'BeginNormalPaletteFade', 'ShowBg']:
        assert call + '(' in init, call
    original_cleanup = function(oak, 'Task_OakSpeech_TellMeALittleAboutYourself')
    assert 'DestroySprite(&gSprites[tNidoranFSpriteId]);' in original_cleanup
    assert 'DestroySprite(&gSprites[tPokeBallSpriteId]);' in original_cleanup
    fade = function(oak, 'Task_OakSpeech_FadeOutOak')
    assert 'CreateFadeInTask(taskId, 2);' in fade
    assert 'tTrainerPicFadeState != 0' in function(oak, 'Task_OakSpeech_AskPlayerGender')
    assert 'ClearTrainerPic();' in function(oak, 'Task_OakSpeech_AskPlayerGender')
    gender = function(oak, 'Task_OakSpeech_HandleGenderInput')
    assert 'playerGender = MALE;' in gender and 'playerGender = FEMALE;' in gender
    assert 'case MENU_B_PRESSED:' in gender
    naming = function(oak, 'Task_OakSpeech_DoNamingScreen')
    for token in ['GetDefaultName(', 'NAMING_SCREEN_PLAYER', 'NAMING_SCREEN_RIVAL',
                  'CB2_ReturnFromNamingScreen', 'DestroyPikachuOrPlatformSprites(', 'FreeAllWindowBuffers();']:
        assert token in naming, token
    confirm = function(oak, 'Task_OakSpeech_HandleConfirmNameInput')
    for end in ['FadeOutPlayerPic', 'FadeOutRivalPic', 'FadeOutForPlayerNamingScreen', 'RepeatNameQuestion']:
        edge('Task_OakSpeech_HandleConfirmNameInput', 'Task_OakSpeech_' + end)
    assert 'case MENU_B_PRESSED:' in confirm and 'case 1: // NO' in confirm
    for start, end in [('FadeOutPlayerPic', 'FadeInRivalPic'), ('FadeInRivalPic', 'AskRivalsName'),
                       ('AskRivalsName', 'MoveRivalDisplayNameOptions'),
                       ('MoveRivalDisplayNameOptions', 'HandleRivalNameInput'),
                       ('HandleRivalNameInput', 'DoNamingScreen'),
                       ('HandleRivalNameInput', 'ConfirmName'),
                       ('FadeOutRivalPic', 'ReshowPlayersPic'), ('ReshowPlayersPic', 'LetsGo'),
                       ('LetsGo', 'FadeOutBGM'), ('FadeOutBGM', 'SetUpExitAnimation'),
                       ('SetUpShrinkPlayerPic', 'ShrinkPlayerPic'),
                       ('ShrinkPlayerPic', 'FadePlayerPicToBlack'),
                       ('FadePlayerPicToBlack', 'WaitForFade'), ('WaitForFade', 'FreeResources')]:
        edge('Task_OakSpeech_' + start, 'Task_OakSpeech_' + end)
    cleanup = function(oak, 'Task_OakSpeech_FreeResources')
    for token in ['FreeAllWindowBuffers();', 'DestroyMonSpritesGfxManager();',
                  'Free(sOakSpeechResources);', 'sOakSpeechResources = NULL;',
                  'SetMainCallback2(CB2_NewGame);', 'DestroyTask(taskId);']:
        assert token in cleanup, token
    assert 'NewGameInitData();' in function(overworld, 'CB2_NewGame')
    for token in ['InitPlayerTrainerId();', 'InitEventData();', 'WarpToPlayersRoom();',
                  'StringCopy(gSaveBlock1Ptr->rivalName, rivalName);']:
        assert token in function(new_game, 'NewGameInitData'), token
    assert '(Random() << 0x10) | GetGeneratedTrainerIdLower()' in function(new_game, 'InitPlayerTrainerId')
    print('PASS: exact source bindings, bypass/retained lifecycle, identity/retry/default/Trainer ID paths')
    print('PASS: bounded source diff; no SaveBlock/layout, settings, running, story or Gitlink change')
    print('SOURCE ONLY: no build/runtime acceptance claimed')


if __name__ == '__main__':
    main()
