#!/usr/bin/env python3
"""
Generate volcano/magma themed word cloud from participant feature descriptions.
Black background with red -> orange -> bright yellow gradient.
Bigger words get brighter colors (yellow), smaller words are red.

Generates TWO versions:
  1. Mixed orientation (horizontal + vertical words)
  2. Horizontal only (all words horizontal)

Requires: pip install wordcloud matplotlib
"""

from pathlib import Path
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image, ImageDraw

# ============================================================================
# EDIT THIS SECTION TO CUSTOMIZE EXCLUDED WORDS
# ============================================================================
# Add or remove words from this list to control what appears in the word cloud
CUSTOM_STOPWORDS = [
    # Common words to exclude
    'like', 'doesn', 'doesn\'t', 'comes', 'don', 't', 's', 'aren', 'aren\'t', 'semi', 'two', 'theres',

    # Generic/filler words to exclude
    'sounds', 'soudns', 'towards', 'away', 'series', 'present', 'end', 'overall',
    'tell', 'reselect', 'means', 'look', 'odd', 'sidestick', 'lots',
    'coming', 'kind', 'go', 'first', 'work', 'weak', 'single',
    'earlier', 'noticed', 'something', 'eq', 'selection', 'data',

    # Domain-specific words to exclude
    'event', 'frequency', 'frequencies', 'high', 'low', 'sound', 'more',
    'time', 'half', 'spectrogram', 'spectrogrogram', 'recording',

    # Add more words here to exclude them:
    # 'example', 'another', 'word',
]

# Standard English stopwords (you can comment out if you want to include some)
STANDARD_STOPWORDS = [
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
    'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
    'to', 'was', 'will', 'with', 'this', 'but', 'they', 'have', 'had',
    'what', 'when', 'where', 'who', 'which', 'why', 'how', 'all', 'each',
    'she', 'or', 'other', 'some', 'such', 'no', 'not', 'only', 'own',
    'than', 'too', 'very', 'can', 'just', 'should', 'now', 'my', 'me',
    'i', 'you', 'your', 'we', 'our', 'us', 'them', 'their', 'his', 'her',
    'am', 'been', 'being', 'do', 'does', 'did', 'doing', 'would', 'could',
    'might', 'must', 'shall', 'may', 'here', 'there', 'then', 'these',
    'those', 'any', 'both', 'same', 'so', 'out', 'over', 'under', 'up',
    'down', 'off', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'into', 'onto', 'about', 'against', 'among', 'if', 'because',
    'while', 'until', 'unless', 'since', 'though', 'although', 'whether',
    'nor', 'either', 'neither', 'yet', 'still', 'also', 'even', 'ever',
    'never', 'already', 'again', 'once', 'always', 'often', 'sometimes',
    'usually',
]

# Combine all stopwords
stopwords = set(CUSTOM_STOPWORDS + STANDARD_STOPWORDS)
# ============================================================================

# Read the text blob
text_file = Path(__file__).parent / 'word cloud' / 'feature_descriptions_blob.txt'
with open(text_file, 'r') as f:
    text = f.read()

# Fix typos/combine variants - replace misspellings with correct spelling
# This makes them count together in word frequency
text = text.replace('metall', 'metal')  # Combine metall -> metal
text = text.replace('snapps', 'snaps')  # Combine snapps -> snaps
text = text.replace('kracking', 'cracking')  # Combine kracking -> cracking

print("=" * 80)
print(f"VOLCANO-THEMED WORD CLOUD GENERATOR")
print("=" * 80)
print(f"Source text: {len(text)} characters")
print(f"Excluded words: {len(stopwords)} total")
print()

# Create custom colormap: red -> orange -> bright yellow
# For volcano/magma theme
# Reversed so bigger/frequent words get yellow (hot), smaller/rare words get red
colors = [
    '#FFFF00',  # Bright yellow (bigger words)
    '#FFCC00',  # Yellow-orange
    '#FF9900',  # Orange-yellow
    '#FF6600',  # Orange
    '#FF3300',  # Red-orange
    '#CC0000',  # Bright red (smaller words)
]
n_bins = 100
cmap = LinearSegmentedColormap.from_list('volcano', colors, N=n_bins)

# ============================================================================
# CREATE OVAL/ELLIPSE MASK (optional - comment out for rectangle)
# ============================================================================
def create_ellipse_mask(width, height):
    """Create an ellipse/oval mask for the word cloud"""
    mask = Image.new('L', (width, height), 255)  # White background (no words)
    draw = ImageDraw.Draw(mask)
    # Draw black ellipse (words will fill this area)
    draw.ellipse([0, 0, width, height], fill=0)
    return np.array(mask)

def create_volcano_mask(width, height):
    """Create a volcano shape mask (trapezoid/mountain with flat top)"""
    mask = Image.new('L', (width, height), 255)  # White background (no words)
    draw = ImageDraw.Draw(mask)

    # Draw volcano shape (trapezoid - narrow at top, wide at bottom) - MAXIMUM SIZE!
    center_x = width // 2
    top_y = 20              # Very close to top
    bottom_y = height - 20  # Very close to bottom
    top_width = 200         # Narrower top (crater area)
    base_width = 950        # Very wide base

    # Volcano outline (filled black trapezoid for words)
    volcano_points = [
        (center_x - top_width, top_y),      # Top left
        (center_x + top_width, top_y),      # Top right
        (center_x + base_width, bottom_y),  # Bottom right
        (center_x - base_width, bottom_y),  # Bottom left
    ]
    draw.polygon(volcano_points, fill=0)

    return np.array(mask)

# Generate the masks
oval_mask = create_ellipse_mask(1920, 1080)
volcano_mask = create_volcano_mask(1920, 1080)

# Common word cloud settings
common_settings = {
    'width': 1920,
    'height': 1080,
    'background_color': 'black',
    'stopwords': stopwords,
    'colormap': cmap,
    'max_words': 100,
    'relative_scaling': 0.5,   # Controls size variance (0.0-1.0). Try: 0.5, 0.7, 0.9
    'min_font_size': 13,       # Make smallest words readable
    'max_font_size': 160,      # Cap the largest words
    'random_state': 42,        # FIXED SEED = same layout every time (change number for different layout)
}

# ============================================================================
# VERSION 1: MIXED ORIENTATION (horizontal + vertical) - COMMENTED OUT
# ============================================================================
# print("Creating VERSION 1: Mixed orientation (70% horizontal, 30% vertical)...")
# wordcloud_mixed = WordCloud(
#     **common_settings,
#     prefer_horizontal=0.7  # 70% horizontal, 30% vertical
# ).generate(text)

# plt.figure(figsize=(19.2, 10.8))
# plt.imshow(wordcloud_mixed, interpolation='bilinear')
# plt.axis('off')
# plt.tight_layout(pad=0)

# output_mixed = Path(__file__).parent / 'feature_wordcloud_volcano_mixed.png'
# plt.savefig(output_mixed, dpi=300, bbox_inches='tight', facecolor='black')
# plt.close()
# print(f"✓ Saved to: {output_mixed}")

# ============================================================================
# VERSION 2: HORIZONTAL ONLY (RECTANGLE)
# ============================================================================
print()
print("Creating VERSION 2: Horizontal only - Rectangle...")
wordcloud_horizontal = WordCloud(
    **common_settings,
    prefer_horizontal=1.0  # 100% horizontal
).generate(text)

plt.figure(figsize=(19.2, 10.8))
plt.imshow(wordcloud_horizontal, interpolation='bilinear')
plt.axis('off')
plt.tight_layout(pad=0)

output_horizontal = Path(__file__).parent / 'word cloud' / 'feature_wordcloud_volcano_horizontal.png'
plt.savefig(output_horizontal, dpi=300, bbox_inches='tight', facecolor='black')
plt.close()
print(f"✓ Saved to: {output_horizontal}")

# ============================================================================
# VERSION 3: HORIZONTAL ONLY (OVAL)
# ============================================================================
print()
print("Creating VERSION 3: Horizontal only - Oval...")
wordcloud_oval = WordCloud(
    **common_settings,
    mask=oval_mask,        # Apply oval mask
    prefer_horizontal=1.0  # 100% horizontal
).generate(text)

plt.figure(figsize=(19.2, 10.8))
plt.imshow(wordcloud_oval, interpolation='bilinear')
plt.axis('off')
plt.tight_layout(pad=0)

output_oval = Path(__file__).parent / 'word cloud' / 'feature_wordcloud_volcano_horizontal_oval.png'
plt.savefig(output_oval, dpi=300, bbox_inches='tight', facecolor='black')
plt.close()
print(f"✓ Saved to: {output_oval}")

# ============================================================================
# VERSION 4: HORIZONTAL ONLY (VOLCANO SHAPE)
# ============================================================================
print()
print("Creating VERSION 4: Horizontal only - Volcano shape...")
wordcloud_volcano_shape = WordCloud(
    **common_settings,
    mask=volcano_mask,     # Apply volcano mask
    prefer_horizontal=1.0  # 100% horizontal
).generate(text)

plt.figure(figsize=(19.2, 10.8))
plt.imshow(wordcloud_volcano_shape, interpolation='bilinear')
plt.axis('off')
plt.tight_layout(pad=0)

output_volcano = Path(__file__).parent / 'word cloud' / 'feature_wordcloud_volcano_horizontal_volcano.png'
plt.savefig(output_volcano, dpi=300, bbox_inches='tight', facecolor='black')
plt.close()
print(f"✓ Saved to: {output_volcano}")

# Print summary
print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Words in cloud: ~{len(wordcloud_horizontal.words_)}")
print(f"Excluded stopwords: {len(stopwords)} total")
print()
print("Color scheme:")
print("  🔴 Bright Red (small/rare words)")
print("  🟠 Orange (medium frequency)")
print("  🟡 Bright Yellow (large/common words)")
print()
print("Output files:")
print(f"  • {output_horizontal.name} (rectangle)")
print(f"  • {output_oval.name} (oval)")
print(f"  • {output_volcano.name} (volcano shape)")
print()
print("✓ Done! Word clouds generated.")
print()
print("To exclude more words, edit the CUSTOM_STOPWORDS list at the top of this file.")
