import pyodbc
import pandas as pd

# --- DATABASE CONFIGURATION ---
SQL_SERVER = 'FTDC4-SQLVLT1-T'
DATABASE = 'FTI Vault'
# ------------------------------

def map_entire_vault_schema():
    print("🔌 Connecting to Vault Server for deep schema scan...")
    
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=" + str(SQL_SERVER) + ";"
        "DATABASE=" + str(DATABASE) + ";"
        "Trusted_Connection=yes;"       
        "TrustServerCertificate=yes;"   
        "Connection Timeout=8;"
    )

    try:
        conn = pyodbc.connect(conn_str)
    except Exception as e:
        print(f"❌ Connection Blocked: {str(e)}")
        return
    
    print("🔎 Connection accepted! Mapping table names across the database...")
    
    # Query to find all tables related to files or lifecycles
    table_query = """
    SELECT TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_TYPE = 'BASE TABLE' 
      AND (TABLE_NAME LIKE '%File%' OR TABLE_NAME LIKE '%State%' OR TABLE_NAME LIKE '%Lifecycle%')
    """
    
    try:
        tables_df = pd.read_sql(table_query, conn)
        print("\n==================================================")
        print(f"📋 AVAILABLE TABLES DETECTED IN '{DATABASE}':")
        print("==================================================")
        for tbl in sorted(tables_df['TABLE_NAME'].tolist()):
            print(f"  📦 {tbl}")
        print("==================================================")
        
        # Now let's print columns for 'FileRevision' or 'FileIteration' if they exist
        target_tables = ['FileIteration', 'FileRev', 'FileRevision', 'Document']
        for target in target_tables:
            if target in tables_df['TABLE_NAME'].values:
                print(f"\nListing columns for found table: {target}")
                col_query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{target}'"
                cols_df = pd.read_sql(col_query, conn)
                for col in sorted(cols_df['COLUMN_NAME'].tolist()):
                    print(f"    🔹 {col}")
                    
        conn.close()
            
    except Exception as e:
        print(f"\n❌ Structural Scan Failed: {str(e)}")
        conn.close()

if __name__ == "__main__":
    map_entire_vault_schema();