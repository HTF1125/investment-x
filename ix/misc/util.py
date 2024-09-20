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
