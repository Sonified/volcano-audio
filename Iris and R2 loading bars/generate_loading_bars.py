#!/usr/bin/env python3
"""
Generate elegant loading bar comparison video for R2 vs IRIS
Transparent background, optimized for PowerPoint streaming
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FFMpegWriter
from pathlib import Path
import subprocess

# Set font to Arial for crisp, clean rendering
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.sans-serif'] = ['Arial']

# Load times from captain's log (in seconds)
R2_LOAD_TIME = 0.407  # 407ms
IRIS_LOAD_TIME = 66.575  # 66,575ms

# Video settings
FPS = 30
DURATION = IRIS_LOAD_TIME  # FULL VERSION - complete IRIS download time
WIDTH = 1920
HEIGHT = 430  # Height with balanced padding (60px top and bottom) - MUST BE EVEN for H.264
DPI = 100
GENERATE_FINAL_FRAME = True  # Generate final comparison frame as PNG

# Visual settings - VERY WIDE bars with BORDER
BORDER = 60  # Border padding on all sides - more room for checkmark
BAR_WIDTH = WIDTH - (2 * BORDER)  # Full width minus borders
BAR_HEIGHT = 32  # Shorter bars so checkmark shows better
BAR_SPACING = 120  # More vertical space between bars

# Colors (lava theme)
R2_COLOR = '#FF6B35'      # Bright orange-red for Cloudflare Cache (fast) - fresh lava
IRIS_COLOR = '#B22222'    # Brighter red for IRIS Download (slow) - cooled lava/basalt
TEXT_COLOR = '#FFFFFF'    # White text
BAR_BG_COLOR = '#2a2a2a'  # Dark gray for unfilled portion
BORDER_COLOR = '#1a1a1a'  # Subtle border

# Button colors
BUTTON_NORMAL = '#8899aa'      # Light blue/grey for "Fetch 24h Data"
BUTTON_ACTIVE = '#2a4d6e'      # Dark blue for "Downloading Data"
BUTTON_READY = '#008800'       # Darker green for "Cloudflare Ready"

def draw_final_comparison(ax):
    """Draw the final comparison frame with both bars complete and speedup text"""
    ax.clear()
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, HEIGHT)
    ax.axis('off')

    # Draw subtle border
    border_rect = patches.Rectangle(
        (0, 0), WIDTH, HEIGHT,
        linewidth=2, edgecolor=BORDER_COLOR, facecolor='none',
        zorder=0
    )
    ax.add_patch(border_rect)

    # Position bars with border padding
    bar_left = BORDER
    iris_y = BORDER
    r2_y = iris_y + BAR_HEIGHT + 80

    # === BUTTON (above bars, to the left) ===
    button_width = 380
    button_height = 65
    button_x = bar_left
    button_y = r2_y + BAR_HEIGHT + 100

    button_bg = patches.FancyBboxPatch(
        (button_x, button_y), button_width, button_height,
        boxstyle="round,pad=8",
        linewidth=2,
        edgecolor='#aaaaaa',
        facecolor=BUTTON_READY,  # Green for completed
        alpha=1.0,
        zorder=10
    )
    ax.add_patch(button_bg)

    # Button text
    ax.text(button_x + button_width/2, button_y + button_height/2,
            "Download Complete",
            fontsize=24, color='white', weight='bold',
            ha='center', va='center',
            zorder=11)

    # === R2 BAR (TOP) - COMPLETE ===
    r2_fill = patches.Rectangle(
        (bar_left, r2_y), BAR_WIDTH, BAR_HEIGHT,
        linewidth=2, edgecolor='#555555', facecolor=R2_COLOR, alpha=1.0,
        zorder=2
    )
    ax.add_patch(r2_fill)

    # R2 Label
    ax.text(bar_left, r2_y + BAR_HEIGHT + 8,
            'Cloudflare Cache',
            fontsize=24, color=TEXT_COLOR, weight='bold',
            ha='left', va='bottom',
            zorder=5)

    # R2 Time display
    time_text_bg = patches.Rectangle(
        (bar_left + BAR_WIDTH - 130, r2_y + BAR_HEIGHT + 5),
        125, 35,
        facecolor='black', alpha=0.6,
        zorder=4
    )
    ax.add_patch(time_text_bg)

    ax.text(bar_left + BAR_WIDTH, r2_y + BAR_HEIGHT + 8,
            f'{R2_LOAD_TIME * 1000:.0f}ms',
            fontsize=26, color=R2_COLOR, weight='bold',
            ha='right', va='bottom',
            zorder=5)

    # Green checkmark
    ax.text(bar_left + BAR_WIDTH + 5, r2_y + BAR_HEIGHT,
            '✓',
            fontsize=40, color='#00aa00', weight='bold',
            ha='left', va='bottom',
            fontfamily='DejaVu Sans',
            zorder=5)

    # === IRIS BAR (BOTTOM) - COMPLETE ===
    iris_fill = patches.Rectangle(
        (bar_left, iris_y), BAR_WIDTH, BAR_HEIGHT,
        linewidth=2, edgecolor='#555555', facecolor=IRIS_COLOR, alpha=1.0,
        zorder=2
    )
    ax.add_patch(iris_fill)

    # IRIS Label
    ax.text(bar_left, iris_y + BAR_HEIGHT + 8,
            'IRIS Download',
            fontsize=24, color=TEXT_COLOR, weight='bold',
            ha='left', va='bottom',
            zorder=5)

    # IRIS Time display
    time_text_bg2 = patches.Rectangle(
        (bar_left + BAR_WIDTH - 130, iris_y + BAR_HEIGHT + 5),
        125, 35,
        facecolor='black', alpha=0.6,
        zorder=4
    )
    ax.add_patch(time_text_bg2)

    ax.text(bar_left + BAR_WIDTH, iris_y + BAR_HEIGHT + 8,
            f'{IRIS_LOAD_TIME:.1f}s',
            fontsize=26, color=IRIS_COLOR, weight='bold',
            ha='right', va='bottom',
            zorder=5)

    # Orange checkmark for IRIS completion
    ax.text(bar_left + BAR_WIDTH + 5, iris_y + BAR_HEIGHT,
            '✓',
            fontsize=40, color=IRIS_COLOR, weight='bold',
            ha='left', va='bottom',
            fontfamily='DejaVu Sans',
            zorder=5)

    # === BIG SPEEDUP TEXT IN THE MIDDLE ===
    speedup = IRIS_LOAD_TIME / R2_LOAD_TIME
    text_y = r2_y + BAR_HEIGHT + 50  # Centered above the bars

    ax.text(WIDTH / 2, text_y,
            f'{speedup:.0f}× faster time to playback',
            fontsize=48, color='#00aa00', weight='bold',
            ha='center', va='center',
            zorder=10)

def draw_frame(ax, time_sec, frame_num=0):
    """Draw a single frame on the given axes"""
    ax.clear()
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, HEIGHT)
    ax.axis('off')

    # Draw subtle border
    border_rect = patches.Rectangle(
        (0, 0), WIDTH, HEIGHT,
        linewidth=2, edgecolor=BORDER_COLOR, facecolor='none',
        zorder=0
    )
    ax.add_patch(border_rect)

    # Position bars with border padding
    bar_left = BORDER

    iris_y = BORDER  # IRIS bar at bottom with border
    r2_y = iris_y + BAR_HEIGHT + 80  # R2 bar above - reduced spacing for more even look

    # Calculate progress for each bar
    r2_progress = min(1.0, time_sec / R2_LOAD_TIME) if time_sec > 0 else 0
    iris_progress = min(1.0, time_sec / IRIS_LOAD_TIME) if time_sec > 0 else 0

    # === BUTTON (above bars, to the left) ===
    button_width = 380  # Wider to accommodate larger text
    button_height = 65  # Taller for larger text
    button_x = bar_left
    button_y = r2_y + BAR_HEIGHT + 100  # More compact spacing

    is_first_frame = (frame_num == 0)

    # Button background - changes based on progress
    if is_first_frame:
        button_color = BUTTON_NORMAL
        button_text = "Fetch 24h Data"
    elif r2_progress >= 1.0:
        button_color = BUTTON_READY
        button_text = "Cloudflare Ready"
    else:
        button_color = BUTTON_ACTIVE
        button_text = "Downloading Data"

    button_bg = patches.FancyBboxPatch(
        (button_x, button_y), button_width, button_height,
        boxstyle="round,pad=8",
        linewidth=2,
        edgecolor='#aaaaaa',  # Light grey border
        facecolor=button_color,
        alpha=1.0,
        zorder=10
    )
    ax.add_patch(button_bg)

    # Button text
    ax.text(button_x + button_width/2, button_y + button_height/2,
            button_text,
            fontsize=24, color='white', weight='bold',
            ha='center', va='center',
            zorder=11)

    # === R2 BAR (TOP) ===
    # Background (unfilled)
    r2_bg = patches.Rectangle(
        (bar_left, r2_y), BAR_WIDTH, BAR_HEIGHT,
        linewidth=2, edgecolor='#555555', facecolor=BAR_BG_COLOR, alpha=0.5,
        zorder=1
    )
    ax.add_patch(r2_bg)

    # Filled portion (animates)
    if r2_progress > 0:
        r2_fill = patches.Rectangle(
            (bar_left, r2_y), BAR_WIDTH * r2_progress, BAR_HEIGHT,
            linewidth=0, facecolor=R2_COLOR, alpha=1.0,
            zorder=2
        )
        ax.add_patch(r2_fill)

    # R2 Label (left side, above bar)
    ax.text(bar_left, r2_y + BAR_HEIGHT + 8,
            'Cloudflare Cache',
            fontsize=24, color=TEXT_COLOR, weight='bold',
            ha='left', va='bottom',
            zorder=5)

    # R2 Time display (right side, counting up - STOPS at load time)
    r2_time_ms = min(time_sec, R2_LOAD_TIME) * 1000
    time_text_bg = patches.Rectangle(
        (bar_left + BAR_WIDTH - 130, r2_y + BAR_HEIGHT + 5),
        125, 35,
        facecolor='black', alpha=0.6,
        zorder=4
    )
    ax.add_patch(time_text_bg)

    ax.text(bar_left + BAR_WIDTH, r2_y + BAR_HEIGHT + 8,
            f'{r2_time_ms:.0f}ms',
            fontsize=26, color=R2_COLOR, weight='bold',
            ha='right', va='bottom',
            zorder=5)

    # Green checkmark when Cloudflare finishes
    if r2_progress >= 1.0:
        ax.text(bar_left + BAR_WIDTH + 5, r2_y + BAR_HEIGHT,
                '✓',
                fontsize=40, color='#00aa00', weight='bold',
                ha='left', va='bottom',
                fontfamily='DejaVu Sans',  # Use DejaVu Sans for checkmark support
                zorder=5)

    # === IRIS BAR (BOTTOM) ===
    # Background (unfilled)
    iris_bg = patches.Rectangle(
        (bar_left, iris_y), BAR_WIDTH, BAR_HEIGHT,
        linewidth=2, edgecolor='#555555', facecolor=BAR_BG_COLOR, alpha=0.5,
        zorder=1
    )
    ax.add_patch(iris_bg)

    # Filled portion (animates)
    if iris_progress > 0:
        iris_fill = patches.Rectangle(
            (bar_left, iris_y), BAR_WIDTH * iris_progress, BAR_HEIGHT,
            linewidth=0, facecolor=IRIS_COLOR, alpha=1.0,
            zorder=2
        )
        ax.add_patch(iris_fill)

    # IRIS Label (left side, above bar)
    ax.text(bar_left, iris_y + BAR_HEIGHT + 8,
            'IRIS Download',
            fontsize=24, color=TEXT_COLOR, weight='bold',
            ha='left', va='bottom',
            zorder=5)

    # IRIS Time display (right side, counting up - STOPS at load time)
    iris_time = min(time_sec, IRIS_LOAD_TIME)
    if iris_time < 1:
        time_str = f'{iris_time * 1000:.0f}ms'
    else:
        time_str = f'{iris_time:.1f}s'

    time_text_bg2 = patches.Rectangle(
        (bar_left + BAR_WIDTH - 130, iris_y + BAR_HEIGHT + 5),
        125, 35,
        facecolor='black', alpha=0.6,
        zorder=4
    )
    ax.add_patch(time_text_bg2)

    ax.text(bar_left + BAR_WIDTH, iris_y + BAR_HEIGHT + 8,
            time_str,
            fontsize=26, color=IRIS_COLOR, weight='bold',
            ha='right', va='bottom',
            zorder=5)

def main():
    output_dir = Path(__file__).parent

    print(f"🎬 Generating FULL loading bar video...")
    print(f"   R2 load time: {R2_LOAD_TIME}s ({R2_LOAD_TIME*1000:.0f}ms)")
    print(f"   IRIS load time: {IRIS_LOAD_TIME}s")
    print(f"   Video duration: {DURATION}s at {FPS} FPS")
    print(f"   Resolution: {WIDTH}x{HEIGHT}")

    total_frames = int(DURATION * FPS)

    # Create figure with NO MARGINS - this is critical!
    fig = plt.figure(figsize=(WIDTH/DPI, HEIGHT/DPI), dpi=DPI, facecolor='black')
    ax = fig.add_subplot(111)

    # Remove ALL margins/padding - make content fill entire frame
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # Create MP4 version
    print(f"\n📹 Rendering {DURATION:.1f}s full video ({total_frames} frames)...")
    writer_mp4 = FFMpegWriter(fps=FPS, metadata=dict(artist='Volcano Audio'),
                              codec='libx264', bitrate=5000,
                              extra_args=['-pix_fmt', 'yuv420p'])

    mp4_file = output_dir / 'loading_comparison_FULL.mp4'
    with writer_mp4.saving(fig, str(mp4_file), DPI):
        for frame_num in range(total_frames):
            time_sec = frame_num / FPS

            # Draw on the SAME figure/axes
            draw_frame(ax, time_sec, frame_num=frame_num)
            fig.canvas.draw()  # CRITICAL: Force matplotlib to actually render
            writer_mp4.grab_frame()

            if frame_num % 30 == 0:
                print(f"   Frame {frame_num}/{total_frames} ({time_sec:.1f}s) - R2: {min(100, time_sec/R2_LOAD_TIME*100):.1f}%", end='\r')

    plt.close(fig)

    print(f"\n✅ Silent video saved: {mp4_file}")

    # Add click and bell sounds
    click_file = output_dir / 'ui_click.wav'
    bell_file = output_dir / 'Breath_of_Life_Bell_5.wav'

    print(f"\n🔔 Checking for audio files...")
    print(f"   Click file: {click_file} - exists: {click_file.exists()}")
    print(f"   Bell file: {bell_file} - exists: {bell_file.exists()}")

    if click_file.exists() and bell_file.exists():
        print(f"\n🔔 Adding click at 0s and bell at {R2_LOAD_TIME}s...")
        output_with_audio = output_dir / 'loading_comparison_FULL_with_audio.mp4'

        # Mix click (at 0s) and bell (at 0.407s) into single audio track
        delay_ms = int(R2_LOAD_TIME * 1000)
        cmd = [
            'ffmpeg', '-y',
            '-i', str(mp4_file),           # Input 0: Video
            '-i', str(click_file),         # Input 1: Click sound
            '-i', str(bell_file),          # Input 2: Bell sound
            '-filter_complex',
            f'[1:a]volume=1.5,apad=pad_dur={DURATION}[click];'  # Click: louder, padded
            f'[2:a]volume=0.5,afade=t=out:st=0:d=2,adelay=delays={delay_ms}:all=1,apad=pad_dur={DURATION}[bell];'  # Bell: quieter, faded, delayed
            f'[click][bell]amix=inputs=2:duration=first[audio]',  # Mix both sounds
            '-map', '0:v',                 # Use video from input 0
            '-map', '[audio]',             # Use mixed audio
            '-c:v', 'copy',                # Copy video stream
            '-c:a', 'aac',                 # Encode audio as AAC
            '-shortest',                   # End when shortest stream ends
            str(output_with_audio)
        ]

        print(f"   Running: ffmpeg with click + bell mix")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Video with audio saved: {output_with_audio}")
            print(f"   Click plays at 0s (button press)")
            print(f"   Bell plays at {R2_LOAD_TIME}s (Cloudflare Ready)")
        else:
            print(f"⚠️  Audio merge FAILED:")
            print(f"   STDERR: {result.stderr}")
            print(f"   STDOUT: {result.stdout}")
    else:
        print(f"⚠️  Audio files not found")

    # Generate final comparison frame as PNG
    if GENERATE_FINAL_FRAME:
        print(f"\n📸 Generating final comparison frame...")
        final_frame_file = output_dir / 'final_comparison_frame.png'

        # Create new figure for final frame
        fig_final = plt.figure(figsize=(WIDTH/DPI, HEIGHT/DPI), dpi=DPI, facecolor='black')
        ax_final = fig_final.add_subplot(111)
        fig_final.subplots_adjust(left=0, right=1, top=1, bottom=0)

        # Draw the final comparison
        draw_final_comparison(ax_final)

        # Save as PNG - exact same resolution as video (1920x430)
        fig_final.savefig(str(final_frame_file), dpi=DPI, facecolor='black')
        plt.close(fig_final)

        print(f"✅ Final comparison frame saved: {final_frame_file}")
        print(f"   Resolution: {WIDTH}x{HEIGHT}px (matches video)")
        print(f"   Shows both bars complete with speedup text")

    print(f"\n🎉 Done! Check the video to verify:")
    print(f"   - Bars fill up (R2 fills completely by ~0.4s)")
    print(f"   - Button changes from 'Fetch 24h Data' to 'Downloading Data' on frame 1")
    print(f"   - Time counters tick up on the right")
    print(f"   - Bars go edge-to-edge with {BORDER}px border")
    print(f"   - Video is {HEIGHT}px tall (minimal height)")
    print(f"   - Bell sound plays at {R2_LOAD_TIME}s when R2 completes")
    if GENERATE_FINAL_FRAME:
        print(f"   - Final comparison frame saved as PNG")

if __name__ == '__main__':
    main()
