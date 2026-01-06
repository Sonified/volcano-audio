#!/usr/bin/env python3
"""
Generate word cloud from participant feature descriptions.

Requires: pip install wordcloud matplotlib
"""

from pathlib import Path
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Read the text blob
text_file = Path(__file__).parent / 'word cloud' / 'feature_descriptions_blob.txt'
with open(text_file, 'r') as f:
    text = f.read()

print(f"Generating word cloud from {len(text)} characters of text...")

# Custom stopwords to exclude common but not meaningful words
stopwords = {
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
    'usually', 'don', 't', 's', 'doesn'
}

# Generate word cloud
wordcloud = WordCloud(
    width=1600,
    height=900,
    background_color='white',
    stopwords=stopwords,
    colormap='viridis',
    max_words=100,
    relative_scaling=0.5,
    min_font_size=10
).generate(text)

# Create figure
plt.figure(figsize=(16, 9))
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis('off')
plt.tight_layout(pad=0)

# Save the word cloud
output_file = Path(__file__).parent / 'word cloud' / 'feature_wordcloud.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"✓ Saved word cloud to: {output_file}")

# Also create a version with dark background
wordcloud_dark = WordCloud(
    width=1600,
    height=900,
    background_color='black',
    stopwords=stopwords,
    colormap='plasma',
    max_words=100,
    relative_scaling=0.5,
    min_font_size=10
).generate(text)

plt.figure(figsize=(16, 9))
plt.imshow(wordcloud_dark, interpolation='bilinear')
plt.axis('off')
plt.tight_layout(pad=0)

output_file_dark = Path(__file__).parent / 'word cloud' / 'feature_wordcloud_dark.png'
plt.savefig(output_file_dark, dpi=300, bbox_inches='tight')
print(f"✓ Saved dark word cloud to: {output_file_dark}")

print()
print("Done! You can now use these word clouds in your analysis.")
