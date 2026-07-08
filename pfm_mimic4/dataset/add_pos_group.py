import numpy as np


def add_position_group(tensor):
    """
    Append a position-group column to a (batch, length, 3) tensor.

    Consecutive events of the same token type (0/1/2) are assigned the same group
    index, so the returned tensor has shape (batch, length, 4).
    """
    batch_size, length, _ = tensor.shape

    A = tensor[:, :, 1]
    B = np.zeros_like(A, dtype=np.int64)

    # The first position always starts a group.
    B[:, 0] = (A[:, 0] == 0) | (A[:, 0] == 1)
    current_val = B[:, 0].copy()

    for i in range(1, length):
        # A new group starts when the token type changes to 0, 1 or 2.
        diff = A[:, i] != A[:, i - 1]
        mask = diff & ((A[:, i] == 0) | (A[:, i] == 1) | (A[:, i] == 2))
        current_val = current_val + mask.astype(int)
        B[:, i] = current_val

    result = np.concatenate([tensor, B[:, :, np.newaxis]], axis=-1)
    return result
