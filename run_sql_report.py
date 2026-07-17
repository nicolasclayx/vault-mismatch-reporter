import pyodbc
import pandas as pd
import os

# --- DATABASE CONFIGURATION ---
SQL_SERVER = 'FTDC4-SQLVLT1-T'
DATABASE = 'FTI Vault'
# ------------------------------

def run_sql_exact_match_audit():
    print("🔌 Connecting directly to Autodesk Vault SQL Server...")
    
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
        print(f"❌ Database Connection Failed: {str(e)}")
        return
    
    # Query built directly from current Autodesk Vault system column layout
    query = """
    SELECT 
        FileName AS [Name],
        LifeCycleStateName AS [State],
        ModDate AS [Date_Modified],
        CASE 
            WHEN FileName LIKE '%.idw' THEN 'idw'
            WHEN FileName LIKE '%.pdf' THEN 'pdf'
            ELSE 'unknown'
        END AS [File_Extension],
        LOWER(REPLACE(REPLACE(FileName, '.idw', ''), '.pdf', '')) AS [Base_Name]
    FROM FileIteration
    WHERE (FileName LIKE '%.idw' OR FileName LIKE '%.pdf')
    """

    print("⚡ Fetching live metadata using your exact system schema...")
    try:
        df = pd.read_sql(query, conn)
    except Exception as sql_error:
        print("\n❌ SQL Execution Failed! A column mapping mismatch occurred.")
        print(f"📝 Error Details: {str(sql_error)}")
        conn.close()
        return
        
    conn.close()
    
    if df.empty:
        print("⚠️ Sync complete, but 0 active rows were returned. Check file filters.")
        return

    print(f"📊 Live data sync complete. Retrieved {len(df)} file records.")

    # Clean data types inside Python's cache memory
    df['File_Extension'] = df['File_Extension'].astype(str).str.strip().str.lower()
    df['Mod_DateTime'] = pd.to_datetime(df['Date_Modified'], errors='coerce')

    # Separate into IDW and PDF datasets
    idws = df[df['File_Extension'] == 'idw'][['Base_Name', 'Name', 'State', 'Mod_DateTime']].rename(
        columns={'Name': 'IDW_Filename', 'State': 'IDW_State', 'Mod_DateTime': 'IDW_Date_Modified'}
    )
    pdfs = df[df['File_Extension'] == 'pdf'][['Base_Name', 'Name', 'State', 'Mod_DateTime']].rename(
        columns={'Name': 'PDF_Filename', 'State': 'PDF_State', 'Mod_DateTime': 'PDF_Date_Modified'}
    )

    # De-duplicate to match only the newest iteration entries
    idws = idws.sort_values('IDW_Date_Modified').groupby('Base_Name').last().reset_index()
    pdfs = pdfs.sort_values('PDF_Date_Modified').groupby('Base_Name').last().reset_index()

    print("🔗 Aligning drawing pairs and running timeline rules...")
    merged = pd.merge(idws, pdfs, on='Base_Name', how='left')

    # Exact Logic Engine Execution ($PDF >= IDW$)
    def evaluate_exact_timeline(row):
        if pd.isna(row['PDF_Filename']) or str(row['PDF_Filename']).strip().lower() in ['nan', '']:
            return "MISSING PDF"
        
        if pd.notna(row['IDW_Date_Modified']) and pd.notna(row['PDF_Date_Modified']):
            idw_day = row['IDW_Date_Modified'].date()
            pdf_day = row['PDF_Date_Modified'].date()
            
            if pdf_day >= idw_day:
                return "MATCH (OK)"
            else:
                return "STALE PDF (PDF is older than IDW)"
                
        return "UNKNOWN (MISSING TIMESTAMPS)"

    merged['Audit_Result'] = merged.apply(evaluate_exact_timeline, axis=1)
    
    # Isolate anomalies to output
    exceptions_report = merged[merged['Audit_Result'] != 'MATCH (OK)'].copy()
    
    output_filename = 'sql_audit_summary.xlsx'
    if len(exceptions_report) > 0:
        exceptions_report = exceptions_report[[
            'Base_Name', 'Audit_Result',
            'IDW_Filename', 'IDW_State', 'IDW_Date_Modified',
            'PDF_Filename', 'PDF_State', 'PDF_Date_Modified'
        ]].rename(columns={'Base_Name': 'Base Name'})
        
        exceptions_report.to_excel(output_filename, index=False)
        print(f"🚨 DONE! Database check flagged {len(exceptions_report)} anomalies (Missing or Stale).")
        print(f"📁 Report workbook generated at: {os.path.abspath(output_filename)}")
    else:
        print("🎉 Perfect database match! All live assets are exact chronological matches.")

if __name__ == "__main__":
    run_sql_exact_match_audit()