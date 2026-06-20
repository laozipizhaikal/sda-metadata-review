import pandas as pd
import os


current_date = pd.to_datetime('2026-04-25') # update reference date

# For live data following code to be used
# from datetime import date
# current_date = date.today().isoformat()

# import files
Base_Dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..") 

subs = pd.read_csv(os.path.join(Base_Dir, 'data/metadata_submissions.csv'))

tracker = pd.read_csv(os.path.join(Base_Dir, 'data/compliance_tracker.csv'))

flagged_df = pd.read_pickle(os.path.join(Base_Dir, 'data/processed/flagged_df.pkl'))

# clean submission id - remove trailing white spaces etc.

subs['submission_id'] = subs['submission_id'].astype(str).str.strip()
tracker['submission_id'] = tracker['submission_id'].astype(str).str.strip()

# create a merged dataframe
merged = pd.merge(subs, tracker, on='submission_id', how='left', suffixes=('_meta', '_tracker'))
merged['follow_up_date_dt'] = pd.to_datetime(merged['follow_up_date'], errors='coerce')

## 2.1 Department-Level Compliance Table

dept_groups = merged.groupby('department_meta')
dept_report = []

for dept, group in dept_groups:
    total_submitted = len(group)
    approved_count = len(group[group['final_status'].str.strip().str.lower() == 'approved'])
    pending_group = group[group['final_status'].str.strip().str.lower() != 'approved']
    pending_count = len(pending_group)
    
    app_rate = (approved_count / total_submitted) * 100 if total_submitted > 0 else 0.0

    # Follow-up metric
    if pending_count == 0:
        follow_up_status = "Not Required" 
    else:
        follow_ups_sent = pending_group['follow_up_sent'].str.strip().str.lower() == 'yes'
        if follow_ups_sent.all():
            follow_up_status = "Yes"
        elif follow_ups_sent.any():
            follow_up_status = "Partial"
        else:
            follow_up_status = "No"
        
    # No response after 7+ days metric
    no_resp_7days = "No"
    days_waiting = 0
    for _, p_row in pending_group.iterrows():
        if p_row['follow_up_sent'] == 'Yes' and p_row['department_responded'] == 'No':
            if not pd.isna(p_row['follow_up_date_dt']):
                days_diff = (current_date - p_row['follow_up_date_dt']).days
                days_waiting = days_diff
                if days_diff >= 7:
                    no_resp_7days = "Yes"
                    break
                
    dept_report.append({
        'Department': dept,
        'Datasets Submitted': total_submitted,
        'Approved': approved_count,
        'Pending': pending_count,
        '% Approved': round(app_rate, 2),
        'Follow-up Sent': follow_up_status,
        'No Response 7+ Days': no_resp_7days,
        'Days since followup': days_waiting
    })

dept_report_df = pd.DataFrame(dept_report).sort_values(by='% Approved', ascending=True)
dept_report_df.to_csv(os.path.join(Base_Dir, 'data/processed/dept_report.csv'), index=False)

# 2.2 Issue Type Analysis
pending_merged = merged[merged['final_status'].str.strip().str.lower() != 'approved']

issue_tracking = {}

for _, p_row in pending_merged.iterrows():
    sid = p_row['submission_id']

    if flagged_df.empty or 'submission_id' not in flagged_df.columns:
        issues_list = []
    else:
        flagged_df['submission_id'] = flagged_df['submission_id'].astype(str).str.strip()
        matched_flagged = flagged_df[flagged_df['submission_id'] == str(sid).strip()]
        
        if not matched_flagged.empty:
            issues_list = matched_flagged.iloc[0]['issue_list']
        else:
            issues_list = []

    has_no_response = (
        p_row['follow_up_sent'] == 'Yes' and p_row['department_responded'] == 'No'
    )

    for iss in issues_list:
        if iss not in issue_tracking:
            issue_tracking[iss] = {'count': 0, 'non_response_count': 0}
        issue_tracking[iss]['count'] += 1
        if has_no_response:
            issue_tracking[iss]['non_response_count'] += 1

# 2.3 DPDP Compliance Flag
dpdp_yes = merged[merged['dpdp_personal_data'].str.strip().str.lower() == 'yes']
dpdp_violators = []

for _, row in dpdp_yes.iterrows():
    class_ok = str(row['data_classification']).strip() in ['Restricted', 'Confidential']
    steward_ok = str(row['data_steward_assigned']).strip().lower() == 'Yes'
    if not (class_ok and steward_ok):
        dpdp_violators.append({
            'submission_id': row['submission_id'],
            'department': row['department_meta'],
            'dataset_title': row['dataset_title'],
            'data_classification': row['data_classification'],
            'data_steward_assigned': row['data_steward_assigned']
        })

dpdp_violators_df = pd.DataFrame(dpdp_violators)
dpdp_violators_df.to_csv(os.path.join(Base_Dir, 'data/processed/dpdp_violators.csv'), index=False)