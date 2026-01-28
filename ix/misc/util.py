import pandas as pd


def update_df(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    # Step 1: Create a combined index and columns set
    combined_index = df1.index.union(df2.index)
    combined_columns = df1.columns.union(df2.columns)
    # Step 2: Reindex the original DataFrame
    df1_reindexed = df1.reindex(index=combined_index, columns=combined_columns)
    # Step 3: Update the reindexed DataFrame with the new DataFrame
    df1_reindexed.update(df2)
    return df1_reindexed


# Function to recursively find all subclasses of a class
def all_subclasses(cls):
    subclasses = []
    for subclass in cls.__subclasses__():
        subclasses.append(subclass)
        subclasses.extend(all_subclasses(subclass))
    return subclasses


import numpy as np


def ContributionToGrowth(
    df: pd.DataFrame,
    period: int = 12,
) -> pd.DataFrame:
    """
    각 컬럼(구성 요소)이 전체 합계(Total)의 성장에 얼마나 기여했는지 계산하는 함수.

    Formula:
        Contribution_i = (Value_i,t - Value_i,t-p) / Total_t-p

    Args:
        df (pd.DataFrame): 구성 요소들로 이루어진 데이터프레임 (숫자형 데이터만 포함 권장)
                           * Date 컬럼이 있다면 index로 설정 후 넘겨주세요.
        period (int): 비교할 기간 (예: 12 = 12개월 전 대비 기여도, YoY)

    Returns:
        pd.DataFrame: 기여도(%p) 데이터프레임.
                      각 행의 합(Sum)은 전체 총합의 성장률과 일치합니다.
    """
    # 1. 데이터프레임 내 숫자형 컬럼만 선택 (날짜/문자열 컬럼 제외)
    numeric_df = df.select_dtypes(include=[np.number])

    # 2. 전체 합계(Total) 계산 (분모로 사용됨)
    # 가정: 입력된 df의 모든 컬럼이 Total을 구성하는 요소라고 가정
    total_series = numeric_df.sum(axis=1)

    # 3. '이전 시점'의 Total 값 구하기 (Lagged Total)
    prev_total = total_series.shift(period)

    # 4. 각 컬럼의 '변동폭(Delta)' 계산 (현재 값 - 이전 값)
    delta_df = numeric_df.diff(period)

    # 5. 기여도 계산 (변동폭 / 이전 시점의 Total)
    # axis=0을 사용하여 각 컬럼을 prev_total 시리즈로 나눔
    contribution_df = delta_df.div(prev_total, axis=0) * 100

    return contribution_df
