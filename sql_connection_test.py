import pyodbc
import os

SQL_SERVER = 'FTDC4-SQLVLT1-T'
DATABASE = 'FTI Vault'  # e.g., 'Vault'

def test_connection():
    print("🛰️ Initializing direct ODBC Driver 18 authentication handshake...")
    
    # Writing the connection string directly without overlapping curly brackets
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=" + str(SQL_SERVER) + ";"
        "DATABASE=" + str(DATABASE) + ";"
        "Trusted_Connection=yes;"  # <-- This tells SQL to use your Windows Login
        "TrustServerCertificate=yes;"
        "Connection Timeout=5;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        if cursor.fetchone():
            print("\n=============================================")
            print("🎉 SUCCESS! Pipeline established over ODBC 18.")
            print("=============================================")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"\n❌ Pipeline Rejected: {str(e)}")

if __name__ == "__main__":
    test_connection()