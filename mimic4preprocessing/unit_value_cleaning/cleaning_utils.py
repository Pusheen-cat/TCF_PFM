import numpy as np

def trimmed_mean_from_counter(value_counter, lower_q=0.2, upper_q=0.8):
    """
    value_counter: dict[str, int]  (value -> count)
    return: (mean, n_used) or (None, 0)
    """
    values = []

    for v_str, cnt in value_counter.items():
        try:
            v = float(v_str)
        except (ValueError, TypeError):
            continue
        values.extend([v] * cnt)

    if len(values) == 0:
        return np.nan, 0

    values = np.array(values)
    values = values[~np.isnan(values)]

    # 표본이 너무 적으면 trimming 없이 사용
    if len(values) < 10:
        return values.mean(), len(values)

    low = np.quantile(values, lower_q)
    high = np.quantile(values, upper_q)

    trimmed = values[(values >= low) & (values <= high)]

    if len(trimmed) == 0:
        return np.nan, 0

    return trimmed.mean(), len(trimmed)
