import streamlit as st
import pandas as pd
import os
import plotly.express as px

# Section 3: Compliance Dashboard

# Load Data
Base_Dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..") 


@st.cache_data #(ttl=300) cache refresh not needed in local, can be refreshed manually on need
def load_data():
    """Load data safely, handling missing or empty files gracefully."""
    try:
        subs = pd.read_csv(os.path.join(Base_Dir, 'data/metadata_submissions.csv'))
        tracker = pd.read_csv(os.path.join(Base_Dir, 'data/compliance_tracker.csv'))
        quality_flags = pd.read_csv(os.path.join(Base_Dir, 'data/processed/quality_flags.csv'))
        clean_subs = pd.read_csv(os.path.join(Base_Dir, 'data/processed/clean_submissions.csv'))
        comp_report = pd.read_csv(os.path.join(Base_Dir, 'data/processed/dept_report.csv'))
    except Exception as e:
        st.error(f"Error loading source files. Please ensure your core script has run successfully. Details: {e}")
        st.stop()
        
    subs['submission_id'] = subs['submission_id'].astype(str).str.strip()
    tracker['submission_id'] = tracker['submission_id'].astype(str).str.strip()
    
    merged = pd.merge(subs, tracker, on='submission_id', how='left')
    return subs, tracker, quality_flags, clean_subs, comp_report, merged


subs, tracker, quality_flags, clean_subs, comp_report, merged = load_data()

# 1. Page Configuration
st.set_page_config(
    page_title="Metadata Submission Status - SDA UP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header block
st.title("Metadata Submission Status - SDA UP")
st.markdown("Interactive Dashboard to track metadata status, DPDP compliance, and department response")

#refresh data button
if st.button("🔄 Refresh data"):
    load_data.clear()
    st.rerun()
    
st.markdown("---")

# ==============================================================================
# PANEL 1: OVERVIEW METRICS
# ==============================================================================

st.subheader("Progress Overview")

# calculation
total_submissions = len(subs)

approved_series = tracker['final_status'].str.strip().str.lower() == 'approved'
total_approved = approved_series.sum()
pct_approved = (total_approved / total_submissions * 100) if total_submissions > 0 else 0

total_pending = len(tracker) - total_approved
pct_pending = (total_pending / total_submissions * 100) if total_submissions > 0 else 0

dpdp_yes = merged[merged['dpdp_personal_data'].str.strip().str.lower() == 'yes']

dpdp_violations = 0
for _, row in dpdp_yes.iterrows():
    class_ok = str(row.get('data_classification')).strip() in ['Restricted', 'Confidential']
    steward_ok = str(row.get('data_steward_assigned')).strip().lower() == 'yes'
    if not (class_ok and steward_ok):
        dpdp_violations += 1

# charting
row1 = st.container(horizontal=True)

with row1:
    st.metric("Total Submissions Received", f"{total_submissions}", height = "stretch")
    st.metric("Approved Submissions", f"{total_approved}", f"{pct_approved:.1f}% of total")
    st.metric("Pending Submissions", f"{total_pending}", f"{pct_pending:.1f}% of total", delta_color="inverse")
    st.metric("DPDP Compliance Issues", f"{dpdp_violations}", height = "stretch")    

st.markdown("---")

# ==============================================================================
# PANEL 2: DEPARTMENT STATUS
# ==============================================================================

st.subheader("Panel 2: Department-wise Compliance Metrics")

all_departments = sorted(comp_report['Department'].unique()) if 'Department' in comp_report.columns else []

selected_depts = st.multiselect("Filter by Department(s):", options=all_departments, default=all_departments)

status_list = comp_report['Follow-up Sent'].astype(str)

all_status = sorted(status_list.unique()) if 'Follow-up Sent' in comp_report.columns else []

selected_status = st.multiselect("Filter by Follow-up Status: ", options=all_status, default=all_status)

filtered_comp = comp_report[comp_report['Department'].isin(selected_depts) & comp_report['Follow-up Sent'].isin(selected_status)]
# filtered_comp = comp_report[comp_report['Follow-up Sent'].isin(selected_status)]  

st.markdown("**Department Status** (Click column headers to sort)")
row2 = st.container(horizontal=True)

with row2:
        st.dataframe(
        filtered_comp.style.background_gradient(subset=['% Approved'], cmap='RdYlGn'),
        width="stretch",
        hide_index=True
    )

row3 = st.container(horizontal=True)
with row3:
        fig_dept = px.bar(
            filtered_comp,
            x='Department',
            y=['Approved', 'Pending'],
            # color='% Approved',
            title="Submission volume by Department ",
            # color_continuous_scale=px.colors.diverging.RdYlGn
        )
        st.plotly_chart(fig_dept, width="stretch")
                 


st.markdown("---")

# ==============================================================================
# PANEL 3: ISSUE BREAKDOWN
# ==============================================================================
st.subheader("Panel 3: Common Quality Issue Breakdown")

all_issues = []
if not quality_flags.empty and 'issues' in quality_flags.columns:
    for _, row in quality_flags.iterrows():
        if pd.notna(row['issues']):
            all_issues.extend([i.strip() for i in str(row['issues']).split(',')])

if all_issues:
    issue_counts = pd.Series(all_issues).value_counts().reset_index()
    issue_counts.columns = ['Issue Type', 'Frequency']
    
    row4 = st.container(horizontal=True)
    
    with row4:
        fig_issues = px.bar(
            issue_counts, 
            y='Issue Type', 
            x='Frequency', 
            orientation='h',
            color='Frequency',
            text = 'Issue Type',
            title="Frequency of Rejection/Flag Reasons Across Submissions",
            color_continuous_scale=px.colors.sequential.OrRd
        )
        fig_issues.update_layout(yaxis={'categoryorder':'total ascending'})
        fig_issues.update_yaxes(showticklabels=False)
        st.plotly_chart(fig_issues, width="stretch")
        
else:
    st.success("No quality flags or systemic validation flaws detected in pending submissions.")

st.markdown("---")

# ==============================================================================
# PANEL 4: DPDP FLAG TRACKER
# ==============================================================================
st.subheader("Panel 4: DPDP (Personal Data) Guardrail Tracker")

dpdp_view = merged[merged['dpdp_personal_data'].str.strip().str.lower() == 'yes'].copy()

if not dpdp_view.empty:
    dpdp_view['Classification Valid'] = dpdp_view['data_classification'].isin(['Restricted', 'Confidential'])
    dpdp_view['Steward Assigned'] = dpdp_view['data_steward_assigned'].str.strip().str.lower() == 'yes'
    
    def evaluate_compliance(row):
        return "Compliant" if (row['Classification Valid'] and row['Steward Assigned']) else "NON-COMPLIANT"
        
    dpdp_view['Status'] = dpdp_view.apply(evaluate_compliance, axis=1)
    
    status_filter = st.radio("Filter Guardrail Status:", ["Show All Personal Datasets", "Show Non-Compliant Only"], horizontal=True)
    
    if status_filter == "Show Non-Compliant Only":
        dpdp_view = dpdp_view[dpdp_view['Status'] == "NON-COMPLIANT"]
        
    display_cols = [
        'submission_id', 'department_x', 'dataset_title', 
        'data_classification', 'data_steward_assigned', 'Status'
    ]
    
    final_dpdp_df = dpdp_view[display_cols].rename(columns={'department_x': 'Department'})
    
    def highlight_non_compliant(val):
        if val == 'NON-COMPLIANT':
            bg = 'RED'
            textcolor = 'WHITE' 
        else:
            bg = 'lightgreen'
            textcolor = 'black'
        return f'background-color: {bg}; color: {textcolor}; font-weight: bold;'

    st.dataframe(
        final_dpdp_df.style.map(highlight_non_compliant, subset=['Status']),
        width="stretch",
        hide_index=True
    )
else:
    st.success("No datasets containing personal data flags (DPDP) require active tracking.")