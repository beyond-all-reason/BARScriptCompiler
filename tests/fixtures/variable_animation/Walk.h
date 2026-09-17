StartWalk()
{
	set-signal-mask SIGNAL_MOVE;
	VA_useAmplitude = 0;
	call-script VA_Reset();
	while (TRUE) {
		call-script VA_NextKeyframe(3);
		turn thigh to x-axis <10> speed <300> / VA_frames;
		sleep VA_sleepTime;
	}
}

StopWalk()
{
	turn thigh to x-axis <0> speed <100>;
}
