"""Simple statistics-based learning system for format prediction."""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple
from collections import defaultdict
from PIL import Image

# Optional vision analysis (graceful degradation if not available)
try:
    from vision_analyzer import analyze_image_vision, categorize_vision_features
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False


class FormatLearner:
    """
    Simple learning system that tracks which format wins for different image characteristics.
    Uses basic statistics (no ML) to make predictions.
    """
    
    def __init__(self, stats_file: Optional[Path] = None):
        """
        Initialize the format learner.
        
        Args:
            stats_file: Path to JSON file for storing statistics (default: .image-squisher-stats.json)
        """
        if stats_file is None:
            stats_file = Path('.image-squisher-stats.json')
        self.stats_file = stats_file
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict:
        """Load statistics from file, or return empty stats if file doesn't exist."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, start fresh
                return self._empty_stats()
        return self._empty_stats()
    
    def _empty_stats(self) -> Dict:
        """Return empty statistics structure."""
        return {
            'total_processed': 0,
            'by_original_format': {},  # e.g., {'.png': {'jxl': 10, 'webp': 15, 'original': 2}}
            'by_color_mode': {},       # e.g., {'RGB': {'jxl': 20, 'webp': 10}}
            'by_size_category': {},    # e.g., {'small': {'jxl': 5, 'webp': 8}}
            'by_dimensions': {},       # e.g., {'large': {'jxl': 12, 'webp': 5}}
            'by_vision_features': {},  # e.g., {'low_variability': {'jxl': 5, 'webp': 3}}
        }
    
    def _save_stats(self):
        """Save statistics to file."""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except IOError:
            # If we can't save, just continue (non-critical)
            pass
    
    def _get_size_category(self, file_size: int) -> str:
        """Categorize file size."""
        if file_size < 100_000:  # < 100 KB
            return 'tiny'
        elif file_size < 500_000:  # < 500 KB
            return 'small'
        elif file_size < 2_000_000:  # < 2 MB
            return 'medium'
        elif file_size < 10_000_000:  # < 10 MB
            return 'large'
        else:
            return 'huge'
    
    def _get_dimension_category(self, width: int, height: int) -> str:
        """Categorize image dimensions."""
        pixels = width * height
        if pixels < 100_000:  # < 100K pixels
            return 'tiny'
        elif pixels < 500_000:  # < 500K pixels
            return 'small'
        elif pixels < 2_000_000:  # < 2M pixels
            return 'medium'
        elif pixels < 10_000_000:  # < 10M pixels
            return 'large'
        else:
            return 'huge'
    
    def record_result(
        self,
        image_path: Path,
        winner: str,  # 'jxl', 'webp', or 'original'
        original_size: int,
        jxl_size: Optional[int],
        webp_size: Optional[int]
    ):
        """
        Record the result of processing an image.
        
        Args:
            image_path: Path to the processed image
            winner: Which format won ('jxl', 'webp', or 'original')
            original_size: Original file size in bytes
            jxl_size: Size of JXL conversion (None if failed)
            webp_size: Size of WebP conversion (None if failed)
        """
        try:
            # Get image characteristics
            with Image.open(image_path) as img:
                color_mode = img.mode
                width, height = img.size
        except Exception:
            # If we can't read image, skip learning for this one
            return
        
        original_format = image_path.suffix.lower()
        size_cat = self._get_size_category(original_size)
        dim_cat = self._get_dimension_category(width, height)
        
        # Update statistics
        self.stats['total_processed'] += 1
        
        # By original format
        if original_format not in self.stats['by_original_format']:
            self.stats['by_original_format'][original_format] = {'jxl': 0, 'webp': 0, 'original': 0}
        self.stats['by_original_format'][original_format][winner] += 1
        
        # By color mode
        if color_mode not in self.stats['by_color_mode']:
            self.stats['by_color_mode'][color_mode] = {'jxl': 0, 'webp': 0, 'original': 0}
        self.stats['by_color_mode'][color_mode][winner] += 1
        
        # By size category
        if size_cat not in self.stats['by_size_category']:
            self.stats['by_size_category'][size_cat] = {'jxl': 0, 'webp': 0, 'original': 0}
        self.stats['by_size_category'][size_cat][winner] += 1
        
        # By dimensions
        if dim_cat not in self.stats['by_dimensions']:
            self.stats['by_dimensions'][dim_cat] = {'jxl': 0, 'webp': 0, 'original': 0}
        self.stats['by_dimensions'][dim_cat][winner] += 1
        
        # By vision features (if available)
        if VISION_AVAILABLE:
            try:
                vision_features = analyze_image_vision(image_path)
                vision_categories = categorize_vision_features(vision_features)
                
                # Track by each vision category
                for feature_name, category_value in vision_categories.items():
                    key = f"{feature_name}_{category_value}"
                    if key not in self.stats['by_vision_features']:
                        self.stats['by_vision_features'][key] = {'jxl': 0, 'webp': 0, 'original': 0}
                    self.stats['by_vision_features'][key][winner] += 1
            except Exception:
                # If vision analysis fails, just skip it
                pass
        
        # Save periodically (every 10 images to avoid too much I/O)
        if self.stats['total_processed'] % 10 == 0:
            self._save_stats()
    
    def predict_best_format(
        self,
        image_path: Path,
        original_size: int
    ) -> Optional[str]:
        """
        Predict which format is likely to win based on learned statistics.
        
        Args:
            image_path: Path to the image
            original_size: Original file size in bytes
            
        Returns:
            'jxl', 'webp', or None (if not enough data or no clear winner)
        """
        try:
            with Image.open(image_path) as img:
                color_mode = img.mode
                width, height = img.size
        except Exception:
            return None
        
        original_format = image_path.suffix.lower()
        size_cat = self._get_size_category(original_size)
        dim_cat = self._get_dimension_category(width, height)
        
        # Collect votes from different characteristics
        votes = {'jxl': 0, 'webp': 0}
        
        # Vote by original format
        if original_format in self.stats['by_original_format']:
            fmt_stats = self.stats['by_original_format'][original_format]
            total = fmt_stats['jxl'] + fmt_stats['webp']
            if total >= 3:  # Need at least 3 samples
                if fmt_stats['jxl'] > fmt_stats['webp']:
                    votes['jxl'] += 2  # Strong vote
                elif fmt_stats['webp'] > fmt_stats['jxl']:
                    votes['webp'] += 2
        
        # Vote by color mode
        if color_mode in self.stats['by_color_mode']:
            mode_stats = self.stats['by_color_mode'][color_mode]
            total = mode_stats['jxl'] + mode_stats['webp']
            if total >= 3:
                if mode_stats['jxl'] > mode_stats['webp']:
                    votes['jxl'] += 1
                elif mode_stats['webp'] > mode_stats['jxl']:
                    votes['webp'] += 1
        
        # Vote by size category
        if size_cat in self.stats['by_size_category']:
            size_stats = self.stats['by_size_category'][size_cat]
            total = size_stats['jxl'] + size_stats['webp']
            if total >= 3:
                if size_stats['jxl'] > size_stats['webp']:
                    votes['jxl'] += 1
                elif size_stats['webp'] > size_stats['jxl']:
                    votes['webp'] += 1
        
        # Vote by dimensions
        if dim_cat in self.stats['by_dimensions']:
            dim_stats = self.stats['by_dimensions'][dim_cat]
            total = dim_stats['jxl'] + dim_stats['webp']
            if total >= 3:
                if dim_stats['jxl'] > dim_stats['webp']:
                    votes['jxl'] += 1
                elif dim_stats['webp'] > dim_stats['jxl']:
                    votes['webp'] += 1
        
        # Vote by vision features (if available)
        if VISION_AVAILABLE and 'by_vision_features' in self.stats:
            try:
                vision_features = analyze_image_vision(image_path)
                vision_categories = categorize_vision_features(vision_features)
                
                # Each vision category gets a vote
                for feature_name, category_value in vision_categories.items():
                    key = f"{feature_name}_{category_value}"
                    if key in self.stats['by_vision_features']:
                        vision_stats = self.stats['by_vision_features'][key]
                        total = vision_stats['jxl'] + vision_stats['webp']
                        if total >= 3:
                            if vision_stats['jxl'] > vision_stats['webp']:
                                votes['jxl'] += 1
                            elif vision_stats['webp'] > vision_stats['jxl']:
                                votes['webp'] += 1
            except Exception:
                # If vision analysis fails, just skip it
                pass
        
        # Return winner if there's a clear preference (at least 2 votes difference)
        if votes['jxl'] > votes['webp'] + 1:
            return 'jxl'
        elif votes['webp'] > votes['jxl'] + 1:
            return 'webp'
        
        return None  # Not enough data or tie
    
    def get_statistics_summary(self) -> str:
        """Get a human-readable summary of learned statistics."""
        if self.stats['total_processed'] == 0:
            return "No statistics collected yet."
        
        lines = [f"Total images processed: {self.stats['total_processed']}", ""]
        
        # By original format
        if self.stats['by_original_format']:
            lines.append("By original format:")
            for fmt, counts in sorted(self.stats['by_original_format'].items()):
                total = counts['jxl'] + counts['webp'] + counts['original']
                if total > 0:
                    jxl_pct = (counts['jxl'] / total * 100) if total > 0 else 0
                    webp_pct = (counts['webp'] / total * 100) if total > 0 else 0
                    orig_pct = (counts['original'] / total * 100) if total > 0 else 0
                    lines.append(f"  {fmt}: JXL {jxl_pct:.1f}%, WebP {webp_pct:.1f}%, Original {orig_pct:.1f}% (n={total})")
            lines.append("")
        
        return "\n".join(lines)
    
    def save_stats(self):
        """Manually save statistics (called at end of processing)."""
        self._save_stats()

