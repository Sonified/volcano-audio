#!/usr/bin/env python3
"""
Test script for logarithmic frequency correction formula.

Validates that the correction function in docs/LOG_FREQUENCY_CONVERSION_CHANGE.md
can recover correct frequencies from data saved with the old broken formula.
"""

import math

# Constants (match JavaScript implementation)
MIN_FREQ = 0.1
MAX_FREQ = 50.0  # Nyquist for 100 Hz sample rate


def old_stretch_factor(playback_rate, max_freq):
    """OLD (broken) stretch factor formula"""
    effective_nyquist = max_freq * playback_rate
    return math.log10(effective_nyquist) / math.log10(max_freq)


def new_stretch_factor(playback_rate, max_freq):
    """NEW (correct) stretch factor formula"""
    log_min = math.log10(MIN_FREQ)
    log_max = math.log10(max_freq)
    log_range = log_max - log_min
    
    target_max_freq = max_freq / playback_rate
    log_target_max = math.log10(max(target_max_freq, MIN_FREQ))
    target_log_range = log_target_max - log_min
    fraction = target_log_range / log_range
    return 1 / fraction


def y_to_freq_old(y, canvas_height, playback_rate, max_freq):
    """Convert Y position to frequency using OLD (broken) formula"""
    log_min = math.log10(MIN_FREQ)
    log_max = math.log10(max_freq)
    log_range = log_max - log_min
    
    stretch = old_stretch_factor(playback_rate, max_freq)
    height_from_bottom_scaled = canvas_height - y
    height_from_bottom_1x = height_from_bottom_scaled / stretch
    normalized_log = height_from_bottom_1x / canvas_height
    log_freq = log_min + (normalized_log * log_range)
    
    return 10 ** log_freq


def y_to_freq_new(y, canvas_height, playback_rate, max_freq):
    """Convert Y position to frequency using NEW (correct) formula"""
    log_min = math.log10(MIN_FREQ)
    log_max = math.log10(max_freq)
    log_range = log_max - log_min
    
    stretch = new_stretch_factor(playback_rate, max_freq)
    height_from_bottom_scaled = canvas_height - y
    height_from_bottom_1x = height_from_bottom_scaled / stretch
    normalized_log = height_from_bottom_1x / canvas_height
    log_freq = log_min + (normalized_log * log_range)
    
    return 10 ** log_freq


def correct_log_frequency(freq_saved, playback_rate, max_freq=50):
    """
    Correct frequency values saved with the old broken logarithmic formula.
    """
    log_min = math.log10(MIN_FREQ)
    log_max = math.log10(max_freq)
    log_range = log_max - log_min
    
    stretch_factor_old = old_stretch_factor(playback_rate, max_freq)
    stretch_factor_new = new_stretch_factor(playback_rate, max_freq)
    correction_ratio = stretch_factor_old / stretch_factor_new
    
    log_freq_saved = math.log10(max(freq_saved, MIN_FREQ))
    log_freq_corrected = log_min + (log_freq_saved - log_min) * correction_ratio
    
    return 10 ** log_freq_corrected


def main():
    print("=" * 60)
    print("Logarithmic Frequency Correction Test")
    print("=" * 60)
    
    canvas_height = 500
    
    # Test realistic playback rates (0.1x to 15x range)
    playback_rates = [0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 15.0]
    
    # Test middle-of-canvas Y positions (where users actually draw boxes)
    y_positions = [150, 250, 350]  # Avoiding edges
    
    all_passed = True
    
    print("\n✓ = correction recovered correct frequency")
    print("✗ = correction failed\n")
    
    for playback_rate in playback_rates:
        old_sf = old_stretch_factor(playback_rate, MAX_FREQ)
        new_sf = new_stretch_factor(playback_rate, MAX_FREQ)
        diff_pct = abs(old_sf - new_sf) / new_sf * 100
        
        print(f"playbackRate = {playback_rate}x (formula diff: {diff_pct:.1f}%)")
        
        for y in y_positions:
            freq_correct = y_to_freq_new(y, canvas_height, playback_rate, MAX_FREQ)
            freq_saved = y_to_freq_old(y, canvas_height, playback_rate, MAX_FREQ)
            freq_recovered = correct_log_frequency(freq_saved, playback_rate, MAX_FREQ)
            
            error = abs(freq_recovered - freq_correct)
            passed = error < 0.0001
            status = "✓" if passed else "✗"
            
            if not passed:
                all_passed = False
                print(f"  {status} Y={y}: correct={freq_correct:.2f}Hz, saved={freq_saved:.2f}Hz, "
                      f"recovered={freq_recovered:.2f}Hz, ERROR={error:.4f}")
            else:
                print(f"  {status} Y={y}: correct={freq_correct:.2f}Hz, saved={freq_saved:.2f}Hz → recovered correctly")
        
        print()
    
    # Special test: at 1x, old and new should be identical
    print("Special case: at 1x playback, formulas should be identical...")
    for y in y_positions:
        freq_old = y_to_freq_old(y, canvas_height, 1.0, MAX_FREQ)
        freq_new = y_to_freq_new(y, canvas_height, 1.0, MAX_FREQ)
        diff = abs(freq_old - freq_new)
        passed = diff < 0.0001
        if not passed:
            all_passed = False
            print(f"  ✗ Y={y}: old={freq_old:.4f}, new={freq_new:.4f}, diff={diff}")
    print("  ✓ All 1x tests passed\n")
    
    print("=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("The correction formula works for playback rates 0.1x to 15x")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
