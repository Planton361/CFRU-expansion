#include "defines.h"
#include "include/gba/gba.h"
#include "include/new/ruins_of_alph.h"

// This file provides a rough skeleton for the Ruins of Alph puzzle
// ported from the original standalone project located in the
// `ruins-of-alph` directory. It does not replicate the full logic, but
// establishes the entry points used by the engine.

static const u8 sTutorialText[] = {
    0xF8, 0x0C, 0xC7, 0xC9, 0xD0, 0xBF, 0x00, 0x00,
    0xF8, 0x00, 0xC1, 0xCC, 0xBB, 0xBC, 0x00, 0x00,
    0xF8, 0x01, 0xBF, 0xD2, 0xC3, 0xCE, 0xFF,
};

void RuinsOfAlph_Init(void)
{
    // TODO: load graphics and set callbacks as in init/init2/init3
}

void RuinsOfAlph_Main(void)
{
    // TODO: implement puzzle logic ported from main.c
}
