import time
import os
from typing import Iterator, List, Collection, Callable

import pandas as pd
from tqdm import tqdm

# A very general type hint for a prediction function.
# A prediction function takes a triplet of (test object description, train descriptions, train labels)
# and outputs a bool prediction
PREDICTION_FUNCTION_HINT = Callable[
    [Collection, Collection[Collection], Collection[bool]], bool
]


def load_data(df_name: str) -> pd.DataFrame:
    """Generalized function to load datasets in the form of pandas.DataFrame"""
    if df_name == 'tic_tac_toe':
        return load_tic_tac_toe()
    elif df_name == 'smoking':
        return load_smoking()

    raise ValueError(f'Unknown dataset name: {df_name}')


def load_tic_tac_toe() -> pd.DataFrame:
    """Load tic-tac-toe dataset from UCI repository"""
    column_names = [
        'top-left-square', 'top-middle-square', 'top-right-square',
        'middle-left-square', 'middle-middle-square', 'middle-right-square',
        'bottom-left-square', 'bottom-middle-square', 'bottom-right-square',
        'Class'
    ]
    url = 'https://archive.ics.uci.edu/ml/machine-learning-databases/tic-tac-toe/tic-tac-toe.data'
    df = pd.read_csv(url, names=column_names)
    df['Class'] = [x == 'positive' for x in df['Class']]
    return df

def load_smoking() -> pd.DataFrame:
    """Load smoking dataset from UCI repository"""
    file_path = os.path.expanduser('~/personal/uni/datasets/smoking/smoking.csv')
    df = pd.read_csv(file_path)
    df.drop('ID', inplace=True, axis=1)
    df.rename(columns = {'height(cm)': 'height_cm', 'weight(kg)': 'weight_kg', 'waist(cm)': 'waist_cm', 'eyesight(left)': 'eyesight_left', 'eyesight(right)': 'eyesight_right', 'hearing(left)': 'hearing_left', 'hearing(right)': 'hearing_right', 'fasting blood sugar': 'fasting_blood_sugar', 'Cholesterol': 'cholesterol', 'HDL': 'hdl', 'LDL': 'ldl', 'Urine protein': 'urine_protein', 'serum creatinine': 'serum_creatinine', 'AST': 'ast', 'ALT': 'alt', 'Gtp': 'gtp', 'dental caries': 'dental_caries'}, inplace=True)
    return df


def binarize_X(X: pd.DataFrame) -> 'pd.DataFrame[bool]':
    """Scale values from X into pandas.DataFrame of binary values"""
    X_bin = X.copy(deep=True)
    for f in X_bin.columns:
        if X_bin[f].dtypes == 'int64' or X_bin[f].dtypes == 'float64':
            X_bin[f] = pd.qcut(X_bin[f], q=3, duplicates='drop')
    dummies = [pd.get_dummies(X_bin[f], prefix=f, prefix_sep=': ') for f in X_bin.columns]
    X_bin = pd.concat(dummies, axis=1).astype(bool)
    return X_bin

def predict_with_generators(
        x: set, X_train: List[set], Y_train: List[bool],
        min_cardinality: int = 1
) -> bool:
    """Lazy prediction for ``x`` based on training data ``X_train`` and ``Y_train``
    Parameters
    ----------
    x : set
        Description to make prediction for
    X_train: List[set]
        List of training examples
    Y_train: List[bool]
        List of labels of training examples
    min_cardinality: int
        Minimal size of an intersection required to count for counterexamples
    Returns
    -------
    prediction: bool
        Class prediction for ``x`` (either True or False)
    """
    X_pos = [x_train for x_train, y in zip(X_train, Y_train) if y]
    X_neg = [x_train for x_train, y in zip(X_train, Y_train) if not y]

    n_counters_pos = 0  # number of counter examples for positive intersections
    for x_pos in X_pos:
        intersection_pos = x & x_pos
        if len(intersection_pos) < min_cardinality:  # the intersection is too small
            continue

        for x_neg in X_neg:  # count all negative examples that contain intersection_pos
            if (intersection_pos & x_neg) == intersection_pos:
                n_counters_pos += 1

    n_counters_neg = 0  # number of counter examples for negative intersections
    for x_neg in X_neg:
        intersection_neg = x & x_neg
        if len(intersection_neg) < min_cardinality:
            continue

        for x_pos in X_pos:  # count all positive examples that contain intersection_neg
            if (intersection_neg & x_pos) == intersection_neg:
                n_counters_neg += 1

    perc_counters_pos = n_counters_pos / len(X_pos)
    perc_counters_neg = n_counters_neg / len(X_neg)

    prediction = perc_counters_pos < perc_counters_neg
    return prediction


def predict_array(
        X: List[set], Y: List[bool],
        n_train: int, update_train: bool = True, use_tqdm: bool = False,
        predict_func: PREDICTION_FUNCTION_HINT = predict_with_generators
) -> Iterator[bool]:
    """Predict the labels of multiple examples from ``X``
    Parameters
    ----------
    X: List[set]
        Set of train and test examples to classify represented with subsets of attributes
    Y: List[bool]
        Set of train and test labels for each example from X
    n_train: int
        Initial number of train examples. That is, make predictions only for examples from X_train[n_train:]
    update_train: bool
        A flag whether to consider true labels of predicted examples as training data or not.
        If True, then for each X_i the training data consists of X_1, X_2, ..., X_{n_train}, ...,  X_{i-1}.
        If False, then for each X_i the training data consists of X_1, X_2, ..., X_{n_train}
    use_tqdm: bool
        A flag whether to use tqdm progress bar (in case you like progress bars)
    predict_func: <see PREDICTION_FUNCTION_HINT defined in this file>
        A function to make prediction for each specific example from ``X``.
        The default prediction function is ``predict_with_generator`` (considered as baseline for the home work).
    Returns
    -------
    prediction: Iterator
        Python generator with predictions for each x in X[n_train:]
    """
    for i, x in tqdm(
        enumerate(X[n_train:]),
        initial=n_train, total=len(X),
        desc='Predicting step by step',
        disable=not use_tqdm,
    ):
        n_trains = n_train + i if update_train else n_train
        yield predict_func(x, X[:n_trains], Y[:n_trains])


def apply_stopwatch(iterator: Iterator):
    """Measure run time of each iteration of ``iterator``
    The function can be applied e.g. for the output of ``predict_array`` function
    """
    outputs = []
    times = []

    t_start = time.time()
    for out in iterator:
        dt = time.time() - t_start
        outputs.append(out)
        times.append(dt)
        t_start = time.time()

    return outputs, times
