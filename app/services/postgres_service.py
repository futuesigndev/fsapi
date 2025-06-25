import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_user_credentials(client_id: str):
    """
    ดึง CLIENT_ID และ CLIENT_SECRET จาก PostgreSQL
    """
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT")
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT client_id, client_secret, id_babi
            FROM fsapi_user
            WHERE client_id = %s
        """, (client_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return {
                "client_id": row[0],
                "client_secret": row[1],
                "id_babi": row[2]
            }
        return None
    except Exception as e:
        raise RuntimeError(f"Failed to fetch user credentials: {e}")


def get_function_names(client_id: str):
    """
    ดึง function_name / function_detail ที่ผูกกับ ID_BABI ของ client
    """
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT")
        )
        cur = conn.cursor()

        # 1. ดึง id_babi
        cur.execute("SELECT id_babi FROM fsapi_user WHERE client_id = %s", (client_id,))
        row = cur.fetchone()
        if not row:
            return []

        # 2. แปลง '1,2' เป็น list [1, 2]
        id_list = [int(x.strip()) for x in row[0].split(",")]

        # 3. Query function จาก fsapi_babi
        cur.execute("""
            SELECT babi AS function_name, detail AS function_detail
            FROM fsapi_babi
            WHERE id = ANY(%s)
            ORDER BY babi
        """, (id_list,))
        results = [{"function_name": r[0], "function_detail": r[1]} for r in cur.fetchall()]

        cur.close()
        conn.close()
        return results
    except Exception as e:
        raise RuntimeError(f"Failed to fetch function names: {e}")

