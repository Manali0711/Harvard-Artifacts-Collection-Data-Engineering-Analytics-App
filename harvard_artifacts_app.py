
import streamlit as st
import requests
import pandas as pd
import mysql.connector
from datetime import datetime
import time
import plotly.express as px       
import plotly.graph_objects as go

print("Imports are working!")

# Page config

st.set_page_config(page_title="Harvard Artifacts Collection", layout="wide")

# Database connection function (using your provided credentials)

@st.cache_resource
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
            port=4000,
            user="2pUFmw5B7Z8PAcC.root",
            password="QoDuwoQtPH7W4EPg",
            database="harvard_artifacts",
            autocommit=True
        )
        return conn
    except mysql.connector.Error as e:
        st.error(f"❌ Database connection failed: {e}")
        return None


# **BLOCK 1: Database Setup**
def create_tables():
    """Create the 3 required tables"""
    conn = get_db_connection()
    if conn is None:
        st.error("Cannot create tables: no database connection.")
        return

    if not conn.is_connected():
        st.error("Connection to TiDB is closed or not available.")
        return

    cursor = conn.cursor()


    # Table 1: artifactmetadata

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS artifactmetadata (
        id INT PRIMARY KEY,
        title TEXT,
        culture TEXT,
        period TEXT,
        century TEXT,
        medium TEXT,
        dimensions TEXT,
        description TEXT,
        department TEXT,
        classification TEXT,
        accessionyear INT,
        accessionmethod TEXT
    )
    """)

    # Table 2: artifactmedia                      

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS artifactmedia (
        objectid INT,
        imagecount INT,
        mediacount INT,
        colorcount INT,
        `rank` INT,         
        datebegin INT,                                                 
        dateend INT,
        FOREIGN KEY (objectid) REFERENCES artifactmetadata(id)
    )
    """)

    # Table 3: artifactcolors

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS artifactcolors (
        objectid INT,
        spectrum TEXT,
        hue TEXT,
        color TEXT,
        percent REAL,
        css3 TEXT,
        FOREIGN KEY (objectid) REFERENCES artifactmetadata(id)
    )
    """)

    #conn.commit()     
    #cursor.close()    
    #conn.close()       
   
# **BLOCK 2: API Data Collection**

def fetch_artifacts(classification, api_key, target_records=2500):
    """Fetch 2500 records for a given classification with pagination"""
    base_url = "https://api.harvardartmuseums.org"
    artifacts = []                                                 
    page = 1
    size = 100  # Max per page
    collected = 0
      
    st.info(f"Collecting {target_records} records for '{classification}'...")
    
    # Create a single progress bar object (start at 0)
    progress_bar = st.progress(0.0)

    while collected < target_records:
        url = f"{base_url}/object"
        params = {
            'apikey': api_key,
            'classification': classification,   
            'size': size,
            'page': page
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if not data.get('records'):
            break
            
        new_records = min(len(data['records']), target_records - collected)
        artifacts.extend(data['records'][:new_records])
        collected += new_records
        
        if 'next' not in data.get('info', {}):
            # Update to 100% when no next page
            progress_bar.progress(1.0)
            break
            
        page += 1
        time.sleep(0.1)  # Rate limiting
        
        # ---- FIXED PROGRESS CODE ----                     
        # value between 0.0 and 1.0
        progress_value = min(1.0, collected / float(target_records))
        progress_bar.progress(progress_value)
        # ------------------------------

    st.success(f"Collected {len(artifacts)} records!")
    return artifacts


# **BLOCK 3: Data Transformation**      

def transform_data(artifacts):         
    """Transform API JSON to structured data for 3 tables"""  
    metadata = []  
    media = []    
    colors = []      
    for artifact in artifacts:                     
        obj_id = artifact.get('id')  

        # Metadata                                                                        
                                     
        metadata.append({
            'id': obj_id,
            'title': artifact.get('title', ''),
            'culture': artifact.get('culture', ''),
            'period': artifact.get('period', ''),
            'century': artifact.get('century', ''),
            'medium': artifact.get('medium', ''),
            'dimensions': artifact.get('dimensions', ''),
            'description': (artifact.get('description') or '')[:500],  # Truncate long desc
            'department': artifact.get('department', ''),
            'classification': artifact.get('classification', ''),
            'accessionyear': artifact.get('accessionyear'),
            'accessionmethod': artifact.get('accessionmethod', '')
        })

        # Media

        media.append({
            'objectid': obj_id,                     
            'imagecount': artifact.get('imagecount', 0),
            'mediacount': artifact.get('mediacount', 0),
            'colorcount': artifact.get('colorcount', 0),          
            'rank': artifact.get('rank', 0),
            'datebegin': artifact.get('datebegin'),
            'dateend': artifact.get('dateend')
        })


        # Colors (if available)

        if 'colors' in artifact:
            for color in artifact['colors'][:5]:  # Top 5 colors per artifact
                colors.append({
                    'objectid': obj_id,
                    'spectrum': color.get('spectrum', ''),        
                    'hue': color.get('hue', ''),
                    'color': color.get('color', ''),
                    'percent': color.get('percent', 0),
                    'css3': color.get('css3', '')
                })
    
    return metadata, media, colors
    
# **BLOCK 4: SQL Insertion**   

def insert_data(metadata, media, colors):
    """Insert transformed data into 3 tables in batches"""
    conn = get_db_connection()
    if conn is None:
        st.error("Cannot insert data: no database connection.")
        return

    if not conn.is_connected():
        st.error("Connection to TiDB is closed or not available.")
        return

    cursor = conn.cursor()

    # Helper to clean NaN / inf
    def clean_rows(df):
        cleaned = []
        for _, row in df.iterrows():
            cleaned.append(tuple(
                None if (pd.isna(v) or v == float("inf") or v == float("-inf")) else v
                for v in row
            ))
        return cleaned

    # ---- METADATA (batch insert) ----
    metadata_df = pd.DataFrame(metadata)
    if not metadata_df.empty:
        metadata_rows = clean_rows(metadata_df)
        cursor.executemany(
            """
            INSERT IGNORE INTO artifactmetadata 
            (id, title, culture, period, century, medium, dimensions, description, 
             department, classification, accessionyear, accessionmethod)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            metadata_rows
        )

    # ---- MEDIA (batch insert) ----
    media_df = pd.DataFrame(media)
    if not media_df.empty:
        media_rows = clean_rows(media_df)
        cursor.executemany(
            """
            INSERT IGNORE INTO artifactmedia 
            (objectid, imagecount, mediacount, colorcount, `rank`, datebegin, dateend)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            media_rows
        )    
    # ---- COLORS (batch insert) ----
    colors_df = pd.DataFrame(colors)
    if not colors_df.empty:
        colors_rows = clean_rows(colors_df)
        cursor.executemany(
            """
            INSERT IGNORE INTO artifactcolors 
            (objectid, spectrum, hue, color, percent, css3)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            colors_rows
        )

    conn.commit()
    cursor.close()
    conn.close()

    st.success("Data inserted into SQL tables (batch insert)!")

    #conn.commit()
    #cursor.close()
    #conn.close()

    #st.success("Data inserted into SQL tables!")


# **BLOCK 5: SQL Queries**

QUERY_TEMPLATES = {
    "1": "SELECT * FROM artifactmetadata WHERE century = '11th century' AND culture = 'Byzantine'",
    "2": "SELECT DISTINCT culture FROM artifactmetadata WHERE culture IS NOT NULL AND culture != ''",
    "3": "SELECT * FROM artifactmetadata WHERE period LIKE '%Archaic%'",
    "4": "SELECT title, accessionyear FROM artifactmetadata WHERE accessionyear IS NOT NULL ORDER BY accessionyear DESC LIMIT 20",
    "5": "SELECT department, COUNT(*) as count FROM artifactmetadata GROUP BY department",
    "6": "SELECT m.title, a.imagecount FROM artifactmetadata m JOIN artifactmedia a ON m.id = a.objectid WHERE a.imagecount > 1 LIMIT 20",
    "7": "SELECT AVG(`rank`) as avg_rank FROM artifactmedia WHERE `rank` IS NOT NULL",
    "8": "SELECT m.title FROM artifactmetadata m JOIN artifactmedia a ON m.id = a.objectid WHERE a.colorcount > a.mediacount LIMIT 20",
    "9": "SELECT m.title FROM artifactmetadata m JOIN artifactmedia a ON m.id = a.objectid WHERE a.datebegin BETWEEN 1500 AND 1600 LIMIT 20",
    "10": "SELECT COUNT(*) FROM artifactmedia WHERE mediacount = 0",
    "11": "SELECT DISTINCT hue FROM artifactcolors WHERE hue IS NOT NULL",
    "12": "SELECT color, COUNT(*) as frequency FROM artifactcolors GROUP BY color ORDER BY frequency DESC LIMIT 5",
    "13": "SELECT hue, AVG(percent) AS avg_coverage FROM artifactcolors WHERE hue IS NOT NULL GROUP BY hue",
    "14":"SELECT m.title, m.culture, a.rank FROM artifactmetadata m JOIN artifactmedia a ON m.id = objectid WHERE m.period IS NOT NULL",
    "15": "SELECT COUNT(*) AS total_color_entries FROM artifactcolors",
    "16": "SELECT m.title, c.hue FROM artifactmetadata m JOIN artifactcolors c ON m.id = c.objectid WHERE m.culture = 'Byzantine' LIMIT 20",
    "17": "SELECT m.title, c.hue FROM artifactmetadata m JOIN artifactcolors c ON m.id = c.objectid ORDER BY m.title",
    "18": "SELECT m.title, m.culture, a.`rank` FROM artifactmetadata m JOIN artifactmedia a ON m.id = a.objectid WHERE m.period IS NOT NULL",
    "19": "SELECT DISTINCT m.title FROM artifactmetadata m "
          "JOIN artifactmedia a ON m.id = a.objectid "
          "JOIN artifactcolors c ON m.id = c.objectid "
          "WHERE c.hue = 'Grey' AND a.`rank` <= 10",
    "20": "SELECT classification, COUNT(*) as artifact_count, AVG(a.mediacount) as avg_media FROM artifactmetadata m JOIN artifactmedia a ON m.id = a.objectid GROUP BY classification ORDER BY artifact_count DESC LIMIT 10"
}

def run_query(query_num): 
    """Execute predefined SQL query and return DataFrame (dict cursor)."""
    query = QUERY_TEMPLATES.get(query_num, "")
    if not query:
        st.error("Invalid query number.")
        return pd.DataFrame()

    try:
        conn = mysql.connector.connect(
            host="gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
            port=4000,
            user="2pUFmw5B7Z8PAcC.root",
            password="QoDuwoQtPH7W4EPg",
            database="harvard_artifacts",
        )
    except mysql.connector.Error as e:
        st.error(f"❌ Database connection failed: {e}")
        return pd.DataFrame()

    try:
        cursor = conn.cursor(dictionary=True)  # rows as dicts [web:66][web:67]
        cursor.execute(query)
        rows = cursor.fetchall()              # list[dict]
        df = pd.DataFrame(rows)               # DataFrame directly from list of dicts
    except mysql.connector.Error as e:
        st.error(f"MySQL error while running query: {e}")
        df = pd.DataFrame()
    finally:
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass

    return df

# **Streamlit App Layout**

st.title("Harvard's Artifacts Collection")
st.markdown("---")

# Sidebar for API Key

st.sidebar.header("🔑 API Configuration")
api_key = st.sidebar.text_input("Harvard Art Museums API Key", type="password", 
                               help="Get your free key: https://www.harvardartmuseums.org/collections/api")

# 5 Predefined Classifications

classifications = ["Coins", "Paintings", "Sculpture", "Jewelry", "Drawings"]

# Main App

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Data Collection & ETL")

# Classification selector

    selected_class = st.selectbox("Select Classification", classifications, key="collect")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        if st.button("Collect Data", key="collect_btn"):
            if api_key:
                with st.spinner("Fetching from Harvard API..."):
                    raw_data = fetch_artifacts(selected_class, api_key)  
                    st.session_state.raw_data = raw_data
                    st.session_state.selected_class = selected_class
                    st.rerun()
            else:
                st.error("Please enter your API key!")

    with col_b:
        if st.button("Show Data", key="show_btn") and 'raw_data' in st.session_state:
            st.dataframe(pd.DataFrame(st.session_state.raw_data).head(10))
    
    with col_c:
        if st.button("Insert to SQL", key="insert_btn") and 'raw_data' in st.session_state:
            with st.spinner("Transforming & inserting..."):
                create_tables()  # Ensure tables exist
                metadata, media, colors = transform_data(st.session_state.raw_data)
                insert_data(metadata, media, colors)
                st.success("Data pipeline complete!")

with col2:
    st.header("Quick Stats")
    if 'selected_class' in st.session_state:
        st.metric("Classification", st.session_state.selected_class)
        st.metric("Records Collected", len(st.session_state.get('raw_data', [])))

# SQL Queries Section

st.markdown("---")
st.header("🔍 SQL Analytics Dashboard")

query_col1, query_col2 = st.columns([1, 3])

with query_col1:
    st.subheader("Run Query")
    query_num = st.selectbox("Select Query", list(QUERY_TEMPLATES.keys()), format_func=lambda x: f"Q{x}")
    
    if st.button("Execute Query"):
        with st.spinner("Running query..."):
            result_df = run_query(query_num)
            st.session_state.query_result = result_df
            st.session_state.query_num = query_num
with query_col2:
    if 'query_result' in st.session_state:
        st.subheader(f"Results - Query {st.session_state.query_num}")
        st.dataframe(st.session_state.query_result, use_container_width=True)
        
        # Auto-charting
        if len(st.session_state.query_result) > 0:
            if st.session_state.query_result.shape[1] >= 2:
                fig = px.bar(st.session_state.query_result.head(10), 
                           x=st.session_state.query_result.columns[0],
                           y=st.session_state.query_result.columns[1],
                           title="Query Visualization")
                st.plotly_chart(fig, use_container_width=True)

# Footer 
st.markdown("---")
st.caption("Created by : MANALI | Harvard Art Museums API")
