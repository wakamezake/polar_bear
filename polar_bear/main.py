import numpy as np
import pandas as pd
import optuna
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

int_dtype_list = ['int8', 'int16', 'int32',
                  'int64', 'uint8', 'uint16', 'uint32', 'uint64']
float_dtype_list = ['float16', 'float32', 'float64', 'float128']


def _target_data(train_df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """Get target column and data from train data

    Extended description of function.

    Parameters
    ----------
    train_df : pd.DataFrame
        train data
    target_col : str
        target column name

    Returns
    -------
    pd.DataFrame

    >>> import pandas as pd
    >>> data = pd.DataFrame({"param": [1, 2, 3], "target": [1, 0, 1]})
    >>> _target_data(data, "target")
       y1:target
    0          1
    1          0
    2          1
    """
    target_df = pd.DataFrame()
    target_df["y1:" + target_col] = train_df[target_col]
    return target_df


def _make_return_df(train_df, test_df, threshold_one_hot):
    return_df = pd.DataFrame()
    rows_count = len(train_df) + len(test_df)
    feature_column_index = 1

    for label, content in train_df.iteritems():
        content = pd.concat([content, test_df[label]])
        dtype = content.dtype

        value_counts = content.value_counts()
        value_counts_number = value_counts.shape[0]

        if value_counts_number == 1:
            continue

        if dtype in int_dtype_list:
            if value_counts_number < (rows_count * threshold_one_hot):
                mode_value = value_counts.index[0]
                content[np.isnan(content)] = mode_value
                one_hot_df = pd.get_dummies(content, prefix=label)
                for one_hot_label, one_hot_content in one_hot_df.iteritems():
                    return_df["x" + str(feature_column_index) +
                              ":" + one_hot_label] = one_hot_content
                    feature_column_index += 1
        elif dtype in float_dtype_list:
            if value_counts_number < (rows_count * threshold_one_hot):
                mode_value = content.value_counts().index[0]
                content[np.isnan(content)] = mode_value
                one_hot_df = pd.get_dummies(content, prefix=label)
                for one_hot_label, one_hot_content in one_hot_df.iteritems():
                    return_df["x" + str(feature_column_index) +
                              ":" + one_hot_label] = one_hot_content
                    feature_column_index += 1
            else:
                mean = content.mean()
                content[np.isnan(content)] = mean
                return_df["x" + str(feature_column_index) +
                          ":" + label + "_float"] = content
                feature_column_index += 1
        elif (dtype == 'object') or (dtype == 'bool'):
            if value_counts_number < (rows_count * threshold_one_hot):
                mode_value = content.value_counts().index[0]
                content[pd.isnull(content)] = mode_value
                one_hot_df = pd.get_dummies(content, prefix=label)
                for one_hot_label, one_hot_content in one_hot_df.iteritems():
                    return_df["x" + str(feature_column_index) +
                              ":" + one_hot_label] = one_hot_content
                    feature_column_index += 1

    return return_df


def _wrapper_objective(train_df, target_df, test_df):
    target_dtype = target_df.dtypes[0]
    if target_dtype in float_dtype_list:
        if target_df.iloc[:, 0].value_counts().shape[0] < 10:
            rf = RandomForestClassifier()
        else:
            rf = RandomForestRegressor()
    else:
        rf = RandomForestClassifier()

    def objective(trial):
        threshold_one_hot = trial.suggest_discrete_uniform(
            'threshold_one_hot', 0.0, 1.0, 0.01)
        return_df = _make_return_df(train_df, test_df, threshold_one_hot)
        X_train, X_test, y_train, y_test = train_test_split(
            return_df[0:len(train_df)].values, target_df.iloc[:, 0].values, test_size=0.2, random_state=0)
        rf.fit(X_train, y_train)
        y_pred = rf.predict(X_test)
        print(y_pred)
        return 1.0 - accuracy_score(y_test, y_pred)
    return objective


def clean(train_df, test_df, target_col, threshold_one_hot=None):
    target_df = _target_data(train_df, target_col)
    del train_df[target_col]

    if threshold_one_hot is None:
        study = optuna.create_study()
        study.optimize(_wrapper_objective(train_df, target_df, test_df), 100)
        return_df = _make_return_df(
            train_df, test_df, study.best_params['threshold_one_hot'])
    else:
        return_df = _make_return_df(train_df, test_df, threshold_one_hot)

    return return_df[0:len(train_df)], target_df, return_df[len(train_df):]
