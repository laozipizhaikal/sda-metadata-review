import pandas as pd
import os
from datetime import datetime


Base_DIR = r'D:\Personal\Applications\ISB_SDA_UttarPradesh\Assignment\sda-metadata-review'

subs = pd.read_csv(os.path.join(Base_DIR, 'data/metadata_submissions.csv'))

tracker = pd.read_csv(os.path.join(Base_DIR, 'data/compliance_tracker.csv'))

# Check Integrity of the Data 

required_subs_cols = [
        'submission_id', 'department', 'dataset_title', 'data_owner_name',
        'description', 'data_classification', 'dpdp_personal_data',
        'last_updated', 'formats', 'record_count', 'submitted_on',
        'data_steward_assigned',
    ]

required_tracker_cols = [
        'submission_id', 'department', 'final_status', 'follow_up_sent',
        'follow_up_date', 'department_responded',
    ]


missing_subs = set(required_subs_cols) - set(subs.columns)
missing_tracker = set(required_tracker_cols) - set(tracker.columns)

if missing_subs:
    raise ValueError(f"metadata_submissions.csv is missing columns: {sorted(missing_subs)}")
if missing_tracker:
    raise ValueError(f"compliance_tracker.csv is missing columns: {sorted(missing_tracker)}")

subs['submission_id'] = subs['submission_id'].str.strip()
tracker['submission_id'] = tracker['submission_id'].str.strip()

current_date = pd.to_datetime('2026-06-18')

Valid_Classifications = ['Public', 'Restricted', 'Confidential']
DPDP_Valid_Classifications = ['Restricted', 'Confidential']

flagged_rows = []
clean_rows = []


for _, row in subs.iterrows():
    issues = []

    # Check 1: Data owner present
    if pd.isna(row['data_owner_name']) or str(row['data_owner_name']).strip() == "":
        issues.append("Missing data owner name")

    # Check 2: Description adequate
    desc = str(row['description']).strip() if not pd.isna(row['description']) else ""
    if desc == "" or len(desc) < 20:
        issues.append("Description missing / inadequate")
    

    # Check 3: Classification present & valid
    if pd.isna(row['data_classification']) or row['data_classification'] not in Valid_Classifications:
        issues.append("Classification invalid/missing")

    # Check 4: DPDP flag consistent
    if str(row['dpdp_personal_data']).strip().lower() == 'yes':
        if row['data_classification'] not in DPDP_Valid_Classifications:
            issues.append("DPDP flag inconsistent")

    # Check 5: Date format valid (last_updated)
    if not pd.isna(row['last_updated']):
        try:
            pd.to_datetime(row['last_updated'], format='%Y-%m-%d')
        except:
            issues.append("Last updated date format invalid")

    # Check 6: Record count present (unless live API)
    is_live_api = not pd.isna(row['formats']) and 'API' in str(row['formats'])
    
    if pd.isna(row['record_count']) or str(row['record_count']).strip() == "":
        if not is_live_api:
            issues.append("Record count missing")
    else:
        try:
            rc = int(float(row['record_count']))
            if rc < 0:
                issues.append("Record count negative")
        except:
            issues.append("Record count invalid")

    # Check 7: Submission date format
    if not pd.isna(row['submitted_on']):
        try:
            pd.to_datetime(row['submitted_on'], format='%Y-%m-%d')
        except:
            issues.append("Submission date format invalid")

    if issues:
        flagged_rows.append({
            'submission_id': row['submission_id'],
            'department': row['department'],
            'dataset_title': row['dataset_title'],
            'issues': ", ".join(issues),
            'issue_list': issues
        })
    else:
        clean_rows.append(row)

    flagged_df = pd.DataFrame(flagged_rows)
    clean_df = pd.DataFrame(clean_rows)

    if not flagged_df.empty:
        flagged_df[['submission_id', 'department', 'dataset_title', 'issues']].to_csv(os.path.join(Base_DIR, 'data/processed/quality_flags.csv'), index=False)
    else:
        pd.DataFrame(columns=['submission_id', 'department', 'dataset_title', 'issues']).to_csv(os.path.join(Base_DIR, 'data/processed/quality_flags.csv'), index=False)

    if not clean_df.empty:
        clean_df.to_csv(os.path.join(Base_DIR, 'data/processed/clean_submissions.csv'), index=False)
    else:
        subs.iloc[0:0].to_csv(os.path.join(Base_DIR, 'data/processed/clean_submissions.csv'), index=False)


flagged_ids = set(flagged_df['submission_id']) if not flagged_df.empty else set()

mis_approved = []
ready_to_approve = []
correctly_approved = 0
correctly_pending = 0

for _, row in tracker.iterrows():
    sid = row['submission_id']
    status = str(row['final_status']).strip()
    is_approved_in_tracker = status.lower() == 'approved'

    if sid in flagged_ids:
        if is_approved_in_tracker:
            mis_approved.append(sid)
        else:
            correctly_pending += 1
    else:
        if is_approved_in_tracker:
            correctly_approved += 1
        else:
            ready_to_approve.append(sid)
        
summary_metrics = {
    "Correctly Approved": correctly_approved,
    "Correctly Pending": correctly_pending,
    "Potentially Mis-approved": len(mis_approved),
    "Potentially Ready to Approve": len(ready_to_approve)
}

total_subs = len(subs)
pass_count = len(clean_df)
fail_count = len(flagged_df)

all_issues = []

if not flagged_df.empty:
    for _, row in flagged_df.iterrows():
        all_issues.extend(row['issue_list'])

issue_counts = pd.Series(all_issues).value_counts() if all_issues else pd.Series(dtype=int)

os.makedirs(os.path.join(Base_DIR, 'data/processed'), exist_ok=True)


summary_file_path = os.path.join(Base_DIR, 'data/processed/review_summary.txt')

with open(summary_file_path, 'w', encoding='utf-8') as f:
    f.write(f"Metadata Quality Report\n")
    f.write(f"=======================\n")
    f.write(f"Total Submissions: {total_subs} \n")
    f.write(f"Passing Submissions: {pass_count} ({pass_count/total_subs*100:.0f}%)\n")
    f.write(f"Failing Submissions: {fail_count} ({fail_count/total_subs*100:.0f}%)\n")
    f.write(f"Most Common Issue Types:\n")
    for iss, cnt in issue_counts.items():
        f.write(f"- {iss}: {cnt}\n")

flagged_df.to_pickle(os.path.join(Base_DIR, 'data/processed/flagged_df.pkl'))

dict = {'Ready to Approve':ready_to_approve ,'Misapproved':mis_approved}
to_check = pd.DataFrame(dict)

to_check.to_csv(os.path.join(Base_DIR, 'data/processed/to_check.csv'), index=False)