from __future__ import annotations

from typing import Sized, Iterable, TypeVar, Generator

import numpy as np
import numpy.typing as npt


_T = TypeVar("_T", bound=np.dtype)
_S = TypeVar("_S")


def moving_average(arr: Iterable[float], window: int = 10) -> npt.NDArray[np.float_]:
    """
    Generates a moving average of arr with the size window.

    Args:
        arr: The array/list the moving average will be applied to.
        window: The size of the moving average

    """
    return np.convolve(arr, np.ones(window), 'valid') / window


def sections(array: npt.ArrayLike[_T], bounds: Iterable[slice]) -> Generator[npt.NDArray[_T]]:
    """
    Divides an array into sections determined by bounds.

    Args:
        array: The list/array to be divided.
        bounds: The bounds of each section.

    Returns:
        A generator yielding each divided section.

    """
    for bound in bounds:
        yield np.array(array[bound])


def to_slices(l1: Iterable, l2: Iterable) -> list[slice]:
    """Converts two lists of indexes into slices.

    Args:
        l1 (Iterable): The list of lower bounds or slice start values
        l2 (Iterable): The list of upper bounds or slice stop values

    Returns:
        list[slice]: Array of slices following `[ l1[0]:l2[0], l1[1]:l2[1], ..., l1[n]:l2[n] ]`
    """
    return list(map(lambda x: slice(*x), zip(l1, l2)))


def normalize_len(arr1: list[_T] | tuple[_T] | npt.NDArray[_T],
                  arr2: list[_S] | tuple[_S] | npt.NDArray[_S]) -> tuple[npt.NDArray[_T], npt.NDArray[_S]]:
    """Ensures two arrays have the same length. Length is normalized to the smaller length.

    Args:
        arr1 (Sized): One of the two arrays.
        arr2 (Sized): The other of the two arrays.

    Returns:
        a tuple of the two normalized arrays formed as (arr1, arr2)
    """
    len1 = len(arr1)
    len2 = len(arr2)

    if len1 > len2:
        arr1 = arr1[:len2 - len1]
    elif len1 < len2:
        arr2 = arr2[:len1 - len2]

    return np.array(arr1), np.array(arr2)


def flatten(it: Iterable[Iterable]) -> list:
    """Flattens a 2d list/array into a 1d list

    Args:
        it (Iterable): The list to be flattened

    Returns:
        list[any]: the resulting 1d list
    """

    result = []

    for part in it:
        result.extend(part)

    return result
