from common.settings import DB_CHARSET, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER


def is_db_configured():
    return all([DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME])


def _import_pymysql():
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("PyMySQL is required. Run: pip install PyMySQL") from exc

    return pymysql


def get_conn():
    if not is_db_configured():
        raise RuntimeError("Database connection is not configured")

    pymysql = _import_pymysql()
    return pymysql.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset=DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
    )


def fetch_all(sql, params=None):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
    finally:
        conn.close()


def fetch_one(sql, params=None):
    rows = fetch_all(sql, params=params)
    return rows[0] if rows else None





if __name__ == '__main__':
    sql = """
    SELECT subtitle_name AS subtitleName, font_family_url AS fontFamilyUrl
    FROM subtitle
    WHERE type = 0 AND language = 'ZH'
    """
    result = fetch_all(sql)
    con = len(result)
    print(result)
    print(con)
    
   # 调试sql
   # python -m common.db_util