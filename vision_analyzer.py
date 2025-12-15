"""Vision-based image analysis for format prediction.

Uses simple computer vision techniques to analyze image characteristics
that might predict which format compresses better.
"""

from typing import Dict, Optional, Tuple
from PIL import Image

# Optional numpy (graceful degradation)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def analyze_image_vision(image_path) -> Dict[str, float]:
    """
    Analyze image using simple vision techniques to extract features
    that might predict compression performance.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dictionary of vision-based features
    """
    if not NUMPY_AVAILABLE:
        return {}  # Can't analyze without numpy
    
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if needed (for consistent analysis)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Convert to numpy array
            img_array = np.array(img)
            
            features = {}
            
            # 1. Pixel value variability (variance)
            features.update(_analyze_pixel_variability(img_array))
            
            # 2. Color complexity (k-means clustering)
            features.update(_analyze_color_complexity(img_array))
            
            # 3. Edge density (simple gradient-based)
            features.update(_analyze_edge_density(img_array))
            
            # 4. Texture smoothness
            features.update(_analyze_texture(img_array))
            
            return features
    except Exception:
        # If analysis fails, return empty features
        return {}


def _analyze_pixel_variability(img_array) -> Dict[str, float]:
    """Analyze pixel value variability (variance, std dev)."""
    if not NUMPY_AVAILABLE:
        return {}
    
    features = {}
    
    # Overall variance across all channels
    features['pixel_variance'] = float(np.var(img_array))
    features['pixel_std'] = float(np.std(img_array))
    
    # Per-channel variance
    for i, channel in enumerate(['R', 'G', 'B']):
        channel_data = img_array[:, :, i]
        features[f'{channel}_variance'] = float(np.var(channel_data))
        features[f'{channel}_std'] = float(np.std(channel_data))
    
    # Coefficient of variation (std/mean) - normalized variability
    mean_val = np.mean(img_array)
    if mean_val > 0:
        features['coefficient_of_variation'] = float(features['pixel_std'] / mean_val)
    else:
        features['coefficient_of_variation'] = 0.0
    
    return features


def _analyze_color_complexity(img_array, k: int = 8) -> Dict[str, float]:
    """
    Analyze color complexity using k-means clustering.
    
    Uses a simple k-means to find dominant colors and measure complexity.
    Lower k-means error = fewer distinct colors = simpler image
    
    Args:
        img_array: Image as numpy array
        k: Number of clusters (default: 8, good balance of speed/accuracy)
    """
    if not NUMPY_AVAILABLE:
        return {}
    
    features = {}
    
    try:
        from sklearn.cluster import KMeans
        from sklearn.utils import shuffle
        
        # Reshape to (pixels, channels)
        h, w, c = img_array.shape
        pixels = img_array.reshape(-1, c)
        
        # Sample pixels for faster computation (max 10k pixels)
        max_samples = 10000
        if len(pixels) > max_samples:
            pixels = shuffle(pixels, random_state=0, n_samples=max_samples)
        
        # Run k-means
        kmeans = KMeans(n_clusters=k, random_state=0, n_init=10, max_iter=100)
        kmeans.fit(pixels)
        
        # Calculate metrics
        # Inertia = sum of squared distances to centroids (lower = simpler)
        features['color_complexity'] = float(kmeans.inertia_)
        
        # Number of unique colors (approximate)
        labels = kmeans.labels_
        unique_labels = len(np.unique(labels))
        features['dominant_colors'] = float(unique_labels)
        
        # Average distance to nearest centroid (lower = more uniform)
        distances = np.linalg.norm(pixels - kmeans.cluster_centers_[labels], axis=1)
        features['avg_color_distance'] = float(np.mean(distances))
        
    except ImportError:
        # If sklearn not available, use simpler method
        # Count approximate unique colors
        # Sample pixels
        h, w, c = img_array.shape
        sample_size = min(10000, h * w)
        indices = np.random.choice(h * w, sample_size, replace=False)
        sampled = img_array.reshape(-1, c)[indices]
        
        # Quantize colors to reduce precision
        quantized = (sampled // 32) * 32  # Reduce to ~8 levels per channel
        unique_colors = len(np.unique(quantized.view(np.dtype((np.void, quantized.dtype.itemsize * c)))))
        
        features['color_complexity'] = float(unique_colors)  # Use as proxy
        features['dominant_colors'] = float(unique_colors)
        features['avg_color_distance'] = 0.0  # Can't calculate without k-means
    
    return features


def _analyze_edge_density(img_array) -> Dict[str, float]:
    """
    Analyze edge density using simple gradient-based edge detection.
    More edges = more detail = potentially harder to compress.
    """
    if not NUMPY_AVAILABLE:
        return {}
    
    features = {}
    
    # Convert to grayscale for edge detection
    gray = np.mean(img_array, axis=2).astype(np.float32)
    
    # Simple gradient-based edge detection (Sobel-like)
    # Horizontal gradient
    h_grad = np.abs(np.diff(gray, axis=1, prepend=gray[:, 0:1]))
    # Vertical gradient
    v_grad = np.abs(np.diff(gray, axis=0, prepend=gray[0:1, :]))
    
    # Combined gradient magnitude
    gradient_magnitude = np.sqrt(h_grad**2 + v_grad**2)
    
    # Edge density metrics
    features['edge_density'] = float(np.mean(gradient_magnitude))
    features['edge_variance'] = float(np.var(gradient_magnitude))
    
    # Percentage of "strong" edges (above threshold)
    threshold = np.percentile(gradient_magnitude, 90)  # Top 10% as "strong"
    strong_edges = (gradient_magnitude > threshold).sum()
    features['strong_edge_ratio'] = float(strong_edges / gradient_magnitude.size)
    
    return features


def _analyze_texture(img_array) -> Dict[str, float]:
    """
    Analyze texture smoothness.
    Smoother images (lower local variance) compress better.
    """
    if not NUMPY_AVAILABLE:
        return {}
    
    features = {}
    
    # Convert to grayscale
    gray = np.mean(img_array, axis=2).astype(np.float32)
    
    # Calculate local variance using a simple sliding window
    # (simpler than full texture analysis, but fast)
    h, w = gray.shape
    window_size = min(5, min(h, w) // 10)  # Adaptive window size
    
    if window_size < 3:
        # Image too small for texture analysis
        features['texture_smoothness'] = 0.0
        features['local_variance'] = 0.0
        return features
    
    # Calculate local variance
    local_variances = []
    for i in range(0, h - window_size, window_size):
        for j in range(0, w - window_size, window_size):
            window = gray[i:i+window_size, j:j+window_size]
            local_variances.append(np.var(window))
    
    if local_variances:
        features['local_variance'] = float(np.mean(local_variances))
        # Smoothness = inverse of variance (higher = smoother)
        features['texture_smoothness'] = float(1.0 / (1.0 + features['local_variance']))
    else:
        features['local_variance'] = 0.0
        features['texture_smoothness'] = 0.0
    
    return features


def categorize_vision_features(features: Dict[str, float]) -> Dict[str, str]:
    """
    Categorize vision features into discrete categories for learning.
    
    Args:
        features: Dictionary of vision features
        
    Returns:
        Dictionary of categorized features
    """
    categories = {}
    
    # Pixel variability categories
    if 'pixel_variance' in features:
        var = features['pixel_variance']
        if var < 1000:
            categories['variability'] = 'low'
        elif var < 5000:
            categories['variability'] = 'medium'
        else:
            categories['variability'] = 'high'
    
    # Color complexity categories
    if 'color_complexity' in features:
        complexity = features['color_complexity']
        # Normalize based on typical range (k-means inertia can vary widely)
        if complexity < 100000:
            categories['color_complexity'] = 'simple'
        elif complexity < 500000:
            categories['color_complexity'] = 'medium'
        else:
            categories['color_complexity'] = 'complex'
    
    # Edge density categories
    if 'edge_density' in features:
        edges = features['edge_density']
        if edges < 10:
            categories['edge_density'] = 'low'
        elif edges < 30:
            categories['edge_density'] = 'medium'
        else:
            categories['edge_density'] = 'high'
    
    # Texture categories
    if 'texture_smoothness' in features:
        smooth = features['texture_smoothness']
        if smooth > 0.7:
            categories['texture'] = 'smooth'
        elif smooth > 0.3:
            categories['texture'] = 'medium'
        else:
            categories['texture'] = 'rough'
    
    return categories

