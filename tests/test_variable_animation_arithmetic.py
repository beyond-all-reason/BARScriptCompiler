import itertools


PRECISION = 1000


def dda(desired_scaled_values, minimum=1, maximum=12):
	error = 0
	result = []
	for desired in desired_scaled_values:
		error += desired
		frames, error = divmod(error, PRECISION)
		if frames < minimum or frames > maximum:
			frames = min(max(frames, minimum), maximum)
			error = 0
		result.append(frames)
	return result, error


def trunc_div(numerator, denominator):
	return int(numerator / denominator)


def module_step(source_delta, current, maximum, blend=50, use_amplitude=True):
	maximum = max(maximum, 1)
	current = min(max(current, max(maximum * 25 // 100, 1)), maximum * 150 // 100)
	speed_percent = (current // maximum) * 100 + (current % maximum) * 100 // maximum
	amplitude = 100 + trunc_div((speed_percent - 100) * blend, 100) if use_amplitude else 100
	amplitude = min(max(amplitude, 50), 125)
	ratio = (maximum // current) * PRECISION + (maximum % current) * PRECISION // current
	desired = min(max(source_delta, 1), 120) * amplitude * ratio // 100
	return desired, amplitude, current, ratio


def test_dda_exact_halves_and_thirds():
	frames, _ = dda(itertools.repeat(2000, 20))
	assert frames == [2] * 20
	frames, _ = dda(itertools.repeat(2500, 8))
	assert frames == [2, 3] * 4
	frames, error = dda(itertools.repeat(2333, 100))
	assert abs(sum(frames) - 233.3) < 1
	assert 0 <= error < PRECISION


def test_uneven_intervals_preserve_long_run_sum():
	desired = [value * PRECISION for value in [3, 2, 4]] * 20
	frames, error = dda(desired)
	assert sum(frames) == 180
	assert error == 0


def test_changing_speed_keeps_remainder_in_constant_precision_domain():
	desired = [2500, 2333, 1750, 2500, 2333]
	frames, error = dda(desired)
	assert frames == [2, 2, 2, 3, 2]
	assert error == sum(desired) - sum(frames) * PRECISION


def test_boundaries_are_safe_and_nonzero():
	for current in (0, 1, 327500, 1310000, 1965000, 99999999):
		desired, amplitude, clamped_speed, ratio = module_step(120, current, 1310000)
		assert 1 <= clamped_speed <= 1965000
		assert 50 <= amplitude <= 125
		assert desired <= 2_147_483_647
		assert ratio <= 4000
		frames, _ = dda([desired])
		assert 1 <= frames[0] <= 12
		assert 33 * frames[0] - 1 > 0


def test_max_speed_preserves_authored_animation():
	for delta in (1, 2, 3, 4, 12):
		desired, amplitude, _, _ = module_step(delta, 1310000, 1310000)
		assert amplitude == 100
		assert desired == delta * PRECISION


def test_no_skid_identity_before_clamps_and_quantization():
	for speed_percent in (50, 75, 100, 125, 150):
		for blend in (0, 50, 100):
			desired, amplitude, _, _ = module_step(4, speed_percent * 1000, 100000, blend)
			timing_ratio = desired / (4 * PRECISION)
			apparent_ratio = (amplitude / 100) / timing_ratio
			assert abs(apparent_ratio - speed_percent / 100) < 0.003
