# Format Learning Integration Example

This shows how to integrate the `FormatLearner` into the existing codebase.

## How It Works (Easiest Approach)

1. **Collect statistics automatically** - Just record what happens during normal processing
2. **Store in JSON** - Simple `.image-squisher-stats.json` file
3. **Use predictions later** - Once you have data, predict which format to try first

## Integration Steps

### Step 1: Record Results (in `file_manager.py`)

Add learning after processing each image:

```python
# At top of file_manager.py
from format_learner import FormatLearner

# Global learner instance (or pass it around)
_learner = FormatLearner()

# In process_image(), after determining winner:
def process_image(image_path: Path) -> Tuple[bool, str, int, int]:
    # ... existing code ...
    
    # After determining format_name and final_size:
    # Record result for learning
    try:
        _learner.record_result(
            image_path=image_path,
            winner=format_name,
            original_size=original_size,
            jxl_size=jxl_size,
            webp_size=webp_size
        )
    except Exception:
        pass  # Don't fail if learning fails
    
    return True, format_name, original_size, final_size
```

### Step 2: Use Predictions (Optional - in `processor.py`)

Once you have enough data, you could prioritize one format:

```python
from format_learner import FormatLearner

_learner = FormatLearner()

def convert_image(image_path: Path, temp_dir: Path, original_size: Optional[int] = None):
    # Get prediction
    predicted = _learner.predict_best_format(image_path, original_size)
    
    # If we have a prediction, start that format first
    # (but still do both to verify)
    if predicted == 'jxl':
        # Start JXL first, then WebP
        jxl_thread.start()
        time.sleep(0.1)  # Small delay
        webp_thread.start()
    else:
        # Default: start both simultaneously
        jxl_thread.start()
        webp_thread.start()
```

### Step 3: View Statistics (in `main.py`)

Add a command to show learned statistics:

```python
# Add to main() after processing:
if _learner.stats['total_processed'] > 0:
    print("\n" + "=" * 60)
    print("Learned Statistics:")
    print(_learner.get_statistics_summary())
    _learner.save_stats()  # Final save
```

## What Gets Learned

The system tracks:
- **By original format**: `.png` files → JXL wins 60%, WebP wins 30%
- **By color mode**: `RGBA` images → WebP wins 70%, JXL wins 20%
- **By file size**: Large files (>10MB) → JXL wins 80%
- **By dimensions**: Huge images → JXL wins 75%

## Why This Is "Easiest"

1. ✅ **No ML libraries** - Just counting and simple statistics
2. ✅ **No training phase** - Learns during normal use
3. ✅ **Simple storage** - JSON file, human-readable
4. ✅ **Non-invasive** - Can be added without changing core logic
5. ✅ **Gets better over time** - More images = better predictions
6. ✅ **Optional** - Works even if predictions are wrong (still converts both)

## Example Statistics File

```json
{
  "total_processed": 150,
  "by_original_format": {
    ".png": {
      "jxl": 45,
      "webp": 60,
      "original": 5
    },
    ".jpg": {
      "jxl": 80,
      "webp": 15,
      "original": 5
    }
  },
  "by_color_mode": {
    "RGB": {
      "jxl": 90,
      "webp": 40,
      "original": 10
    },
    "RGBA": {
      "jxl": 20,
      "webp": 50,
      "original": 5
    }
  }
}
```

## Future Enhancements

Once you have data, you could:
- Skip the slower format if prediction is confident enough
- Use predictions to set compression effort levels
- Learn per-user patterns (different users have different image types)

