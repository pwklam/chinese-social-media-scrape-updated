import sqlite3
import pandas as pd
import config


def sqlite_to_excel_unnamed_first(
    db_path, excel_path, column_mapping=None, exclude_columns=None
):
    """
    Export SQLite table to Excel
    :param db_path: SQLite database path
    :param excel_path: Export Excel path
    :param column_mapping: dict，columns mapping {"like_count": "Like"}
    :param exclude_columns: list， Exclude columns，such as ["id"]
    """
    if exclude_columns is None:
        exclude_columns = ["id"]
    if column_mapping is None:
        column_mapping = {}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [table[0] for table in cursor.fetchall()]

    if not table_names:
        print("[ERROR] No database tables")
        return

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for table_name in table_names:
            print(f"Processing table: {table_name}")
            df = pd.read_sql_query(f"SELECT * FROM `{table_name}`", conn)

            if df.empty:
                print(f"  [WARN] Table {table_name} is empty, skip")
                continue

            # Exclude custome columns
            cols_to_drop = [col for col in exclude_columns if col in df.columns]
            if cols_to_drop:
                df = df.drop(columns=cols_to_drop)

            # Convert customed column to int
            for col in ['like_count', 'shared_count', 'comment_count']:
                if col in df.columns:
                    # Convert to NaN first, then to 0, finaly to int
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

            # Rename columns
            df = df.rename(columns=column_mapping)

            # Export to Excel
            df.to_excel(writer, sheet_name=table_name, index=False)

    conn.close()
    print(f"[OK] Done! Export excel path: {excel_path}")


if __name__ == "__main__":
    custom_columns = {
        "unnamed": "Unnamed: 0",
        "user_name": "User.name",
        "publication_date": "Publication.date",
        "content": "Content",
        "shared_count": "Share",
        "comment_count": "Comment",
        "like_count": "Like",
        "link1": "Link1",
        "link2": "Link2",
        "content_segmented": "content_segmented",
        "is_agriculture_related": "is_agriculture_related",
        "index_number": "No.",
        "comments": "Comments",
    }

    sqlite_to_excel_unnamed_first(
        db_path=config.db_name,
        excel_path=config.export_excel_path,
        column_mapping=custom_columns,
        exclude_columns=["id"],
    )
