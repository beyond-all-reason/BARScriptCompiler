// SuperSkeletor include contract:
// requires SIGNAL_MOVE and unit-owned VA_frames, VA_sleepTime, VA_amplitude,
// VA_timeError, VA_useAmplitude plus variable_animation.h when Variable Speed is enabled.

StartRun()
{
	set-signal-mask SIGNAL_MOVE;
	VA_useAmplitude = 1;
	call-script VA_Reset();
	call-script VA_NextKeyframe(3);
	// Blender frame 3 (source delta 3)
	move pelvis to z-axis ([1.000000] + (([1.000000] * VA_amplitude) / 100)) speed (([30.000000] * VA_amplitude) / 100) / VA_frames;
	turn thigh to x-axis (<0.000000> + ((<-10.000000> * VA_amplitude) / 100)) speed ((<300.000000> * VA_amplitude) / 100) / VA_frames;
	sleep VA_sleepTime;

	while (TRUE) {
		call-script VA_NextKeyframe(2);
		// Blender frame 5 (source delta 2)
		move pelvis to z-axis ([1.000000] + (([0.000000] * VA_amplitude) / 100)) speed (([30.000000] * VA_amplitude) / 100) / VA_frames;
		turn thigh to x-axis (<0.000000> + ((<5.000000> * VA_amplitude) / 100)) speed ((<450.000000> * VA_amplitude) / 100) / VA_frames;
		sleep VA_sleepTime;
	}
}

StopRun()
{
	move pelvis to z-axis [1.000000] speed [15.000000];
	turn thigh to x-axis <0.000000> speed <225.000000>;
}
