"""
Dashboard application for visualizing the AI Sonar Issue Fixer.
"""
import os
import json
import time
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.utils.memory import AgentMemory
from src.utils.feedback import FeedbackManager

# Set page configuration
st.set_page_config(
    page_title="AI Sonar Issue Fixer Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize memory and feedback with error handling
try:
    memory = AgentMemory()
    feedback_manager = FeedbackManager(memory=memory)
except Exception as e:
    st.error(f"Error initializing memory or feedback: {str(e)}")
    # Create empty instances as fallback
    memory = AgentMemory(memory_file="empty_memory.json")
    feedback_manager = FeedbackManager(feedback_file="empty_feedback.json", memory=memory)

# Title
st.title("🔍 AI Sonar Issue Fixer Dashboard")
st.markdown("Monitor and analyze the performance of the AI Sonar Issue Fixer")

# Sidebar
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Overview", "Memory Analysis", "Feedback Analysis", "Agent Interactions"])

# Overview page
if page == "Overview":
    st.header("System Overview")

    # Get statistics
    memory_stats = memory.get_memory_stats()
    feedback_stats = feedback_manager.get_feedback_stats()

    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Fixes", memory_stats.get("total_memories", 0))

    with col2:
        st.metric("Successful Fixes", memory_stats.get("successful_fixes", 0))

    with col3:
        success_rate = memory_stats.get("success_rate", 0) * 100
        st.metric("Success Rate", f"{success_rate:.1f}%")

    with col4:
        st.metric("Total Feedback", feedback_stats.get("total_feedback", 0))

    # Create a chart for rule distribution
    st.subheader("Rule Distribution")

    rules = memory_stats.get("rules", {})
    if rules:
        rule_data = []
        for rule, stats in rules.items():
            rule_data.append({
                "Rule": rule,
                "Total": stats["total"],
                "Successful": stats["successful"],
                "Failed": stats["total"] - stats["successful"]
            })

        rule_df = pd.DataFrame(rule_data)

        # Create a stacked bar chart
        fig = px.bar(
            rule_df,
            x="Rule",
            y=["Successful", "Failed"],
            title="Fixes by Rule",
            labels={"value": "Number of Fixes", "variable": "Status"},
            color_discrete_map={"Successful": "#00CC96", "Failed": "#EF553B"}
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No rule data available yet.")

    # Recent activity
    st.subheader("Recent Activity")

    # Get recent memories
    recent_memories = sorted(memory.memories, key=lambda m: m.timestamp, reverse=True)[:10]

    if recent_memories:
        for memory_item in recent_memories:
            with st.expander(f"{memory_item.issue_key} - {memory_item.rule}"):
                st.markdown(f"**Message:** {memory_item.message}")
                st.markdown(f"**File:** {memory_item.file_path}")
                st.markdown(f"**Status:** {'✅ Success' if memory_item.success else '❌ Failed'}")
                st.markdown(f"**Time:** {datetime.fromtimestamp(memory_item.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")

                # Show code diff
                if memory_item.original_code and memory_item.fixed_code:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Original Code:**")
                        st.code(memory_item.original_code)

                    with col2:
                        st.markdown("**Fixed Code:**")
                        st.code(memory_item.fixed_code)

                st.markdown(f"**Explanation:** {memory_item.explanation}")

                # Show feedback if available
                feedback_items = feedback_manager.get_feedback_for_issue(memory_item.issue_key)
                if feedback_items:
                    st.markdown("**Feedback:**")
                    for feedback in feedback_items:
                        st.markdown(f"- {feedback.feedback_text} ({'✅' if feedback.success else '❌'}) - {feedback.source}")
    else:
        st.info("No recent activity available yet.")

# Memory Analysis page
elif page == "Memory Analysis":
    st.header("Memory Analysis")

    # Get memory statistics
    memory_stats = memory.get_memory_stats()

    # Success rate over time
    st.subheader("Success Rate Over Time")

    # Group memories by day
    memories_by_day = {}
    for memory_item in memory.memories:
        day = datetime.fromtimestamp(memory_item.timestamp).strftime("%Y-%m-%d")
        if day not in memories_by_day:
            memories_by_day[day] = {"total": 0, "successful": 0}

        memories_by_day[day]["total"] += 1
        if memory_item.success:
            memories_by_day[day]["successful"] += 1

    if memories_by_day:
        day_data = []
        for day, stats in memories_by_day.items():
            success_rate = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
            day_data.append({
                "Day": day,
                "Success Rate": success_rate * 100,
                "Total": stats["total"]
            })

        day_df = pd.DataFrame(day_data)
        day_df = day_df.sort_values("Day")

        # Create a line chart
        fig = px.line(
            day_df,
            x="Day",
            y="Success Rate",
            title="Success Rate Over Time",
            labels={"Success Rate": "Success Rate (%)"},
            markers=True
        )

        # Add a size dimension for the number of fixes
        fig.update_traces(marker=dict(size=day_df["Total"] * 2))

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No memory data available yet.")

    # Rule success rates
    st.subheader("Rule Success Rates")

    rules = memory_stats.get("rules", {})
    if rules:
        rule_data = []
        for rule, stats in rules.items():
            success_rate = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
            rule_data.append({
                "Rule": rule,
                "Success Rate": success_rate * 100,
                "Total": stats["total"]
            })

        rule_df = pd.DataFrame(rule_data)

        # Create a bar chart
        fig = px.bar(
            rule_df,
            x="Rule",
            y="Success Rate",
            title="Success Rate by Rule",
            labels={"Success Rate": "Success Rate (%)"},
            color="Success Rate",
            color_continuous_scale=px.colors.sequential.Viridis
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No rule data available yet.")

    # Memory usage
    st.subheader("Memory Usage")

    # Count how many fixes used memory
    memory_usage_count = sum(1 for m in memory.memories if hasattr(m, "used_memory") and m.used_memory)
    # Safely handle empty memory list
    total_memories = max(1, len(memory.memories))

    if total_memories > 0:
        memory_usage_rate = memory_usage_count / total_memories

        # Create a gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=memory_usage_rate * 100,
            title={"text": "Memory Usage Rate (%)"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#1F77B4"},
                "steps": [
                    {"range": [0, 30], "color": "#FFDD99"},
                    {"range": [30, 70], "color": "#99DDFF"},
                    {"range": [70, 100], "color": "#99FFDD"}
                ]
            }
        ))

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No memory usage data available yet.")

# Feedback Analysis page
elif page == "Feedback Analysis":
    st.header("Feedback Analysis")

    # Get feedback statistics
    feedback_stats = feedback_manager.get_feedback_stats()

    # Feedback overview
    st.subheader("Feedback Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Feedback", feedback_stats.get("total_feedback", 0))

    with col2:
        st.metric("Positive Feedback", feedback_stats.get("positive_feedback", 0))

    with col3:
        positive_rate = feedback_stats.get("positive_rate", 0) * 100
        st.metric("Positive Rate", f"{positive_rate:.1f}%")

    # Feedback by source
    st.subheader("Feedback by Source")

    sources = feedback_stats.get("sources", {})
    if sources:
        source_data = []
        for source, stats in sources.items():
            positive_rate = stats["positive"] / stats["total"] if stats["total"] > 0 else 0
            source_data.append({
                "Source": source,
                "Total": stats["total"],
                "Positive": stats["positive"],
                "Negative": stats["total"] - stats["positive"],
                "Positive Rate": positive_rate * 100
            })

        source_df = pd.DataFrame(source_data)

        # Create a stacked bar chart
        fig = px.bar(
            source_df,
            x="Source",
            y=["Positive", "Negative"],
            title="Feedback by Source",
            labels={"value": "Number of Feedback", "variable": "Type"},
            color_discrete_map={"Positive": "#00CC96", "Negative": "#EF553B"}
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No feedback source data available yet.")

    # Recent feedback
    st.subheader("Recent Feedback")

    # Get recent feedback
    recent_feedback = sorted(feedback_manager.feedback_items, key=lambda f: f.timestamp, reverse=True)[:10]

    if recent_feedback:
        for feedback in recent_feedback:
            with st.expander(f"{feedback.issue_key} - {feedback.source}"):
                st.markdown(f"**Feedback:** {feedback.feedback_text}")
                st.markdown(f"**Status:** {'✅ Success' if feedback.success else '❌ Failed'}")
                st.markdown(f"**Time:** {datetime.fromtimestamp(feedback.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
                st.markdown(f"**Source:** {feedback.source}")
    else:
        st.info("No recent feedback available yet.")

# Agent Interactions page
elif page == "Agent Interactions":
    st.header("Agent Interactions")

    # Agent interaction diagram
    st.subheader("Agent Interaction Diagram")

    # Create a Sankey diagram to visualize agent interactions
    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=["SonarQube API", "Issue Analyzer", "Memory", "Code Fixer", "Feedback", "Git Operations", "PR Creator", "Azure DevOps API"],
            color=["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD", "#8C564B", "#E377C2", "#7F7F7F"]
        ),
        link=dict(
            source=[0, 1, 2, 3, 3, 4, 5, 6],
            target=[1, 3, 3, 5, 4, 3, 6, 7],
            value=[10, 8, 5, 7, 4, 3, 6, 6],
            color=["rgba(31, 119, 180, 0.4)", "rgba(255, 127, 14, 0.4)", "rgba(44, 160, 44, 0.4)",
                   "rgba(214, 39, 40, 0.4)", "rgba(148, 103, 189, 0.4)", "rgba(140, 86, 75, 0.4)",
                   "rgba(227, 119, 194, 0.4)", "rgba(127, 127, 127, 0.4)"]
        )
    ))

    fig.update_layout(title_text="Agent Interaction Flow", font_size=12)
    st.plotly_chart(fig, use_container_width=True)

    # Agent performance
    st.subheader("Agent Performance")

    # Create a radar chart for agent performance metrics
    categories = ["Speed", "Accuracy", "Memory Usage", "Feedback Integration", "Code Quality"]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=[0.8, 0.9, 0.7, 0.6, 0.85],
        theta=categories,
        fill='toself',
        name='Issue Analyzer'
    ))

    fig.add_trace(go.Scatterpolar(
        r=[0.7, 0.85, 0.9, 0.8, 0.9],
        theta=categories,
        fill='toself',
        name='Code Fixer'
    ))

    fig.add_trace(go.Scatterpolar(
        r=[0.9, 0.8, 0.6, 0.7, 0.75],
        theta=categories,
        fill='toself',
        name='PR Creator'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # Agent activity timeline
    st.subheader("Agent Activity Timeline")

    # Create a Gantt chart for agent activity with dynamic dates
    today = datetime.now().strftime('%Y-%m-%d')

    # Create time intervals based on today's date
    df = pd.DataFrame([
        dict(Task="Issue Analyzer", Start=f'{today} 00:00', Finish=f'{today} 00:05', Resource="Analysis"),
        dict(Task="Memory Lookup", Start=f'{today} 00:05', Finish=f'{today} 00:06', Resource="Memory"),
        dict(Task="Code Fixer", Start=f'{today} 00:06', Finish=f'{today} 00:10', Resource="Fixing"),
        dict(Task="Feedback", Start=f'{today} 00:10', Finish=f'{today} 00:11', Resource="Feedback"),
        dict(Task="Git Operations", Start=f'{today} 00:11', Finish=f'{today} 00:12', Resource="Git"),
        dict(Task="PR Creator", Start=f'{today} 00:12', Finish=f'{today} 00:14', Resource="PR")
    ])

    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Resource")
    fig.update_layout(xaxis_title="Time", yaxis_title="Agent")

    st.plotly_chart(fig, use_container_width=True)

# Run the dashboard
def run_dashboard():
    """Run the dashboard."""
    import streamlit.cli as stcli
    import sys

    # Get the path to this file
    file_path = os.path.abspath(__file__)

    # Run the dashboard
    sys.argv = ["streamlit", "run", file_path]
    stcli.main()

if __name__ == "__main__":
    run_dashboard()
