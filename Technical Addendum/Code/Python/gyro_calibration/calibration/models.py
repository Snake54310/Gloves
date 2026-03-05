
import numpy as np

def apply_transform(omega, A, b):
    return (A @ omega.T).T + b