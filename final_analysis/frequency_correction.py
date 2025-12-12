#!/usr/bin/env python3
"""
Frequency correction for sessions saved with incorrect log formula

Based on: docs/LOG_FREQUENCY_CONVERSION_CHANGE.md
Fix date: 2025-11-25
"""

import math

def correct_log_frequency(freq_saved, playback_rate, max_freq=50):
    """
    Correct frequency values saved with the old broken logarithmic formula.

    Args:
        freq_saved: The incorrectly saved frequency value
        playback_rate: The playback rate (speedFactor) when the feature was captured
        max_freq: Nyquist frequency (typically 50 Hz)

    Returns:
        The corrected frequency value
    """
    min_freq = 0.1
    log_min = math.log10(min_freq)  # -1
    log_max = math.log10(max_freq)
    log_range = log_max - log_min

    # OLD (broken) stretch factor
    stretch_factor_old = math.log10(max_freq * playback_rate) / math.log10(max_freq)

    # NEW (correct) stretch factor
    target_max_freq = max_freq / playback_rate
    log_target_max = math.log10(max(target_max_freq, min_freq))
    target_log_range = log_target_max - log_min
    fraction = target_log_range / log_range
    stretch_factor_new = 1 / fraction

    # Correction ratio
    correction_ratio = stretch_factor_old / stretch_factor_new

    # Apply correction in log space
    log_freq_saved = math.log10(max(freq_saved, min_freq))
    log_freq_corrected = log_min + (log_freq_saved - log_min) * correction_ratio

    return 10 ** log_freq_corrected

def correct_feature_frequencies(feature, uses_corrected_formula):
    """
    Correct frequency values in a feature if needed

    Args:
        feature: Feature dict with lowFreq, highFreq, speedFactor
        uses_corrected_formula: Whether the session used the corrected formula

    Returns:
        Feature dict with corrected frequencies (if needed)
    """
    # If already using corrected formula, no correction needed
    if uses_corrected_formula:
        return feature

    # If speedFactor is missing or 1.0, no correction needed
    speed_factor = feature.get('speedFactor', 1)
    if speed_factor == 1.0:
        return feature

    # Apply correction
    low_freq = feature.get('lowFreq')
    high_freq = feature.get('highFreq')

    if low_freq is not None and high_freq is not None:
        try:
            low_freq_f = float(low_freq)
            high_freq_f = float(high_freq)

            corrected_low = correct_log_frequency(low_freq_f, speed_factor)
            corrected_high = correct_log_frequency(high_freq_f, speed_factor)

            # Create corrected feature (preserve original as well for debugging)
            corrected_feature = feature.copy()
            corrected_feature['lowFreq_original'] = low_freq
            corrected_feature['highFreq_original'] = high_freq
            corrected_feature['lowFreq'] = f"{corrected_low:.2f}"
            corrected_feature['highFreq'] = f"{corrected_high:.2f}"
            corrected_feature['frequency_corrected'] = True

            return corrected_feature
        except (ValueError, TypeError):
            # If conversion fails, return original
            return feature

    return feature

if __name__ == '__main__':
    # Test the correction
    print("Testing frequency correction:\n")

    # Example: Feature saved at 2x playback with lowFreq = 5.0 Hz
    test_cases = [
        (5.0, 0.5, "Slow playback (0.5x) - should have largest correction"),
        (10.0, 1.0, "Normal playback (1.0x) - should be identical"),
        (5.0, 2.0, "Fast playback (2.0x) - should have moderate correction"),
    ]

    for freq, rate, desc in test_cases:
        corrected = correct_log_frequency(freq, rate)
        diff_pct = abs(corrected - freq) / freq * 100
        print(f"{desc}")
        print(f"  Original: {freq:.2f} Hz")
        print(f"  Corrected: {corrected:.2f} Hz")
        print(f"  Difference: {diff_pct:.1f}%\n")
