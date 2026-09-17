// SuperSkeletor include contract:
// requires SIGNAL_MOVE and unit-owned VA_frames, VA_sleepTime, VA_amplitude,
// VA_timeError, VA_useAmplitude plus variable_animation.h when Variable Speed is enabled.

StartWalk()
{
	set-signal-mask SIGNAL_MOVE;
	VA_useAmplitude = 0;
	call-script VA_Reset();
	call-script VA_NextKeyframe(3);
	// Blender frame 3 (source delta 3)
	move pelvis to z-axis [2.000000] speed [30.000000] / VA_frames;
	turn thigh to x-axis <-10.000000> speed <300.000000> / VA_frames;
	sleep VA_sleepTime;

	while (TRUE) {
		call-script VA_NextKeyframe(2);
		// Blender frame 5 (source delta 2)
		move pelvis to z-axis [1.000000] speed [30.000000] / VA_frames;
		turn thigh to x-axis <5.000000> speed <450.000000> / VA_frames;
		sleep VA_sleepTime;
	}
}

StopWalk()
{
	move pelvis to z-axis [1.000000] speed [15.000000];
	turn thigh to x-axis <0.000000> speed <225.000000>;
}
