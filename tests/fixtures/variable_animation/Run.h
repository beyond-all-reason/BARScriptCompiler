StartRun()
{
	set-signal-mask SIGNAL_MOVE;
	VA_useAmplitude = 1;
	call-script VA_Reset();
	while (TRUE) {
		call-script VA_NextKeyframe(2);
		move pelvis to y-axis ([1] + (([2] * VA_amplitude) / 100)) speed (([60] * VA_amplitude) / 100) / VA_frames;
		sleep VA_sleepTime;
	}
}

StopRun()
{
	move pelvis to y-axis [1] speed [10];
}
