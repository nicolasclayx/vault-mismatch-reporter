import pandas as pd
from pathlib import Path

def run_exact_match_audit():
    # 1. Dynamically get the folder where this script lives
    script_dir = Path(__file__).resolve().parent
    
    # 2. Grab files using glob directly from the path object
    excel_files = list(script_dir.glob("*.xlsx")) + list(script_dir.glob("*.xls"))
    excel_files = [f for f in excel_files if "report" not in f.name.lower() and "audit" not in f.name.lower()]

    if not excel_files:
        print(f"❌ Error: Could not find any Excel files in {script_dir}")
        return

    # Sort by modification time
    excel_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    target_file = excel_files[0]

    print(f"⚡ Auditing: '{target_file.name}'")
    df = pd.read_excel(target_file)
        
    # Aggressive header cleanup
    df.columns = df.columns.str.strip().str.replace(r'\s+', ' ', regex=True)
    if 'File Extensi' in df.columns and 'File Extension' not in df.columns:
        df = df.rename(columns={'File Extensi': 'File Extension'})

    # Clean data columns
    df['Ext_Clean'] = df['File Extension'].astype(str).str.strip().str.lower()
    df['Name_Clean'] = df['Name'].astype(str).str.strip()
    df['Base_Name'] = df['Name_Clean'].str.lower().str.replace('.idw', '', regex=False).str.replace('.pdf', '', regex=False).str.strip()
    df['Mod_DateTime'] = pd.to_datetime(df['Date Modified'], errors='coerce')

    # Split datasets
    idws = df[df['Ext_Clean'] == 'idw'][['Base_Name', 'Name_Clean', 'State', 'Mod_DateTime']].copy()
    pdfs = df[df['Ext_Clean'] == 'pdf'][['Base_Name', 'Name_Clean', 'State', 'Mod_DateTime']].copy()

    # Re-group multiple iterations to ensure we are comparing the absolute latest modification entries
    idws = idws.sort_values('Mod_DateTime').groupby('Base_Name').last().reset_index()
    pdfs = pdfs.sort_values('Mod_DateTime').groupby('Base_Name').last().reset_index()

    print(f"📊 Extracted {len(idws)} IDWs and {len(pdfs)} PDFs. Evaluating relationships...")
    
    # Left join ensures IDWs remain visible even if the PDF is entirely missing
    merged = pd.merge(idws, pdfs, on='Base_Name', how='left', suffixes=('_IDW', '_PDF'))

    # Exact Logic Engine Implementation
    def evaluate_exact_timeline(row):
        # Rule 1: Check if the PDF file is missing entirely
        if pd.isna(row['Name_Clean_PDF']) or str(row['Name_Clean_PDF']).strip().lower() in ['nan', '']:
            return "MISSING PDF"
        
        # Ensure we have valid timestamps to run chronological math
        if pd.notna(row['Mod_DateTime_IDW']) and pd.notna(row['Mod_DateTime_PDF']):
            idw_day = row['Mod_DateTime_IDW'].date()
            pdf_day = row['Mod_DateTime_PDF'].date()
            
            # Rule 2: If PDF date is greater than or equal to IDW date, it is a valid match
            if pdf_day >= idw_day:
                return "MATCH (OK)"
            else:
                return "STALE PDF (PDF is older than IDW)"
                
        return "UNKNOWN (MISSING TIMESTAMPS)"

    merged['Audit_Result'] = merged.apply(evaluate_exact_timeline, axis=1)
    
    # Isolate exceptions (anything that isn't a perfect MATCH)
    exceptions_report = merged[merged['Audit_Result'] != 'MATCH (OK)'].copy()
    
    # 3. Save the output report into the exact same folder as the script
    output_filepath = script_dir / 'vault_audit_summary.xlsx'
    
    if len(exceptions_report) > 0:
        # Organize columns cleanly
        exceptions_report = exceptions_report[[
            'Base_Name', 'Audit_Result',
            'Name_Clean_IDW', 'State_IDW', 'Mod_DateTime_IDW',
            'Name_Clean_PDF', 'State_PDF', 'Mod_DateTime_PDF'
        ]].rename(columns={
            'Base_Name': 'Base Name',
            'Name_Clean_IDW': 'IDW_Filename',
            'State_IDW': 'IDW_State',
            'Mod_DateTime_IDW': 'IDW_Date_Modified',
            'Name_Clean_PDF': 'PDF_Filename',
            'State_PDF': 'PDF_State',
            'Mod_DateTime_PDF': 'PDF_Date_Modified'
        })
        
        exceptions_report.to_excel(output_filepath, index=False)
        print(f"🚨 DONE! Identified {len(exceptions_report)} anomalies (Missing entirely or Stale).")
        print(f"📁 Report workbook generated at: {output_filepath.resolve()}")
    else:
        print("🎉 Perfect dataset! All files are either exact chronological matches or up to date.")

if __name__ == "__main__":
    run_exact_match_audit()