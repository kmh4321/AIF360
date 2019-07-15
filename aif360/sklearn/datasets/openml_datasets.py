import os

import pandas as pd
from sklearn.datasets import fetch_openml

from aif360.sklearn.datasets.utils import standarize_dataset


# cache location
DATA_HOME_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '..', 'data', 'raw')

def to_dataframe(data):
    """Format an OpenML dataset Bunch as a DataFrame with categorical features
    if needed.

    Args:
        data (Bunch): Dict-like object containing `data`, `feature_names` and,
            optionally, `categories` attributes. Note: `data` should contain
            both X and y data.

    Returns:
        pandas.DataFrame: A DataFrame containing all data, including target,
        with categorical features converted to 'category' dtypes.
    """
    def categorize(item):
        return cats[int(item)] if not pd.isna(item) else item

    df = pd.DataFrame(data['data'], columns=data['feature_names'])
    for col, cats in data['categories'].items():
        df[col] = df[col].apply(categorize).astype('category')

    return df

def fetch_adult(subset='all', data_home=None, binary_race=True, usecols=[],
                dropcols=[], numeric_only=False, dropna=True):
    """Load the Adult Census Income Dataset.

    Binarizes 'race' to 'White' (privileged) or 'Non-white' (unprivileged).
    The other protected attribute is 'sex' ('Male' is privileged and 'Female' is
    unprivileged). The outcome variable is '>50K' (favorable) or '<=50K'
    (unfavorable).

    Args:
        subset ({'train', 'test', or 'all'}, optional): Select the dataset to
            load: 'train' for the training set, 'test' for the test set, 'all'
            for both.
        data_home (string, optional): Specify another download and cache folder
            for the datasets. By default all AIF360 datasets are stored in
            'aif360/sklearn/data/raw' subfolders.
        binary_race (bool, optional): Group all non-white races together.
        usecols (single label or list-like, optional): Feature column(s) to
            keep. All others are dropped.
        dropcols (single label or list-like, optional): Feature column(s) to
            drop.
        numeric_only (bool): Drop all non-numeric feature columns.
        dropna (bool): Drop rows with NAs.

    Returns:
        namedtuple: Tuple containing X, y, and sample_weights for the Adult
        dataset accessible by index or name.

    Examples:
        >>> adult = fetch_adult()
        >>> adult.X.shape
        (45222, 13)

        >>> adult_num = fetch_adult(numeric_only=True)
        >>> adult_num.X.shape
        (48842, 5)
    """
    if subset not in {'train', 'test', 'all'}:
        raise ValueError("subset must be either 'train', 'test', or 'all'; "
                         "cannot be {}".format(subset))
    df = to_dataframe(fetch_openml(data_id=1590, target_column=None,
                                   data_home=data_home or DATA_HOME_DEFAULT))
    if subset == 'train':
        df = df.iloc[16281:]
    elif subset == 'test':
        df = df.iloc[:16281]

    df = df.rename(columns={'class': 'annual-income'})  # more descriptive name
    df['annual-income'] = df['annual-income'].cat.as_ordered()  # '<=50K' < '>50K'

    # binarize protected attributes
    if binary_race:
        df.race = df.race.cat.set_categories(['Non-white', 'White'],
                                             ordered=True).fillna('Non-white')
    df.sex = df.sex.cat.as_ordered()  # 'Female' < 'Male'

    return standarize_dataset(df, protected_attributes=['race', 'sex'],
                              target='annual-income', sample_weight='fnlwgt',
                              usecols=usecols, dropcols=dropcols,
                              numeric_only=numeric_only, dropna=dropna)

def fetch_german(data_home=None, binary_age=True, usecols=[], dropcols=[],
                 numeric_only=False, dropna=True):
    """Load the German Credit Dataset.

    Protected attributes are 'sex' ('male' is privileged and 'female' is
    unprivileged) and 'age' (binarized by default as recommended by
    [#kamiran09]_: `age >= 25` is considered privileged and `age < 25` is
    considered unprivileged; see the `binary_age` flag to keep this continuous).
    The outcome variable is 'good' (favorable) or 'bad' (unfavorable).

    References:
        .. [#kamiran09] F. Kamiran and T. Calders, "Classifying without
           discriminating," 2nd International Conference on Computer,
           Control and Communication, 2009.

    Args:
        data_home (string, optional): Specify another download and cache folder
            for the datasets. By default all AIF360 datasets are stored in
            'aif360/sklearn/data/raw' subfolders.
        binary_age (bool, optional): If `True`, split protected attribute,
            `age`, into 'aged' (privileged) and 'youth' (unprivileged). The
            `age` feature remains continuous.
        usecols (single label or list-like, optional): Column name(s) to keep.
            All others are dropped.
        dropcols (single label or list-like, optional): Column name(s) to drop.
        numeric_only (bool): Drop all non-numeric feature columns.
        dropna (bool): Drop rows with NAs.

    Returns:
        namedtuple: Tuple containing X and y for the German dataset accessible
        by index or name.

    Examples:
        >>> german = fetch_german()
        >>> german.X.shape
        (1000, 21)

        >>> german_num = fetch_german(numeric_only=True)
        >>> german_num.X.shape
        (1000, 7)



        >>> X, y = fetch_german(numeric_only=True)
        >>> y_pred = LogisticRegression().fit(X, y).predict(X)
        >>> disparate_impact_ratio(y, y_pred, prot_attr='age', priv_group=True,
        ... pos_label='good')
        0.9483094846144106

    """
    df = to_dataframe(fetch_openml(data_id=31, target_column=None,
                                   data_home=data_home or DATA_HOME_DEFAULT))

    df = df.rename(columns={'class': 'credit-risk'})  # more descriptive name
    df['credit-risk'] = df['credit-risk'].cat.as_ordered()  # 'bad' < 'good'

    # binarize protected attribute (but not corresponding feature)
    age = (pd.cut(df.age, [0, 25, 100], right=False, labels=['young', 'aged'])
           if binary_age else 'age')

    # Note: marital_status directly implies sex. i.e. 'div/dep/mar' => 'female'
    # and all others => 'male'
    personal_status = df.pop('personal_status').str.split(expand=True)
    personal_status.columns = ['sex', 'marital_status']
    df = df.join(personal_status.astype('category'))
    df.sex = df.sex.cat.as_ordered()  # 'female' < 'male'

    return standarize_dataset(df, protected_attributes=['sex', age],
                              target='credit-risk', usecols=usecols,
                              dropcols=dropcols, numeric_only=numeric_only,
                              dropna=dropna)

def fetch_bank(data_home=None, percent10=False, usecols=[], dropcols='duration',
               numeric_only=False, dropna=False):
    """Load the Bank Marketing Dataset.

    The protected attribute is 'age' (left as continuous). The outcome variable
    is 'yes' or 'no'. TODO: which is favorable?

    Args:
        data_home (string, optional): Specify another download and cache folder
            for the datasets. By default all AIF360 datasets are stored in
            'aif360/sklearn/data/raw' subfolders.
        percent10 (bool, optional): Download the reduced version (10% of data).
        usecols (single label or list-like, optional): Column name(s) to keep.
            All others are dropped.
        dropcols (single label or list-like, optional): Column name(s) to drop.
        numeric_only (bool): Drop all non-numeric feature columns.
        dropna (bool): Drop rows with NAs. Note: this is False by default for
            this dataset.

    Returns:
        namedtuple: Tuple containing X and y for the Bank dataset accessible by
        index or name.

    Examples:
        >>> bank = fetch_bank()
        >>> bank.X.shape
        (45211, 15)

        >>> bank_nona = fetch_bank(dropna=True)
        >>> bank_nona.X.shape
        (7842, 15)

        >>> bank_num = fetch_bank(numeric_only=True)
        >>> bank_num.X.shape
        (45211, 6)
    """
    # TODO: this seems to be an old version
    df = to_dataframe(fetch_openml(data_id=1558 if percent10 else 1461,
                                   data_home=data_home or DATA_HOME_DEFAULT,
                                   target_column=None))
    df.columns = ['age', 'job', 'marital', 'education', 'default', 'balance',
                  'housing', 'loan', 'contact', 'day', 'month', 'duration',
                  'campaign', 'pdays', 'previous', 'poutcome', 'deposit']
    # remap target
    df.deposit = df.deposit.cat.rename_categories({'1': 'no', '2': 'yes'})
    # df.deposit = df.deposit.cat.as_ordered()
    # replace 'unknown' marker with NaN
    df.apply(lambda s: s.cat.remove_categories('unknown', inplace=True)
             if hasattr(s, 'cat') and 'unknown' in s.cat.categories else s)
    return standarize_dataset(df, protected_attributes='age', target='deposit',
                              usecols=usecols, dropcols=dropcols,
                              numeric_only=numeric_only, dropna=dropna)
