#include "../include/global.h"
#include "../include/palette.h"
#include "../include/sprite.h"
#include "../include/task.h"
#include "../include/text.h"

void __attribute__((long_call)) Task_OakSpeech_FadeOutOak(u8 taskId);

// #592: replaces WelcomeToTheWorld, after the original OakSpeech_Init.
// Task data indices are owned by BPRE oak_speech.c, not persistent storage.
void Task_OakSpeech_MinimalExposition(u8 taskId)
{
	if (gPaletteFade.active || IsTextPrinterActive(0))
		return;

	// Init created this hidden sprite. The bypassed TellMeALittleAboutYourself
	// normally destroys it and a Poke Ball sprite; no ball was created here.
	DestroySprite(&gSprites[gTasks[taskId].data[4]]);
	Task_OakSpeech_FadeOutOak(taskId);
	// Retain the original fade task and its completion gate, without the
	// additional 48-frame wait before the normal gender question.
	gTasks[taskId].data[3] = 0;
}
