def fit_font_size(text: str, box_width: float, initial_size: float, measure) -> float:
    size = initial_size
    while size > 4 and measure(text, size) > box_width:
        size -= 0.5
    return size
