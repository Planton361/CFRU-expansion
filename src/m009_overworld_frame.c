#include "../include/global.h"
#include "../include/task.h"
#include "../include/sprite.h"
#include "../include/palette.h"
#include "../include/new/hidden_item_sparkle.h"

// Existing BPRE.ld symbols; historical names verified in pret commits
// 72f76b19b35273581f84467efb96a08b9dca6753 and
// 45546ce3508deb0b2f659c8892161d444b91b08d. No new address bindings.
extern bool8 ScriptContext_RunScript(void) __asm__("ScriptContext2_RunScript") __attribute__((long_call));
extern void SetQuestLogEvent_Arrived(void) __asm__("sub_8115798") __attribute__((long_call));
void __attribute__((long_call)) CameraUpdate(void);
void __attribute__((long_call)) UpdateCameraPanning(void);
void __attribute__((long_call)) UpdateTilesetAnimations(void);
void __attribute__((long_call)) DoScheduledBgTilemapCopiesToVram(void);

// Sole named rewrite of OverworldBasic. CB2 wrappers retain fade/VBlank logic.
// Exact pret e060ab95 / Cyan 16b8b9ff order, intentionally superseding M-008's
// slow-camera ordering. Keep the scanner after scheduled BG copies.
void M009_OverworldBasic(void)
{
    ScriptContext_RunScript();
    RunTasks();
    AnimateSprites();
    CameraUpdate();
    SetQuestLogEvent_Arrived();
    UpdateCameraPanning();
    BuildOamBuffer();
    UpdatePaletteFade();
    UpdateTilesetAnimations();
    DoScheduledBgTilemapCopiesToVram();
    TryStartVisibleHiddenItemSparkles();
}
