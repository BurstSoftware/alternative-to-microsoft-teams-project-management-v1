import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import plotly.figure_factory as ff
import requests  # For making API calls
import json
import PyPDF2  # For reading PDFs
from io import BytesIO

# Initialize session state for plans, tasks, team members, and uploaded files
if 'plans' not in st.session_state:
    st.session_state.plans = {
        'Workplace Strategy': {
            'tasks': pd.DataFrame(columns=['Task', 'Status', 'Assigned To', 'Completed', 'Start Date', 'End Date']),
            'privacy': 'Shared',
            'last_accessed': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'shared_with': ['Leadership'],
            'template': 'Custom',
            'pinned': False,
            'group': None,
            'ai_assisted': True
        }
    }
if 'current_plan' not in st.session_state:
    st.session_state.current_plan = 'Workplace Strategy'
if 'team_members' not in st.session_state:
    st.session_state.team_members = ['Unassigned', 'Project Manager', 'Member 1', 'Member 2', 'Member 3']
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'generated_tasks' not in st.session_state:
    st.session_state.generated_tasks = []

# Define templates with pre-populated tasks and descriptions
templates = {
    'Basic': {
        'Simple Plan': {'tasks': ['Task 1', 'Task 2', 'Task 3'], 'description': 'A basic plan for simple projects'},
        'Project Management': {'tasks': ['Define project scope', 'Assign team roles', 'Track progress'], 'description': 'Manage your project with core tasks'}
    },
    'Premium': {
        'Research Report': {'tasks': ['Define research objectives', 'Collect data', 'Analyze data', 'Prepare report'], 'description': 'Create a detailed research report'},
        'Competitive Analysis': {'tasks': ['Identify key competitors', 'Gather competitor data', 'Analyze market position', 'Assess strengths and weaknesses', 'Prepare report', 'Present findings'], 'description': 'Analyze competitors in your industry'},
        'SWOT Analysis': {'tasks': ['Identify strengths', 'Identify weaknesses', 'Identify opportunities', 'Identify threats', 'Compile SWOT matrix'], 'description': 'Perform a SWOT analysis for strategic planning'},
        'Market Study': {'tasks': ['Define market scope', 'Conduct surveys', 'Analyze market trends', 'Prepare market report'], 'description': 'Conduct a comprehensive market study'},
        'Software Development': {'tasks': ['Plan sprint', 'Develop features', 'Test code', 'Deploy release'], 'description': 'Manage software development cycles'},
        'Sprint Planning': {'tasks': ['Define sprint goals', 'Prioritize backlog', 'Assign tasks', 'Review sprint'], 'description': 'Plan and execute agile sprints'}
    }
}

# Define a list of predefined groups
predefined_groups = [None, 'Contoso', 'Operations Department', 'Leadership', 'Public']

# Google AI Studio API setup (placeholder)
GOOGLE_AI_STUDIO_API_KEY = "YOUR_API_KEY_HERE"  # Replace with your API key
GOOGLE_AI_STUDIO_API_URL = "https://api.googleaistudio.com/v1/models/gemini:generate"  # Placeholder URL

# Function to extract text from uploaded files
def extract_file_content(uploaded_file):
    try:
        if uploaded_file.name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        elif uploaded_file.name.endswith('.txt'):
            return uploaded_file.read().decode('utf-8')
        else:
            return ""
    except Exception as e:
        st.error(f"Error reading file {uploaded_file.name}: {e}")
        return ""

# Function to call Google AI Studio API for task generation
def generate_tasks_with_google_ai(goal, content, file_data):
    try:
        # Prepare the prompt for the API
        prompt = f"""
        Based on the following project goal, content, and file data, generate a list of tasks for a project management plan. Return the tasks as a JSON array of strings.

        Goal: {goal}
        Content: {content}
        File Data: {file_data}

        Example output format:
        ["Task 1", "Task 2", "Task 3"]
        """

        headers = {
            "Authorization": f"Bearer {GOOGLE_AI_STUDIO_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt,
            "max_tokens": 500,
            "temperature": 0.7
        }

        response = requests.post(GOOGLE_AI_STUDIO_API_URL, headers=headers, json=payload)
        response.raise_for_status()

        # Parse the response (assuming the API returns JSON with a 'text' field containing the task list)
        result = response.json()
        tasks = json.loads(result.get('text', '[]'))  # Parse the task list from the response
        return tasks

    except Exception as e:
        st.error(f"Error generating tasks with Google AI Studio API: {e}")
        return []

# Title and Introduction
st.title("Streamlit TaskFlow")
st.write("A simple project management tool for your team!")

# Plan Management Sidebar with Filtering Tabs
st.sidebar.header("My Plans")

# Filtering Tabs
filter_tabs = ["Recent", "Shared", "Personal", "Pinned", "My Teams"]
selected_filter = st.sidebar.tabs(filter_tabs)

# Filter plans based on the selected tab
filtered_plans = list(st.session_state.plans.keys())
with selected_filter[0]:  # Recent
    filtered_plans = sorted(st.session_state.plans.keys(), 
                            key=lambda x: datetime.strptime(st.session_state.plans[x]['last_accessed'], "%Y-%m-%d %H:%M:%S"), 
                            reverse=True)
with selected_filter[1]:  # Shared
    filtered_plans = [name for name, data in st.session_state.plans.items() if data['privacy'] == 'Shared']
with selected_filter[2]:  # Personal
    filtered_plans = [name for name, data in st.session_state.plans.items() if data['privacy'] == 'Private']
with selected_filter[3]:  # Pinned
    filtered_plans = [name for name, data in st.session_state.plans.items() if data['pinned']]
with selected_filter[4]:  # My Teams
    filtered_plans = [name for name, data in st.session_state.plans.items() if data['group'] is not None]

# Display filtered plans in a selectbox
if filtered_plans:
    selected_plan = st.sidebar.selectbox("Select Plan", filtered_plans, index=filtered_plans.index(st.session_state.current_plan) if st.session_state.current_plan in filtered_plans else 0)
    if selected_plan != st.session_state.current_plan:
        st.session_state.current_plan = selected_plan
        st.session_state.tasks = st.session_state.plans[selected_plan]['tasks'].copy()
        st.session_state.plans[selected_plan]['last_accessed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
else:
    st.sidebar.write("No plans match this filter.")
    st.session_state.current_plan = None

# Create New Plan with Templates
with st.sidebar.form("new_plan_form"):
    st.subheader("Create New Plan")
    if st.form_submit_button("Create New"):
        with st.expander("Create new", expanded=True):
            st.write("**Project Manager Templates**")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Research Report"):
                    new_plan_name = "Research Report Plan"
                    selected_template = templates['Premium']['Research Report']
                    st.session_state.plans[new_plan_name] = {
                        'tasks': pd.DataFrame({
                            'Task': selected_template['tasks'],
                            'Status': ['To Do'] * len(selected_template['tasks']),
                            'Assigned To': ['Unassigned'] * len(selected_template['tasks']),
                            'Completed': [False] * len(selected_template['tasks']),
                            'Start Date': [None] * len(selected_template['tasks']),
                            'End Date': [None] * len(selected_template['tasks'])
                        }),
                        'privacy': 'Shared',
                        'last_accessed': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'shared_with': ['Leadership'],
                        'template': 'Research Report',
                        'pinned': False,
                        'group': None,
                        'ai_assisted': False
                    }
                    st.session_state.current_plan = new_plan_name
                    st.session_state.tasks = st.session_state.plans[new_plan_name]['tasks'].copy()
                    st.experimental_rerun()
                if st.button("Competitive Analysis"):
                    new_plan_name = "Competitive Analysis Plan"
                    selected_template = templates['Premium']['Competitive Analysis']
                    st.session_state.plans[new_plan_name] = {
                        'tasks': pd.DataFrame({
                            'Task': selected_template['tasks'],
                            'Status': ['To Do'] * len(selected_template['tasks']),
                            'Assigned To': ['Unassigned'] * len(selected_template['tasks']),
                            'Completed': [False] * len(selected_template['tasks']),
                            'Start Date': [None] * len(selected_template['tasks']),
                            'End Date': [None] * len(selected_template['tasks'])
                        }),
                        'privacy': 'Shared',
                        'last_accessed': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'shared_with': ['Leadership'],
                        'template': 'Competitive Analysis',
                        'pinned': False,
                        'group': None,
                        'ai_assisted': False
                    }
                    st.session_state.current_plan = new_plan_name
                    st.session_state.tasks = st.session_state.plans[new_plan_name]['tasks'].copy()
                    st.experimental_rerun()
            with col2:
                if st.button("SWOT Analysis"):
                    new_plan_name = "SWOT Analysis Plan"
                    selected_template = templates['Premium']['SWOT Analysis']
                    st.session_state.plans[new_plan_name] = {
                        'tasks': pd.DataFrame({
                            'Task': selected_template['tasks'],
                            'Status': ['To Do'] * len(selected_template['tasks']),
                            'Assigned To': ['Unassigned'] * len(selected_template['tasks']),
                            'Completed': [False] * len(selected_template['tasks']),
                            'Start Date': [None] * len(selected_template['tasks']),
                            'End Date': [None] * len(selected_template['tasks'])
                        }),
                        'privacy': 'Shared',
                        'last_accessed': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'shared_with': ['Leadership'],
                        'template': 'SWOT Analysis',
                        'pinned': False,
                        'group': None,
                        'ai_assisted': False
                    }
                    st.session_state.current_plan = new_plan_name
                    st.session_state.tasks = st.session_state.plans[new_plan_name]['tasks'].copy()
                    st.experimental_rerun()
                if st.button("Market Study"):
                    new_plan_name = "Market Study Plan"
                    selected_template = templates['Premium']['Market Study']
                    st.session_state.plans[new_plan_name] = {
                        'tasks': pd.DataFrame({
                            'Task': selected_template['tasks'],
                            'Status': ['To Do'] * len(selected_template['tasks']),
                            'Assigned To': ['Unassigned'] * len(selected_template['tasks']),
                            'Completed': [False] * len(selected_template['tasks']),
                            'Start Date': [None] * len(selected_template['tasks']),
                            'End Date': [None] * len(selected_template['tasks'])
                        }),
                        'privacy': 'Shared',
                        'last_accessed': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'shared_with': ['Leadership'],
                        'template': 'Market Study',
                        'pinned': False,
                        'group': None,
                        'ai_assisted': False
                    }
                    st.session_state.current_plan = new_plan_name
                    st.session_state.tasks = st.session_state.plans[new_plan_name]['tasks'].copy()
                    st.experimental_rerun()
            with col3:
                if st.button("Software Development"):
                    new_plan_name = "Software Development Plan"
                    selected_template = templates['Premium']['Software Development']
                    st.session_state.plans[new_plan_name] = {
                        'tasks': pd.DataFrame({
                            'Task': selected_template['tasks'],
                            'Status': ['To Do'] * len(selected_template['tasks']),
                            'Assigned To': ['Unassigned'] * len(selected_template['tasks']),
                            'Completed': [False] * len(selected_template['tasks']),
                            'Start Date': [None] * len(selected_template['tasks']),
                            'End Date': [None] * len(selected_template['tasks'])
                        }),
                        'privacy': 'Shared',
                        'last_accessed': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'shared_with': ['Leadership'],
                        'template': 'Software Development',
                        'pinned': False,
                        'group': None,
                        'ai_assisted': False
                    }
                    st.session_state.current_plan = new_plan_name
                    st.session_state.tasks = st.session_state.plans[new_plan_name]['tasks'].copy()
                    st.experimental_rerun()
                if st.button("Sprint Planning"):
                    new_plan_name = "Sprint Planning Plan"
                    selected_template = templates['Premium']['Sprint Planning']
                    st.session_state.plans[new_plan_name] = {
                        'tasks': pd.DataFrame({
                            'Task': selected_template['tasks'],
                            'Status': ['To Do'] * len(selected_template['tasks']),
                            'Assigned To': ['Unassigned'] * len(selected_template['tasks']),
                            'Completed': [False] * len(selected_template['tasks']),
                            'Start Date': [None] * len(selected_template['tasks']),
                            'End Date': [None] * len(selected_template['tasks'])
                        }),
                        'privacy': 'Shared',
                        'last_accessed': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'shared_with': ['Leadership'],
                        'template': 'Sprint Planning',
                        'pinned': False,
                        'group': None,
                        'ai_assisted': False
                    }
                    st.session_state.current_plan = new_plan_name
                    st.session_state.tasks = st.session_state.plans[new_plan_name]['tasks'].copy()
                    st.experimental_rerun()

            st.write("**Basic and Premium Templates**")
            col4, col5 = st.columns(2)
            with col4:
                if st.button("Simple Plan"):
                    new_plan_name = "Simple Plan"
                    selected_template = templates['Basic']['Simple Plan']
                    st.session_state.plans[new_plan_name] = {
                        'tasks': pd.DataFrame({
                            'Task': selected_template['tasks'],
                            'Status': ['To Do'] * len(selected_template['tasks']),
                            'Assigned To': ['Unassigned'] * len(selected_template['tasks']),
                            'Completed': [False] * len(selected_template['tasks']),
                            'Start Date': [None] * len(selected_template['tasks']),
                            'End Date': [None] * len(selected_template['tasks'])
                        }),
                        'privacy': 'Shared',
                        'last_accessed': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'shared_with': ['Leadership'],
                        'template': 'Simple Plan',
                        'pinned': False,
                        'group': None,
                        'ai_assisted': False
                    }
                    st.session_state.current_plan = new_plan_name
                    st.session_state.tasks = st.session_state.plans[new_plan_name]['tasks'].copy()
                    st.experimental_rerun()
                if st.button("Project Management"):
                    new_plan_name = "Project Management Plan"
                    selected_template = templates['Basic']['Project Management']
                    st.session_state.plans[new_plan_name] = {
                        'tasks': pd.DataFrame({
                            'Task': selected_template['tasks'],
                            'Status': ['To Do'] * len(selected_template['tasks']),
                            'Assigned To': ['Unassigned'] * len(selected_template['tasks']),
                            'Completed': [False] * len(selected_template['tasks']),
                            'Start Date': [None] * len(selected_template['tasks']),
                            'End Date': [None] * len(selected_template['tasks'])
                        }),
                        'privacy': 'Shared',
                        'last_accessed': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'shared_with': ['Leadership'],
                        'template': 'Project Management',
                        'pinned': False,
                        'group': None,
                        'ai_assisted': False
                    }
                    st.session_state.current_plan = new_plan_name
                    st.session_state.tasks = st.session_state.plans[new_plan_name]['tasks'].copy()
                    st.experimental_rerun()
            with col5:
                if st.button("Plan with Project Manager"):
                    new_plan_name = "AI-Assisted Plan"
                    tasks = ['Review plan with Project Manager']
                    st.session_state.plans[new_plan_name] = {
                        'tasks': pd.DataFrame({
                            'Task': tasks,
                            'Status': ['To Do'] * len(tasks),
                            'Assigned To': ['Unassigned'] * len(tasks),
                            'Completed': [False] * len(tasks),
                            'Start Date': [None] * len(tasks),
                            'End Date': [None] * len(tasks)
                        }),
                        'privacy': 'Shared',
                        'last_accessed': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'shared_with': ['Leadership'],
                        'template': 'AI-Assisted',
                        'pinned': False,
                        'group': None,
                        'ai_assisted': True
                    }
                    st.session_state.current_plan = new_plan_name
                    st.session_state.tasks = st.session_state.plans[new_plan_name]['tasks'].copy()
                    st.experimental_rerun()

            st.write("See all templates >")

# Display Plan Metadata
if st.session_state.current_plan:
    st.sidebar.subheader("Plan Details")
    current_plan_data = st.session_state.plans[st.session_state.current_plan]
    st.sidebar.write(f"**Template:** {current_plan_data['template']}")
    st.sidebar.write(f"**Privacy:** {current_plan_data['privacy']}")
    st.sidebar.write(f"**Last Accessed:** {current_plan_data['last_accessed']}")
    st.sidebar.write(f"**Shared with:** {', '.join(current_plan_data['shared_with'])}")
    st.sidebar.write(f"**Pinned:** {current_plan_data['pinned']}")
    st.sidebar.write(f"**Group:** {current_plan_data['group'] if current_plan_data['group'] else 'None'}")

    # Navigation Tabs
    tabs = ["Grid", "Board", "Timeline", "Charts", "Whiteboard", "People", "Goals"]
    selected_tab = st.tabs(tabs)

    # Grid Tab: Task Management
    with selected_tab[0]:
        st.subheader(f"Tasks for {st.session_state.current_plan}")
        
        # Goal and Content Input
        st.write("Share Your Goal and Relevant Content")
        st.write("Describe the goal of your plan and Project Manager will generate tasks for you.")
        goal = st.text_area("Enter your project goal", f"Conduct a {current_plan_data['template'].lower()} on largest custom interior design firms" if current_plan_data['template'] != 'Custom' else "Define your project goal")
        content = st.text_input("Add relevant content or notes", "Focus on market positioning and customer base")

        # File Upload
        st.write("Add files for better results")
        uploaded_file = st.file_uploader("Upload a file", type=["txt", "pdf", "docx"], key="file_uploader")
        if uploaded_file:
            if uploaded_file.name not in st.session_state.uploaded_files:
                st.session_state.uploaded_files.append(uploaded_file.name)
                st.session_state.uploaded_file_data = uploaded_file  # Store the file object for processing
                st.experimental_rerun()

        # Display Uploaded Files
        if st.session_state.uploaded_files:
            st.write("**Uploaded Files:**")
            for file_name in st.session_state.uploaded_files:
                st.write(f"- {file_name}")
            if st.button("Clear Uploaded Files"):
                st.session_state.uploaded_files = []
                st.session_state.uploaded_file_data = None
                st.experimental_rerun()

        # Generate Tasks with Google AI Studio API
        if current_plan_data.get('ai_assisted', False) and st.button("Generate Tasks from Goal"):
            if goal:
                # Extract content from uploaded files
                file_data = ""
                if 'uploaded_file_data' in st.session_state and st.session_state.uploaded_file_data:
                    file_data = extract_file_content(st.session_state.uploaded_file_data)

                # Call Google AI Studio API to generate tasks
                st.session_state.generated_tasks = generate_tasks_with_google_ai(goal, content, file_data)
                if not st.session_state.generated_tasks:
                    st.warning("No tasks generated. Using fallback tasks.")
                    st.session_state.generated_tasks = templates['Premium'].get(current_plan_data['template'], ['Default Task'])
                st.experimental_rerun()

        # Display Generated Tasks with Checkboxes
        if st.session_state.generated_tasks:
            st.write("**Based on the goal and provided content, I've created a custom set of tasks.**")
            st.write("**Team tasks**")
            st.write("**Task Title**")
            selected_tasks = []
            for task in st.session_state.generated_tasks:
                checked = st.checkbox(task, key=f"generated_{task}")
                if checked:
                    selected_tasks.append(task)

            # Assign All to Project Manager
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Assign all to Project Manager"):
                    selected_tasks = st.session_state.generated_tasks
                    new_tasks_df = pd.DataFrame({
                        'Task': selected_tasks,
                        'Status': ['To Do'] * len(selected_tasks),
                        'Assigned To': ['Project Manager'] * len(selected_tasks),
                        'Completed': [False] * len(selected_tasks),
                        'Start Date': [None] * len(selected_tasks),
                        'End Date': [None] * len(selected_tasks)
                    })
                    st.session_state.tasks = pd.concat([st.session_state.tasks, new_tasks_df], ignore_index=True)
                    st.session_state.plans[st.session_state.current_plan]['tasks'] = st.session_state.tasks.copy()
                    st.session_state.generated_tasks = []
                    st.experimental_rerun()
            with col2:
                if st.button("Add Selected Tasks"):
                    if selected_tasks:
                        new_tasks_df = pd.DataFrame({
                            'Task': selected_tasks,
                            'Status': ['To Do'] * len(selected_tasks),
                            'Assigned To': ['Unassigned'] * len(selected_tasks),
                            'Completed': [False] * len(selected_tasks),
                            'Start Date': [None] * len(selected_tasks),
                            'End Date': [None] * len(selected_tasks)
                        })
                        st.session_state.tasks = pd.concat([st.session_state.tasks, new_tasks_df], ignore_index=True)
                        st.session_state.plans[st.session_state.current_plan]['tasks'] = st.session_state.tasks.copy()
                        st.session_state.generated_tasks = []
                        st.experimental_rerun()
                    else:
                        st.warning("Please select at least one task to add.")
            st.info("AI-generated content may be incorrect")

        # Display and Manage Existing Tasks
        if not st.session_state.tasks.empty:
            st.subheader("Existing Tasks")
            for index, row in st.session_state.tasks.iterrows():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"{row['Task']}")
                with col2:
                    assigned_to = st.selectbox("Assign to", st.session_state.team_members, key=f"assign_{index}", index=st.session_state.team_members.index(row['Assigned To']))
                    st.session_state.tasks.at[index, 'Assigned To'] = assigned_to
                with col3:
                    completed = st.checkbox("Completed", key=f"complete_{index}", value=row['Completed'])
                    st.session_state.tasks.at[index, 'Completed'] = completed
                    st.session_state.tasks.at[index, 'Status'] = 'Completed' if completed else 'To Do'

            # Update the DataFrame in session state and plans
            st.session_state.tasks = st.session_state.tasks
            st.session_state.plans[st.session_state.current_plan]['tasks'] = st.session_state.tasks.copy()

            # Display Task Table
            st.dataframe(st.session_state.tasks)

        # Add Custom Task
        with st.form("add_custom_task"):
            custom_task = st.text_input("Add a custom task")
            custom_assigned_to = st.selectbox("Assign to", st.session_state.team_members, index=0)
            submit = st.form_submit_button("Add Custom Task")
            if submit and custom_task:
                new_task = pd.DataFrame({
                    'Task': [custom_task],
                    'Status': ['To Do'],
                    'Assigned To': [custom_assigned_to],
                    'Completed': [False],
                    'Start Date': [None],
                    'End Date': [None]
                })
                st.session_state.tasks = pd.concat([st.session_state.tasks, new_task], ignore_index=True)
                st.session_state.plans[st.session_state.current_plan]['tasks'] = st.session_state.tasks.copy()
                st.experimental_rerun()

    # Board Tab: Kanban-Style View
    with selected_tab[1]:
        st.subheader(f"Board View for {st.session_state.current_plan}")
        if not st.session_state.tasks.empty:
            statuses = ['To Do', 'In Progress', 'Completed']
            cols = st.columns(len(statuses))
            for i, status in enumerate(statuses):
                with cols[i]:
                    st.write(f"**{status}**")
                    tasks_in_status = st.session_state.tasks[st.session_state.tasks['Status'] == status]
                    for index, row in tasks_in_status.iterrows():
                        st.write(f"- {row['Task']} (Assigned to: {row['Assigned To']})")
                        new_status = st.selectbox("Move to", statuses, index=statuses.index(status), key=f"move_{index}")
                        if new_status != status:
                            st.session_state.tasks.at[index, 'Status'] = new_status
                            st.session_state.plans[st.session_state.current_plan]['tasks'] = st.session_state.tasks.copy()
                            st.experimental_rerun()
        else:
            st.write("No tasks to display in the board view.")

    # Timeline Tab: Gantt Chart View
    with selected_tab[2]:
        st.subheader(f"Timeline View for {st.session_state.current_plan}")
        if not st.session_state.tasks.empty:
            # Add date inputs for tasks if not set
            for index, row in st.session_state.tasks.iterrows():
                if pd.isna(row['Start Date']) or pd.isna(row['End Date']):
                    st.write(f"Set dates for task: {row['Task']}")
                    start_date = st.date_input("Start Date", key=f"start_{index}")
                    end_date = st.date_input("End Date", key=f"end_{index}")
                    if start_date and end_date:
                        st.session_state.tasks.at[index, 'Start Date'] = start_date.strftime("%Y-%m-%d")
                        st.session_state.tasks.at[index, 'End Date'] = end_date.strftime("%Y-%m-%d")
                        st.session_state.plans[st.session_state.current_plan]['tasks'] = st.session_state.tasks.copy()
                        st.experimental_rerun()

            # Create Gantt chart if dates are set
            tasks_with_dates = st.session_state.tasks.dropna(subset=['Start Date', 'End Date'])
            if not tasks_with_dates.empty:
                df_gantt = pd.DataFrame({
                    'Task': tasks_with_dates['Task'],
                    'Start': tasks_with_dates['Start Date'],
                    'Finish': tasks_with_dates['End Date'],
                    'Resource': tasks_with_dates['Assigned To']
                })
                fig = ff.create_gantt(df_gantt, index_col='Resource', show_colorbar=True, title="Task Timeline")
                st.plotly_chart(fig)
            else:
                st.write("Please set start and end dates for tasks to view the timeline.")
        else:
            st.write("No tasks to display in the timeline view.")

    # Charts Tab: Progress Visualization
    with selected_tab[3]:
        st.subheader(f"Progress Charts for {st.session_state.current_plan}")
        if not st.session_state.tasks.empty:
            # Simple Progress Bar
            completed_tasks = len(st.session_state.tasks[st.session_state.tasks['Completed'] == True])
            total_tasks = len(st.session_state.tasks)
            st.progress(completed_tasks / total_tasks)
            st.write(f"Progress: {completed_tasks}/{total_tasks} tasks completed")

            # Pie Chart for Task Status
            status_counts = st.session_state.tasks['Status'].value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index, title="Task Status Distribution")
            st.plotly_chart(fig)

            # Bar Chart for Tasks per Assignee
            assignee_counts = st.session_state.tasks['Assigned To'].value_counts()
            fig2 = px.bar(x=assignee_counts.index, y=assignee_counts.values, labels={'x': 'Assignee', 'y': 'Number of Tasks'}, title="Tasks per Assignee")
            st.plotly_chart(fig2)
        else:
            st.write("No tasks to display in the charts view.")

    # Whiteboard Tab: Placeholder for Collaborative Whiteboard
    with selected_tab[4]:
        st.subheader(f"Whiteboard for {st.session_state.current_plan}")
        st.write("This is a placeholder for a collaborative whiteboard feature.")
        whiteboard_notes = st.text_area("Add notes or ideas here:")
        if st.button("Save Whiteboard Notes"):
            st.write("Notes saved! (This is a placeholder for saving whiteboard content.)")
        st.write("In a real application, this could integrate a drawing tool or collaborative whiteboard like Miro or Jamboard.")

    # People Tab: Team Members Overview
    with selected_tab[5]:
        st.subheader(f"People in {st.session_state.current_plan}")
        st.write("**Team Members:**")
        for member in st.session_state.team_members:
            if member != 'Unassigned':
                st.write(f"- {member}")
                tasks_assigned = st.session_state.tasks[st.session_state.tasks['Assigned To'] == member]
                if not tasks_assigned.empty:
                    st.write(f"  Tasks Assigned: {len(tasks_assigned)}")
                else:
                    st.write("  No tasks assigned.")
        st.write("**Shared with:**")
        for shared in current_plan_data['shared_with']:
            st.write(f"- {shared}")

    # Goals Tab: Placeholder for Goal Tracking
    with selected_tab[6]:
        st.subheader(f"Goals for {st.session_state.current_plan}")
        st.write("This is a placeholder for goal tracking.")
        goal_description = st.text_area("Describe your project goals:", value=goal if goal else "Enter your goals here.")
        if st.button("Save Goals"):
            st.write("Goals saved! (This is a placeholder for saving goal content.)")
        st.write("In a real application, this could include goal progress tracking, milestones, or KPIs.")

else:
    st.write("Please select a plan to view its details.")
