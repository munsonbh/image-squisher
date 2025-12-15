# Experimental Features: Format Learning & Vision Analysis

This branch (`experimental/format-learning`) adds experimental features for learning which image format (JPEG XL vs WebP) compresses better for different types of images.

## ⚠️ Experimental Status

These features are **experimental** and may:
- Change or be removed in future versions
- Have performance impacts (vision analysis adds overhead)
- Not work perfectly for all image types

**Use at your own risk!** The core functionality still works normally even if learning fails.

## What's New

### 1. Format Learning System (`format_learner.py`)

Automatically learns which format wins for different image characteristics:
- **By original format**: `.png` files → WebP wins 60%, JXL wins 30%
- **By color mode**: `RGBA` images → WebP wins 70%
- **By file size**: Large files (>10MB) → JXL wins 80%
- **By dimensions**: Huge images → JXL wins 75%
- **By vision features**: Low variability images → JXL wins 65%

### 2. Vision Analysis (`vision_analyzer.py`)

Uses simple computer vision to analyze images:
- **Pixel variability**: Variance, standard deviation (more variability = harder to compress)
- **Color complexity**: K-means clustering to find dominant colors (fewer colors = simpler)
- **Edge density**: Gradient-based edge detection (more edges = more detail)
- **Texture smoothness**: Local variance analysis (smoother = compresses better)

## Installation

### Required Dependencies

```bash
pip install numpy>=1.20.0
```

### Optional (Recommended)

For better color complexity analysis using k-means:

```bash
pip install scikit-learn>=1.0.0
```

**Note**: The system works without scikit-learn, but uses a simpler (less accurate) color analysis method.

## How It Works

1. **During Processing**: 
   - Each image is analyzed for vision features
   - Results are recorded (which format won)
   - Statistics are saved to `.image-squisher-stats.json`

2. **Learning**:
   - After ~10-20 images, starts making predictions
   - Uses voting from multiple characteristics
   - Predictions improve over time

3. **Statistics Display**:
   - At end of processing, shows learned statistics
   - Example: "PNG files: JXL 45%, WebP 60%, Original 5%"

## Vision Features Explained

### Pixel Variability
- **High variance** = lots of color variation = potentially harder to compress
- **Low variance** = uniform colors = compresses well

### Color Complexity (K-means)
- **Few dominant colors** = simple image = compresses well
- **Many colors** = complex image = harder to compress
- Uses k-means clustering (k=8) to find dominant colors

### Edge Density
- **Many edges** = lots of detail = potentially harder to compress
- **Few edges** = smooth image = compresses well
- Uses simple gradient-based edge detection

### Texture Smoothness
- **Smooth texture** = uniform areas = compresses well
- **Rough texture** = high local variance = harder to compress

## Performance Impact

- **Vision analysis**: Adds ~50-200ms per image (depending on size)
- **Learning overhead**: Minimal (~1ms per image)
- **Storage**: Statistics file grows slowly (~1KB per 100 images)

## Future Enhancements

Potential improvements:
- Use predictions to skip slower format conversion
- Learn per-user patterns
- More sophisticated vision features (histogram analysis, frequency domain)
- Machine learning models (once enough data collected)

## Disabling Learning

If you want to disable learning (e.g., for performance):

1. Remove/comment out the import in `file_manager.py`
2. Or set `LEARNING_ENABLED = False` in `file_manager.py`

The system will continue to work normally without learning.

## Statistics File

Statistics are stored in `.image-squisher-stats.json` in the current directory.

You can:
- **View it**: `cat .image-squisher-stats.json`
- **Delete it**: `rm .image-squisher-stats.json` (starts fresh)
- **Back it up**: Copy it to keep your learned patterns

## Example Output

```
============================================================
Experimental: Format Learning Statistics
Total images processed: 150

By original format:
  .jpg: JXL 75.0%, WebP 20.0%, Original 5.0% (n=100)
  .png: JXL 30.0%, WebP 65.0%, Original 5.0% (n=50)
```

## Contributing

This is experimental! If you find patterns or want to improve the learning:
- Test on different image types
- Report what works/doesn't work
- Suggest new vision features
- Share statistics files (anonymized)

