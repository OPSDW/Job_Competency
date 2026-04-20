import streamlit as st
from openai import AzureOpenAI
import os
import base64
import io
import json

# --- Import file parsing libraries ---
import pandas as pd
import pdfplumber
from docx import Document

# --- Page Configuration ---
st.set_page_config(
    page_title="Optomi Capability Classifier",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Optomi Logo Integration ---
logo_path = "optomi_logo.png"

def get_image_as_base64(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

try:
    optomi_logo_base64 = get_image_as_base64(logo_path)
    logo_html = f"<img src='data:image/png;base64,{optomi_logo_base64}' style='max-height: 50px; margin-right: 15px; vertical-align: middle;'>"
except FileNotFoundError:
    logo_html = "<span style='font-size: 2em; color: #b0b0b0;'>🎯</span>"
except Exception as e:
    logo_html = "<span style='font-size: 2em; color: #b0b0b0;'>🎯</span>"

# --- Capability Colors ---
CAPABILITY_COLORS = {
    "Application Innovation": "#4FC3F7",
    "Data & AI": "#AB47BC",
    "ServiceNow": "#66BB6A",
    "Business Enablement": "#FFA726",
    "Cloud & Infrastructure": "#42A5F5",
    "Cybersecurity": "#EF5350",
    "Enterprise Platforms": "#26A69A",
}

# --- Custom App Styling (Dark Theme - matching existing Optomi app) ---
st.markdown(f"""
<style>
    /* Main app background */
    .stApp {{
        background-color: #1a1c23; 
        color: #e0e0e0;
    }}
    
    /* Headers */
    h1, h2, h3 {{
        color: #f0f2f6;
    }}

    /* Input Text Area */
    .stTextArea textarea {{
        background-color: #2b2e38;
        color: #e0e0e0;
        border: 1px solid #4a4d5a;
        border-radius: 8px;
        padding: 10px;
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
    }}

    /* Buttons */
    .stButton>button {{
        background-color: #007bff;
        color: white;
        border: 1px solid #007bff;
        border-radius: 25px;
        padding: 10px 24px;
        font-weight: bold;
        transition: all 0.3s ease-in-out;
        font-family: 'Segoe UI', sans-serif;
    }}
    .stButton>button:hover {{
        background-color: #0056b3;
        border-color: #0056b3;
        color: white;
    }}

    /* General Text */
    .main .block-container {{
        padding-top: 2rem;
    }}
    
    /* Capability result card */
    .capability-card {{
        background: linear-gradient(135deg, #2b2e38 0%, #1e2029 100%);
        border-radius: 12px;
        padding: 25px 30px;
        margin: 15px 0;
        border-left: 5px solid;
    }}
    .capability-card h2 {{
        margin: 0 0 5px 0;
        font-size: 1.8em;
    }}
    .capability-card .subtitle {{
        color: #9e9e9e;
        font-size: 0.95em;
        margin-bottom: 15px;
    }}
    
    /* Confidence bar */
    .confidence-bar-bg {{
        background-color: #3a3d4a;
        border-radius: 10px;
        height: 14px;
        width: 100%;
        margin: 8px 0;
    }}
    .confidence-bar-fill {{
        height: 14px;
        border-radius: 10px;
        transition: width 0.5s ease;
    }}
    
    /* Reasoning section */
    .reasoning-box {{
        background-color: #2b2e38;
        border: 1px solid #4a4d5a;
        border-radius: 8px;
        padding: 15px 20px;
        margin-top: 10px;
        font-size: 14px;
        line-height: 1.6;
    }}
    
    /* Alternative capabilities */
    .alt-capability {{
        display: inline-block;
        background-color: #2b2e38;
        border: 1px solid #4a4d5a;
        border-radius: 20px;
        padding: 6px 16px;
        margin: 4px;
        font-size: 0.85em;
    }}
    
    /* Skills tags */
    .skill-tag {{
        display: inline-block;
        background-color: #3a3d4a;
        border-radius: 15px;
        padding: 4px 12px;
        margin: 3px;
        font-size: 0.82em;
        color: #e0e0e0;
    }}
    
    /* Thick divider */
    hr.thick-divider {{
        border: 0;
        border-top: 3px solid #4a4d5a;
        margin: 25px 0;
    }}
    
    /* Info boxes */
    .info-box {{
        background-color: #2b2e38;
        border: 1px solid #4a4d5a;
        border-radius: 8px;
        padding: 12px 18px;
        margin: 8px 0;
    }}
</style>
""", unsafe_allow_html=True)

# --- Azure OpenAI Client Initialization ---
try:
    client = AzureOpenAI(
        api_key='46a07e250a2345e0ace2ede634d4a697',
        azure_endpoint='https://azopsai.cognitiveservices.azure.com/',
        api_version='2024-12-01-preview'
    )
    DEPLOYMENT_NAME = 'gpt-4o-2'
except Exception as e:
    st.error(f"Failed to configure OpenAI client: {e}", icon="🚨")
    client = None

# --- Helper Functions for File Text Extraction ---
def extract_text_from_pdf(file_like_object):
    text = ""
    with pdfplumber.open(file_like_object) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_text_from_docx(file_like_object):
    text = ""
    doc = Document(file_like_object)
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_text_from_excel(file_like_object):
    text = ""
    try:
        xls = pd.ExcelFile(file_like_object)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            df_string = df.to_string(index=False, header=False, na_rep="")
            cleaned_string = "\n".join([line for line in df_string.split('\n') if line.strip()])
            text += f"--- Content from sheet: {sheet_name} ---\n{cleaned_string}\n\n"
        return text
    except Exception as e:
        st.error(f"Error reading spreadsheet: {e}")
        return ""

def process_uploaded_files():
    if 'file_uploader_key' in st.session_state:
        all_extracted_text = "\n\n" 
        for uploaded_file in st.session_state.file_uploader_key:
            bytes_data = uploaded_file.getvalue()
            file_like_object = io.BytesIO(bytes_data)
            file_name = uploaded_file.name
            all_extracted_text += f"--- [Extracted Content from {file_name}] ---\n"
            try:
                if file_name.endswith('.pdf'):
                    all_extracted_text += extract_text_from_pdf(file_like_object)
                elif file_name.endswith('.docx'):
                    all_extracted_text += extract_text_from_docx(file_like_object)
                elif file_name.endswith(('.xls', '.xlsx')):
                    all_extracted_text += extract_text_from_excel(file_like_object)
                elif file_name.endswith('.txt'):
                     all_extracted_text += file_like_object.read().decode('utf-8')
                else:
                    st.warning(f"Unsupported file type: {file_name}. Skipping.", icon="⚠️")
            except Exception as e:
                st.error(f"Error processing file {file_name}: {e}", icon="🔥")
            all_extracted_text += f"--- [End of {file_name}] ---\n\n"
        
        placeholder = "Paste job description, intake notes, or any job-related information here..."
        if placeholder in st.session_state.raw_notes:
            st.session_state.raw_notes = st.session_state.raw_notes.replace(placeholder, all_extracted_text)
        else:
            st.session_state.raw_notes += all_extracted_text

# --- Application State Management ---
if 'raw_notes' not in st.session_state:
    st.session_state.raw_notes = """Paste job description, intake notes, or any job-related information here..."""
if 'classification_result' not in st.session_state:
    st.session_state.classification_result = None

# --- CORE AI CLASSIFICATION FUNCTION ---
def classify_capability(notes: str) -> dict | None:
    """
    Calls Azure OpenAI to analyze job information and classify it into 
    one of Optomi's 7 capabilities, with confidence scores and reasoning.
    """
    if not client:
        st.error("Azure OpenAI client is not configured.", icon="🚨")
        return None

    system_prompt = """
You are an expert job classification assistant for Optomi, a professional IT staffing and recruiting firm. Your task is to analyze job descriptions, intake notes, or any job-related information and classify the job into exactly ONE primary Optomi capability.

The 7 Optomi capabilities, and the types of jobs/skills that belong to each, are defined below:

1. **Application Innovation** — Software development, full-stack engineering, front-end, back-end, mobile development, QA/testing, application support, and custom application building. Key technologies: Java, .NET/.NET Core, Python (application dev), Node.js, Go, React, Angular, Vue, C++, mainframe development, DevOps (development-focused), Salesforce development (when purely coding custom apps).
   Common titles: Software Engineer, Full-Stack Developer, Front-End Developer, Back-End Developer, QA Engineer, QA Lead, Mobile Developer, Application Support Analyst, .NET Developer, Java Developer.

2. **Data & AI** — Data engineering, data architecture, data analytics, data science, AI/ML engineering, business intelligence, data visualization, database administration, ETL development, and data governance. Key technologies: Databricks, Snowflake, Power BI, Tableau, Informatica, SQL/databases (analytics-focused), Python (data/ML), Dataiku, dbt, Spark.
   Common titles: Data Engineer, Data Analyst, Data Scientist, BI Developer, AI Engineer, ML Engineer, ETL Developer, Database Administrator, Data Architect, AI Governance Analyst.

3. **ServiceNow** — Any role primarily focused on the ServiceNow platform: ServiceNow development, administration, architecture, business process consulting, ITSM, ITOM, CSM, FSO, HRSD, and ServiceNow-specific project management or product ownership.
   Common titles: ServiceNow Developer, ServiceNow Admin, ServiceNow Architect, ServiceNow BSA/BPC, ServiceNow Technical Lead.

4. **Business Enablement** — Project management, program management, product management, business analysis, scrum master, agile coaching, UX/UI design, technical writing, change management, and non-technical leadership/coordination roles in IT. This is NOT about software building — it's about enabling and governing IT delivery.
   Common titles: Project Manager, Program Manager, Product Manager, Product Owner, Business Analyst, Scrum Master, Agile Coach, UX Designer, Technical Writer.

5. **Cloud & Infrastructure** — Cloud architecture, cloud engineering, network engineering, systems administration, site reliability engineering (SRE), DevOps (infrastructure-focused), desktop/helpdesk support, telecom engineering, Windows/Linux administration, virtualization, and infrastructure platform engineering.
   Common titles: Cloud Architect, Cloud Engineer, Network Engineer, Systems Administrator, SRE, DevOps Engineer, Platform Engineer, Desktop Support Technician, Telecom Analyst.

6. **Cybersecurity** — Security operations (SOC), identity and access management (IAM/PAM), governance/risk/compliance (GRC), application security, cloud security, network security, penetration testing, red team, vulnerability management, security architecture, and AI risk/compliance.
   Common titles: Security Analyst, SOC Analyst, IAM Engineer, GRC Analyst, Security Architect, Penetration Tester, Vulnerability Engineer, CISO, Security Engineer.

7. **Enterprise Platforms** — Roles focused on major enterprise platform ecosystems (excluding ServiceNow, which has its own category): Salesforce (admin, architect, solution design), SAP, Oracle, Workday, and other large-scale enterprise application platforms. This includes configuration, admin, architecture, and functional consulting on these platforms.
   Common titles: Salesforce Admin, Salesforce Architect, SAP Consultant, Workday Consultant, Oracle Developer, Salesforce Solution Architect.

**Classification Rules:**
- If a job involves ServiceNow as the PRIMARY platform, always classify as "ServiceNow" even if it also involves project management or business analysis.
- If a job is about Salesforce, SAP, Oracle, or Workday platform work (admin, config, architecture), classify as "Enterprise Platforms."
- If a Salesforce role is purely custom development/coding and does NOT involve platform configuration, it could be "Application Innovation."
- If a role is about managing/leading IT projects or products (PM, PO, BA, Scrum) WITHOUT being tied to a specific platform, classify as "Business Enablement."
- Data-focused roles (data engineering, analytics, AI/ML, BI) go to "Data & AI."
- Infrastructure, cloud, networking, helpdesk/support, SRE go to "Cloud & Infrastructure."
- Security-focused roles always go to "Cybersecurity."
- When a role spans two capabilities, choose the ONE that best represents the primary focus of the daily work.

**Required JSON Output:**
Return ONLY a valid JSON object with this exact structure:
{
  "primary_capability": "One of the 7 capability names exactly as listed above",
  "confidence_percent": 85,
  "suggested_skill": "The most specific skill/sub-category within the capability (e.g., 'Java', 'Data Engineering/Architecture', 'IAM/PAM', 'Project/Program Management', 'Network', 'ServiceNow Admin/Developer', 'Salesforce Developer')",
  "reasoning": "2-3 sentences explaining WHY this capability was chosen, referencing specific technologies, responsibilities, or keywords from the input.",
  "key_signals": ["signal1", "signal2", "signal3"],
  "alternative_capability": "The second most likely capability, or null if confidence is above 90%",
  "alternative_confidence_percent": 10,
  "extracted_title": "The job title found in the input, or 'Not Specified' if none found"
}
"""

    user_prompt = f"""
Please analyze the following job information and classify it into one of Optomi's 7 capabilities. Return ONLY a valid JSON object.

**Job Information:**
---
{notes}
---
"""
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=messages,
            temperature=0.2,
            max_tokens=1000,
            n=1,
            response_format={"type": "json_object"}
        )
        
        response_content = response.choices[0].message.content
        return json.loads(response_content)

    except json.JSONDecodeError as e:
        st.error(f"Error: The AI returned invalid JSON. {e}", icon="🔥")
        return None
    except Exception as e:
        st.error(f"An error occurred while communicating with the AI model: {e}", icon="🔥")
        return None

# --- BATCH CLASSIFICATION FUNCTION ---
def classify_batch(jobs_list: list) -> list:
    """Classify multiple jobs by calling the AI for each one."""
    results = []
    for i, job_text in enumerate(jobs_list):
        if job_text.strip():
            result = classify_capability(job_text.strip())
            if result:
                result['input_text'] = job_text.strip()[:100] + "..."
                results.append(result)
    return results

# =============================================
# UI LAYOUT
# =============================================
st.markdown(
    f"<div style='display: flex; align-items: center;'>{logo_html}<h1 style='margin: 0;'>Optomi Capability Classifier</h1></div>",
    unsafe_allow_html=True
)
st.markdown("Analyze job descriptions and classify them into Optomi's 7 capability areas using AI.")
st.divider()

# --- Tabs for single vs batch ---
tab_single, tab_batch, tab_reference = st.tabs(["🎯 Single Job Classification", "📊 Batch Classification", "📖 Capability Reference"])

# =============================================
# TAB 1: SINGLE JOB CLASSIFICATION
# =============================================
with tab_single:
    col1, col_mid, col2 = st.columns([10, 2, 10])

    with col1:
        st.header("Job Information")
        st.file_uploader(
            "Upload Job Files (PDF, DOCX, XLSX, TXT)",
            type=["pdf", "docx", "xlsx", "xls", "txt"],
            accept_multiple_files=True,
            key='file_uploader_key',
            on_change=process_uploaded_files,
            label_visibility="collapsed"
        )
        st.session_state.raw_notes = st.text_area(
            "Paste job description, intake notes, or any job-related information here.", 
            height=500, 
            value=st.session_state.raw_notes, 
            label_visibility="collapsed"
        )

    with col_mid:
        st.markdown("<div style='margin-top: 280px;'></div>", unsafe_allow_html=True) 
        
        if st.button("Classify →", use_container_width=True, key="classify_btn"):
            if st.session_state.raw_notes and client:
                notes_to_process = st.session_state.raw_notes
                MAX_CHARS = 50000
                
                if len(notes_to_process) > MAX_CHARS:
                    notes_to_process = notes_to_process[:MAX_CHARS]
                    st.warning(f"Input truncated to {MAX_CHARS} characters.", icon="⚠️")

                with st.spinner("🤖 AI is analyzing and classifying..."):
                    result = classify_capability(notes_to_process)
                    if result:
                        st.session_state.classification_result = result
            else:
                st.warning("Please enter job information before classifying.", icon="⚠️")

    with col2:
        if st.session_state.classification_result:
            result = st.session_state.classification_result
            
            cap = result.get("primary_capability", "Unknown")
            confidence = result.get("confidence_percent", 0)
            skill = result.get("suggested_skill", "N/A")
            reasoning = result.get("reasoning", "")
            signals = result.get("key_signals", [])
            alt_cap = result.get("alternative_capability")
            alt_conf = result.get("alternative_confidence_percent", 0)
            title = result.get("extracted_title", "Not Specified")
            cap_color = CAPABILITY_COLORS.get(cap, "#888888")
            
            st.header("Classification Result")
            
            # --- Primary Capability Card ---
            st.markdown(f"""
            <div class="capability-card" style="border-left-color: {cap_color};">
                <div class="subtitle">Detected Job Title</div>
                <h3 style="margin: 0 0 15px 0; color: #f0f2f6;">{title}</h3>
                <div class="subtitle">Primary Capability</div>
                <h2 style="color: {cap_color};">{cap}</h2>
                <div class="subtitle">Suggested Skill: <strong style="color: #e0e0e0;">{skill}</strong></div>
                <div style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.9em; color: #9e9e9e;">Confidence</span>
                        <span style="font-size: 1.1em; font-weight: bold; color: {cap_color};">{confidence}%</span>
                    </div>
                    <div class="confidence-bar-bg">
                        <div class="confidence-bar-fill" style="width: {confidence}%; background-color: {cap_color};"></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- Key Signals ---
            if signals:
                signals_html = " ".join([f"<span class='skill-tag'>{s}</span>" for s in signals])
                st.markdown(f"""
                <div class="info-box">
                    <strong style="color: #9e9e9e; font-size: 0.85em;">KEY SIGNALS DETECTED</strong><br>
                    <div style="margin-top: 8px;">{signals_html}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # --- Reasoning ---
            st.markdown(f"""
            <div class="reasoning-box">
                <strong style="color: #9e9e9e; font-size: 0.85em;">AI REASONING</strong><br>
                <p style="margin-top: 8px; color: #d0d0d0;">{reasoning}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # --- Alternative Capability ---
            if alt_cap and alt_conf and alt_conf > 0:
                alt_color = CAPABILITY_COLORS.get(alt_cap, "#888888")
                st.markdown(f"""
                <div class="info-box" style="margin-top: 12px;">
                    <strong style="color: #9e9e9e; font-size: 0.85em;">ALTERNATIVE CONSIDERATION</strong><br>
                    <div style="margin-top: 8px;">
                        <span class="alt-capability" style="border-color: {alt_color}; color: {alt_color};">{alt_cap} — {alt_conf}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.header("Result")
            st.markdown(
                "<div style='height: 620px; padding: 15px; background-color: #2b2e38; border: 1px solid #4a4d5a; border-radius: 8px;'>"
                "<p style='color: #888; font-style: italic;'>Your classification result will appear here...</p></div>",
                unsafe_allow_html=True
            )

# =============================================
# TAB 2: BATCH CLASSIFICATION
# =============================================
with tab_batch:
    st.header("Batch Classification")
    st.markdown("Paste multiple job titles or short descriptions — one per line — to classify them all at once.")
    
    batch_input = st.text_area(
        "Enter job titles/descriptions (one per line)",
        height=250,
        placeholder="Senior Java Developer\nProject Manager - Agile Transformation\nServiceNow ITSM Architect\nData Engineer - Snowflake/Databricks\nSalesforce Solution Architect\nSOC Analyst Level 2\nAWS Cloud Engineer",
        key="batch_input"
    )
    
    col_batch_btn, col_batch_spacer = st.columns([1, 3])
    with col_batch_btn:
        batch_classify = st.button("🚀 Classify All", use_container_width=True, key="batch_btn")
    
    if batch_classify and batch_input.strip():
        lines = [l for l in batch_input.strip().split("\n") if l.strip()]
        if len(lines) > 25:
            st.warning("Limiting to 25 jobs for batch processing.", icon="⚠️")
            lines = lines[:25]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        batch_results = []
        
        for i, line in enumerate(lines):
            status_text.text(f"Classifying {i+1} of {len(lines)}: {line[:60]}...")
            result = classify_capability(line)
            if result:
                result['input_text'] = line
                batch_results.append(result)
            progress_bar.progress((i + 1) / len(lines))
        
        status_text.text(f"Done! Classified {len(batch_results)} jobs.")
        
        if batch_results:
            # Summary table
            table_data = []
            for r in batch_results:
                table_data.append({
                    "Job": r.get("input_text", "")[:80],
                    "Title": r.get("extracted_title", "N/A"),
                    "Capability": r.get("primary_capability", "Unknown"),
                    "Skill": r.get("suggested_skill", "N/A"),
                    "Confidence": f"{r.get('confidence_percent', 0)}%"
                })
            
            df_results = pd.DataFrame(table_data)
            st.dataframe(df_results, use_container_width=True, hide_index=True)
            
            # Capability breakdown
            st.markdown('<hr class="thick-divider">', unsafe_allow_html=True)
            st.subheader("Capability Breakdown")
            
            cap_counts = df_results['Capability'].value_counts()
            
            for cap_name, count in cap_counts.items():
                pct = count / len(df_results) * 100
                color = CAPABILITY_COLORS.get(cap_name, "#888888")
                st.markdown(f"""
                <div style="display: flex; align-items: center; margin: 6px 0;">
                    <span style="width: 200px; color: {color}; font-weight: bold;">{cap_name}</span>
                    <div style="flex: 1; background-color: #3a3d4a; border-radius: 8px; height: 22px; margin: 0 12px;">
                        <div style="width: {pct}%; background-color: {color}; height: 22px; border-radius: 8px; min-width: 30px; text-align: center;">
                            <span style="font-size: 0.75em; line-height: 22px; color: white; font-weight: bold;">{count}</span>
                        </div>
                    </div>
                    <span style="color: #9e9e9e; font-size: 0.85em; width: 50px; text-align: right;">{pct:.0f}%</span>
                </div>
                """, unsafe_allow_html=True)
            
            # Download option
            csv_data = df_results.to_csv(index=False)
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv_data,
                file_name="optomi_capability_classifications.csv",
                mime="text/csv"
            )

# =============================================
# TAB 3: CAPABILITY REFERENCE
# =============================================
with tab_reference:
    st.header("Optomi Capability Reference Guide")
    st.markdown("A quick reference for what types of roles and skills fall under each capability.")
    
    reference_data = {
        "Application Innovation": {
            "description": "Software development and custom application building across all technology stacks.",
            "example_titles": "Full-Stack Developer, Software Engineer, QA Lead, .NET Developer, Java Developer, Mobile Developer, Front-End Engineer",
            "key_skills": "Java, .NET/.NET Core, Python (dev), React, Angular, Node.js, Go, C++, QA/Testing, Mobile, Mainframe, Application Support"
        },
        "Data & AI": {
            "description": "Data engineering, analytics, AI/ML, business intelligence, and data platform work.",
            "example_titles": "Data Engineer, Data Analyst, Data Scientist, BI Developer, AI/ML Engineer, ETL Developer, Database Administrator",
            "key_skills": "Databricks, Snowflake, Power BI, Tableau, Informatica, SQL, Python (data/ML), Spark, dbt, Dataiku, Data Governance"
        },
        "ServiceNow": {
            "description": "All roles primarily focused on the ServiceNow platform ecosystem.",
            "example_titles": "ServiceNow Developer, ServiceNow Admin, ServiceNow Architect, ServiceNow BSA/BPC, ServiceNow Tech Lead",
            "key_skills": "ITSM, ITOM, CSM, FSO, HRSD, ServiceNow Platform, Flow Designer, IntegrationHub, Service Portal"
        },
        "Business Enablement": {
            "description": "IT project/program/product management, business analysis, agile coaching, and design roles that enable technology delivery.",
            "example_titles": "Project Manager, Program Manager, Product Manager, Product Owner, Business Analyst, Scrum Master, UX Designer, Technical Writer",
            "key_skills": "Project Management, Agile/Scrum, Product Ownership, Business Analysis, UX/UI Design, Change Management, Technical Writing"
        },
        "Cloud & Infrastructure": {
            "description": "Cloud platforms, networking, systems administration, SRE, DevOps infrastructure, and IT support.",
            "example_titles": "Cloud Architect, Cloud Engineer, Network Engineer, SRE, DevOps Engineer, Platform Engineer, Desktop Support, Systems Admin",
            "key_skills": "AWS, Azure, GCP, Networking, Linux/Unix, Windows, VMware, Kubernetes, Docker, Terraform, Telecom, Helpdesk"
        },
        "Cybersecurity": {
            "description": "Security operations, identity management, compliance, penetration testing, and security architecture.",
            "example_titles": "Security Analyst, SOC Analyst, IAM Engineer, GRC Analyst, Security Architect, Pen Tester, Vulnerability Engineer",
            "key_skills": "SOC, IAM/PAM, GRC, Application Security, Cloud Security, Network Security, Red Team, Pen Testing, Vulnerability Management"
        },
        "Enterprise Platforms": {
            "description": "Major enterprise platform ecosystems — Salesforce, SAP, Oracle, Workday — including admin, configuration, and architecture.",
            "example_titles": "Salesforce Admin, Salesforce Architect, SAP Consultant, Workday Consultant, Oracle Developer, Salesforce Solution Architect",
            "key_skills": "Salesforce, SAP, Oracle, Workday, Platform Administration, Solution Architecture, Functional Consulting"
        }
    }
    
    for cap_name, info in reference_data.items():
        color = CAPABILITY_COLORS.get(cap_name, "#888888")
        st.markdown(f"""
        <div class="capability-card" style="border-left-color: {color};">
            <h3 style="color: {color}; margin-bottom: 8px;">{cap_name}</h3>
            <p style="color: #c0c0c0; margin-bottom: 12px;">{info['description']}</p>
            <div style="margin-bottom: 8px;">
                <strong style="color: #9e9e9e; font-size: 0.8em;">EXAMPLE TITLES:</strong><br>
                <span style="color: #d0d0d0; font-size: 0.9em;">{info['example_titles']}</span>
            </div>
            <div>
                <strong style="color: #9e9e9e; font-size: 0.8em;">KEY SKILLS:</strong><br>
                <span style="color: #d0d0d0; font-size: 0.9em;">{info['key_skills']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
