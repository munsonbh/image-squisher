# Format Learning Reporting System

## Overview

The format learning system now includes comprehensive reporting with **specificity and sensitivity metrics** for each feature, plus tracking of **image sets** (by source folder).

## What Gets Tracked

### 1. **Predictions vs Actual Outcomes**
- Every time a prediction is made, it's compared to the actual winner
- Tracks: predicted format, actual format, whether prediction was correct
- Stores feature context for each prediction

### 2. **Image Sets (Source Folders)**
- Images are tracked by their parent directory name
- Accounts for the fact that images come in sets (e.g., first 100 from same art style)
- Helps identify if certain image sets have consistent format preferences

### 3. **Feature-Specific Metrics**
For each feature category (format, color mode, size, dimensions, vision features, source folder):
- **Sensitivity (True Positive Rate)**: When the actual winner is X, how often did we predict X?
- **Specificity (True Negative Rate)**: When the actual winner is NOT X, how often did we predict NOT X?
- **Precision**: When we predict X, how often is it correct?
- **F1 Score**: Harmonic mean of precision and sensitivity

## Report Output

After processing, you'll get:

1. **Console Preview**: First 30 lines of the detailed report
2. **Full Report File**: `format-learning-report.txt` with complete analysis

### Report Contents

```
================================================================================
FORMAT LEARNING DETAILED REPORT
================================================================================
Total images processed: 150

Overall Prediction Accuracy: 72.5% (87/120)

--------------------------------------------------------------------------------
Original Format Analysis
--------------------------------------------------------------------------------

  Category: .png
    Samples: 50
    Distribution: JXL 30.0%, WebP 65.0%, Original 5.0%
    Predicted Winner: webp
    Sensitivity (TPR): 85.0%
    Specificity (TNR): 75.0%
    Precision: 82.5%
    F1 Score: 0.84
    Sample Size: 50

  Category: .jpg
    Samples: 100
    Distribution: JXL 75.0%, WebP 20.0%, Original 5.0%
    Predicted Winner: jxl
    Sensitivity (TPR): 90.0%
    Specificity (TNR): 80.0%
    Precision: 88.5%
    F1 Score: 0.89
    Sample Size: 100

[... similar analysis for each feature type ...]

--------------------------------------------------------------------------------
Summary: Best Predictors
--------------------------------------------------------------------------------
1. Original Format → .jpg: 88.5% accuracy
2. Color Mode → RGB: 85.2% accuracy
3. Source Folder → photos_2024: 82.3% accuracy
[...]
```

## Understanding the Metrics

### Sensitivity (True Positive Rate)
- **High sensitivity** = When JXL actually wins, we usually predict JXL correctly
- Example: 90% sensitivity for ".jpg → JXL" means: when a JPG image's winner is JXL, we correctly predicted JXL 90% of the time

### Specificity (True Negative Rate)
- **High specificity** = When JXL doesn't win, we usually predict something else
- Example: 80% specificity for ".jpg → JXL" means: when a JPG image's winner is NOT JXL, we correctly predicted NOT JXL 80% of the time

### Precision
- **High precision** = When we predict JXL, it's usually correct
- Example: 88.5% precision means: when we predict JXL for a JPG, we're right 88.5% of the time

### F1 Score
- **Balanced metric** combining precision and sensitivity
- Range: 0-1 (higher is better)
- Good for comparing features when one has high precision but low sensitivity (or vice versa)

## Image Sets

The system tracks images by **source folder** (parent directory name) to account for:
- Images from the same source/art style
- Batch processing scenarios
- Potential bias from processing similar images together

This helps identify if:
- Certain folders consistently prefer one format
- Early predictions are biased by image sets
- We need more diverse training data

## Minimum Sample Sizes

Metrics are only calculated when there are:
- **At least 3 samples** for basic statistics
- **At least 5 samples** for prediction accuracy
- **At least 3 samples** for specificity/sensitivity calculations

This prevents misleading metrics from small sample sizes.

## Using the Report

1. **Identify Best Predictors**: Look at the "Summary: Best Predictors" section
2. **Check Feature Quality**: High F1 scores indicate reliable predictors
3. **Find Weak Predictors**: Low sensitivity/specificity suggests the feature isn't useful
4. **Account for Image Sets**: Check if source folder is a strong predictor (might indicate bias)

## Example Use Cases

### Finding Reliable Rules
```
"PNG files → WebP" has:
- Sensitivity: 85% (when WebP wins for PNG, we predict it 85% of the time)
- Specificity: 75% (when WebP doesn't win for PNG, we predict NOT WebP 75% of the time)
- F1: 0.84 (good balance)

→ This is a reliable predictor!
```

### Identifying Weak Features
```
"Small files → JXL" has:
- Sensitivity: 45% (barely better than random)
- Specificity: 50% (essentially random)
- F1: 0.47 (poor)

→ File size alone isn't a good predictor
```

### Detecting Image Set Bias
```
"Source Folder: photos_2024 → JXL" has:
- Very high accuracy (95%)
- But only 20 samples from this folder

→ Might be overfitting to this specific image set
```

## Future Enhancements

Potential improvements:
- Cross-validation to detect overfitting
- Per-folder analysis to identify set-specific patterns
- Confidence intervals for metrics
- Time-series analysis (does accuracy improve over time?)
- Feature importance ranking

