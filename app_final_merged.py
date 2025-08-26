import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime

st.set_page_config(layout="wide")
st.title("📊 Decomposition Tree (Delay/KPI/Any Scenario)")

def convert_pandas_to_json_serializable(obj):
    """Convert pandas objects to JSON serializable format"""
    if obj is None:
        return None
    elif isinstance(obj, list):
        return [convert_pandas_to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_pandas_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.to_dict('records')
    elif isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        # For any other type, try pd.isna() only on scalar values
        try:
            if pd.isna(obj):
                return None
        except (ValueError, TypeError):
            pass
        # Convert to string as fallback
        return str(obj)

def kpi_panel(df, time_comparison="Day"):
    # Create a copy of the dataframe to avoid modifying the original
    df_copy = df.copy()
    if all(col in df.columns for col in ["Status", "Delay_Days"]) and len(df) > 0:
        total_sites = len(df)
        
        # Convert Delay_Days to numeric, handling errors
        df_copy['Delay_Days_Numeric'] = pd.to_numeric(df_copy['Delay_Days'], errors='coerce')
        
        # Calculate status counts based on time comparison method
        if time_comparison == "Week (Monday start)":
            # For week comparison, group by week and calculate status
            if 'Planned_Week_Label' in df_copy.columns and 'Actual_Week_Label' in df_copy.columns:
                # Create week-based status calculation
                df_copy['Week_Status'] = df_copy.apply(lambda row: calculate_week_status(row), axis=1)
                early = len(df_copy[df_copy['Week_Status'] == 'Early'])
                on_time = len(df_copy[df_copy['Week_Status'] == 'On-Time'])
                delayed = len(df_copy[df_copy['Week_Status'] == 'Delayed'])
                pending = len(df_copy[df_copy['Week_Status'] == 'Pending'])
            else:
                # Fallback to original status if week columns not available
                early = len(df_copy[df_copy['Status'] == 'Early'])
                on_time = len(df_copy[df_copy['Status'] == 'On-Time'])
                delayed = len(df_copy[df_copy['Status'] == 'Delayed'])
                pending = len(df_copy[df_copy['Status'] == 'Pending'])
                
        elif time_comparison == "Month":
            # For month comparison, group by month and calculate status
            if 'Planned_Month_Label' in df_copy.columns and 'Actual_Month_Label' in df_copy.columns:
                # Create month-based status calculation
                df_copy['Month_Status'] = df_copy.apply(lambda row: calculate_month_status(row), axis=1)
                early = len(df_copy[df_copy['Month_Status'] == 'Early'])
                on_time = len(df_copy[df_copy['Month_Status'] == 'On-Time'])
                delayed = len(df_copy[df_copy['Month_Status'] == 'Delayed'])
                pending = len(df_copy[df_copy['Month_Status'] == 'Pending'])
            else:
                # Fallback to original status if month columns not available
                early = len(df_copy[df_copy['Status'] == 'Early'])
                on_time = len(df_copy[df_copy['Status'] == 'On-Time'])
                delayed = len(df_copy[df_copy['Status'] == 'Delayed'])
                pending = len(df_copy[df_copy['Status'] == 'Pending'])
        else:
            # Day comparison - use original status
            early = len(df_copy[df_copy['Status'] == 'Early'])
            on_time = len(df_copy[df_copy['Status'] == 'On-Time'])
            delayed = len(df_copy[df_copy['Status'] == 'Delayed'])
            pending = len(df_copy[df_copy['Status'] == 'Pending'])
        
        # Calculate average delay (only for delayed items)
        delayed_data = df_copy.loc[(df_copy['Delay_Days_Numeric'] > 0) & (df_copy['Delay_Days_Numeric'].notna()), 'Delay_Days_Numeric']
        avg_delay = delayed_data.mean() if not delayed_data.empty else 0
        
        # Calculate max delay
        max_delay_data = df_copy.loc[(df_copy['Delay_Days_Numeric'] > 0) & (df_copy['Delay_Days_Numeric'].notna()), 'Delay_Days_Numeric']
        max_delay = max_delay_data.max() if not max_delay_data.empty else 0
        
        # Calculate average early completion (negative delay days)
        early_data = df_copy.loc[(df_copy['Delay_Days_Numeric'] < 0) & (df_copy['Delay_Days_Numeric'].notna()), 'Delay_Days_Numeric']
        avg_early = early_data.mean() if not early_data.empty else 0
        
        # Add time-based insights based on comparison method
        time_insights = ""
        if time_comparison == "Week (Monday start)":
            if 'Planned_Week_Label' in df_copy.columns:
                week_distribution = df_copy['Planned_Week_Label'].value_counts().head(5)
                time_insights = f"\n**Top 5 Planned Weeks:**\n"
                for week, count in week_distribution.items():
                    time_insights += f"• {week}: {count} sites\n"
        elif time_comparison == "Month":
            if 'Planned_Month_Label' in df_copy.columns:
                month_distribution = df_copy['Planned_Month_Label'].value_counts().head(5)
                time_insights = f"\n**Top 5 Planned Months:**\n"
                for month, count in month_distribution.items():
                    time_insights += f"• {month}: {count} sites\n"
        
        st.header(f"🔎 Project KPIs & On-Air Status Summary ({time_comparison})")
        
        # Create conditional display for delay and early metrics
        delay_text = f"**Avg Delay:** {avg_delay:.1f} days" if delayed > 0 else "**Avg Delay:** No delays"
        early_text = f"**Avg Early:** {abs(avg_early):.1f} days early" if early > 0 else "**Avg Early:** No early completions"
        max_delay_text = f"**Max Delay:** {max_delay} days" if delayed > 0 else "**Max Delay:** No delays"
        
        st.info(f"""
        **Total Sites:** {total_sites}  
        🔵 **Early On-Air:** {early}  
        🟢 **On-Time On-Air:** {on_time}  
        🔴 **Delayed On-Air:** {delayed}  
        ⚪ **Pending On-Air:** {pending}  
        {delay_text}  
        {early_text}  
        {max_delay_text}{time_insights}
        """)
    
    return df_copy

def calculate_week_status(row):
    """Calculate status based on week comparison"""
    if pd.isna(row['Planned_Week_Label']) or pd.isna(row['Actual_Week_Label']):
        return 'Pending'
    
    try:
        # Convert week labels to comparable format
        planned_week = str(row['Planned_Week_Label']).split(' ')[0]  # Get "2024-W01" part
        actual_week = str(row['Actual_Week_Label']).split(' ')[0]    # Get "2024-W01" part
        

        
        if planned_week == actual_week:
            return 'On-Time'
        elif actual_week < planned_week:  # Earlier week
            return 'Early'
        else:  # Later week
            return 'Delayed'
    except Exception as e:
        print(f"Error in calculate_week_status: {e}")
        return 'Pending'

def calculate_month_status(row):
    """Calculate status based on month comparison"""
    if pd.isna(row['Planned_Month_Label']) or pd.isna(row['Actual_Month_Label']):
        return 'Pending'
    
    try:
        # Convert month labels to comparable format
        planned_month = str(row['Planned_Month_Label']).split(' ')[0]  # Get "2024-01" part
        actual_month = str(row['Actual_Month_Label']).split(' ')[0]    # Get "2024-01" part
        

        
        if planned_month == actual_month:
            return 'On-Time'
        elif actual_month < planned_month:  # Earlier month
            return 'Early'
        else:  # Later month
            return 'Delayed'
    except Exception as e:
        print(f"Error in calculate_month_status: {e}")
        return 'Pending'

def node_color(status):
    return {
        'Early': '#3B82F6',      # Blue for early completion
        'Delayed': '#EF4444',    # Red for delayed
        'On-Time': '#10B981',    # Green for on-time
        'Pending': '#6B7280',    # Gray for pending
        'No Data': '#9CA3AF'     # Light gray for no data
    }.get(str(status), '#3B82F6')

def build_tree(df, hierarchy, value_col=None, tooltip_cols=None, time_comparison="Day"):
    # Calculate total for percentage calculation
    total_count = len(df)
    
    def add_node(level, parent, df_sub):
        if level >= len(hierarchy):
            return
        col = hierarchy[level]
        for val, group in df_sub.groupby(col):
            val_str = "No Data" if pd.isna(val) else str(val)
            value = int(group[value_col].sum()) if value_col else int(len(group))
            
            # Calculate percentage
            percentage_raw = (value / total_count) * 100 if total_count > 0 else 0
            # Format percentage: always show as whole number
            percentage = round(percentage_raw)
            
            tooltip_data = {}
            if tooltip_cols:
                for tcol in tooltip_cols:
                    if tcol in group.columns:
                        tdata = group[tcol]
                        vals = list(sorted(set(tdata.astype(str))))
                        tooltip_data[tcol] = ", ".join([v for v in vals if v and v != "nan"])
            # Always include these if present
            for dcol in ["Status","Delay_Days","PIC","Delay_Reason","Planned_OnAir_Date","Actual_OnAir_Date"]:
                if dcol in group.columns and dcol not in (tooltip_data.keys()):
                    vals = list(sorted(set(group[dcol].astype(str))))
                    tooltip_data[dcol] = ", ".join([v for v in vals if v and v != "nan"])
            
            # Add time-based status columns to tooltip based on comparison method
            if time_comparison == "Week (Monday start)" and 'Week_Status' in group.columns:
                vals = list(sorted(set(group['Week_Status'].astype(str))))
                tooltip_data['Week_Status'] = ", ".join([v for v in vals if v and v != "nan"])
            elif time_comparison == "Month" and 'Month_Status' in group.columns:
                vals = list(sorted(set(group['Month_Status'].astype(str))))
                tooltip_data['Month_Status'] = ", ".join([v for v in vals if v and v != "nan"])
            # Safely get the mode status based on time comparison
            status_mode = ""
            if time_comparison == "Week (Monday start)" and 'Week_Status' in group.columns and not group.empty:
                mode_result = group['Week_Status'].mode()
                if len(mode_result) > 0:
                    status_mode = mode_result[0]

            elif time_comparison == "Month" and 'Month_Status' in group.columns and not group.empty:
                mode_result = group['Month_Status'].mode()
                if len(mode_result) > 0:
                    status_mode = mode_result[0]

            elif 'Status' in group.columns and not group.empty:
                mode_result = group['Status'].mode()
                if len(mode_result) > 0:
                    status_mode = mode_result[0]

            
            node = {
                "name": f"{col}: {val_str}",
                "children": [],
                "value": value,
                "percentage": percentage,
                "level": level,
                "column": col,
                "node_value": val_str,
                "tooltip_data": tooltip_data,
                "color": node_color(status_mode),
                "raw_data": convert_pandas_to_json_serializable(group.to_dict('records'))
            }
            add_node(level + 1, node, group)
            if not node["children"]:
                node.pop("children")
            parent["children"].append(node)
    root_nodes = []
    
    # Safety check for empty hierarchy
    if not hierarchy:
        return []
    
    col = hierarchy[0]
    for val, group in df.groupby(col):
        val_str = "No Data" if pd.isna(val) else str(val)
        value = int(group[value_col].sum()) if value_col else int(len(group))
        
        # Calculate percentage for root nodes
        percentage_raw = (value / total_count) * 100 if total_count > 0 else 0
        # Format percentage: always show as whole number
        percentage = round(percentage_raw)
        
        tooltip_data = {}
        if tooltip_cols:
            for tcol in tooltip_cols:
                if tcol in group.columns:
                    tdata = group[tcol]
                    vals = list(sorted(set(tdata.astype(str))))
                    tooltip_data[tcol] = ", ".join([v for v in vals if v and v != "nan"])
        for dcol in ["Status","Delay_Days","PIC","Delay_Reason","Planned_OnAir_Date","Actual_OnAir_Date"]:
            if dcol in group.columns and dcol not in (tooltip_data.keys()):
                vals = list(sorted(set(group[dcol].astype(str))))
                tooltip_data[dcol] = ", ".join([v for v in vals if v and v != "nan"])
        
        # Add time-based status columns to tooltip based on comparison method
        if time_comparison == "Week (Monday start)" and 'Week_Status' in group.columns:
            vals = list(sorted(set(group['Week_Status'].astype(str))))
            tooltip_data['Week_Status'] = ", ".join([v for v in vals if v and v != "nan"])
        elif time_comparison == "Month" and 'Month_Status' in group.columns:
            vals = list(sorted(set(group['Month_Status'].astype(str))))
            tooltip_data['Month_Status'] = ", ".join([v for v in vals if v and v != "nan"])
        
        # Safely get the mode status for root node based on time comparison
        status_mode = ""
        if time_comparison == "Week (Monday start)" and 'Week_Status' in group.columns and not group.empty:
            mode_result = group['Week_Status'].mode()
            if len(mode_result) > 0:
                status_mode = mode_result[0]
        elif time_comparison == "Month" and 'Month_Status' in group.columns and not group.empty:
            mode_result = group['Month_Status'].mode()
            if len(mode_result) > 0:
                status_mode = mode_result[0]
        elif 'Status' in group.columns and not group.empty:
            mode_result = group['Status'].mode()
            if len(mode_result) > 0:
                status_mode = mode_result[0]
        
        root_node = {
            "name": f"{col}: {val_str}",
            "children": [],
            "value": value,
            "percentage": percentage,
            "level": 0,
            "column": col,
            "node_value": val_str,
            "tooltip_data": tooltip_data,
            "color": node_color(status_mode),
            "raw_data": convert_pandas_to_json_serializable(group.to_dict('records'))
        }
        add_node(1, root_node, group)
        if not root_node["children"]:
            root_node.pop("children")
        root_nodes.append(root_node)
    return root_nodes

st.sidebar.header("🧩 Advanced Configuration")
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    all_cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    
    # Time comparison fixed to Day for current workflow
    time_comparison = "Day"
    
    # Add time-based columns to the dataframe (kept for future, but only Day is used)
    if 'Planned_OnAir_Date' in df.columns:
        df['Planned_OnAir_Date'] = pd.to_datetime(df['Planned_OnAir_Date'], errors='coerce')
    
    if 'Actual_OnAir_Date' in df.columns:
        df['Actual_OnAir_Date'] = pd.to_datetime(df['Actual_OnAir_Date'], errors='coerce')
    
    st.sidebar.header("🪜 Hierarchy Configuration")
    
    # Time columns disabled for now (Day-only mode)
    time_columns = []
    
    # Combine all available columns
    available_cols = all_cols + time_columns
    
    # Use first 6 columns as default, or all columns if less than 6
    default_hierarchy = available_cols[:min(6, len(available_cols))]
    hierarchy = st.sidebar.multiselect(
        "Select hierarchy columns (ordered)",
        available_cols,
        default=default_hierarchy,
        help="⚠️ **Required:** Select at least one column. The order determines the tree structure - first column = root level, second = second level, etc."
    )
    tooltip_cols = st.sidebar.multiselect("Tooltip columns (aggregated for each node)", all_cols, default=[])
    
    # Node style customization
    st.sidebar.header("🎨 Node Style Customization")
    
    # Node shape selection
    node_shape = st.sidebar.selectbox(
        "Node Shape:",
        ["Circle", "Square", "Diamond", "Triangle", "Star", "Hexagon", "Cross", "Plus"],
        help="Choose the shape for tree nodes. Different shapes can help distinguish node types or levels."
    )
    
    # Node size customization
    node_size = st.sidebar.slider(
        "Node Size:",
        min_value=8,
        max_value=40,
        value=17,
        help="Adjust the size of all nodes in the tree"
    )
    
    # Bottleneck base color for node intensity scale
    bottleneck_base_color = st.sidebar.color_picker(
        "Bottleneck Base Color:",
        value="#2563EB",
        help="Base hue for node color intensity (darker = higher share)"
    )
    
    # Connection line customization
    st.sidebar.header("🔗 Connection Line Settings")
    line_width = st.sidebar.slider(
        "Line Width:",
        min_value=1,
        max_value=8,
        value=3,
        help="Adjust the thickness of connection lines between nodes"
    )
    
    line_color = st.sidebar.color_picker(
        "Line Color:",
        value="#94A3B8",
        help="Choose the color for connection lines"
    )
    
    line_opacity = st.sidebar.slider(
        "Line Opacity:",
        min_value=0.1,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Adjust the transparency of connection lines"
    )
    
    # Font size customization
    st.sidebar.header("📝 Label Font Settings")
    font_size = st.sidebar.slider(
        "Font Size:",
        min_value=10,
        max_value=20,
        value=13,
        help="Adjust the font size of node labels"
    )
    
    font_weight = st.sidebar.selectbox(
        "Font Weight:",
        ["400", "500", "600", "700", "800"],
        index=2,  # Default to 600
        help="Choose the font weight for labels"
    )
    
    # Layout spacing to reduce overlaps
    st.sidebar.header("📐 Layout Spacing")
    vertical_spacing = st.sidebar.slider(
        "Vertical Spacing (dx)",
        min_value=28,
        max_value=120,
        value=52,
        help="Increase if sibling nodes overlap vertically"
    )
    horizontal_spacing = st.sidebar.slider(
        "Horizontal Spacing (dy)",
        min_value=140,
        max_value=360,
        value=220,
        help="Increase if labels crowd each other horizontally"
    )
    
    st.sidebar.header("🔤 Label Options")
    label_position = st.sidebar.selectbox(
        "Label Position",
        ["Right of node", "Above node"],
        index=0,
        help="Place labels to the right (best for dense trees) or above"
    )
    label_max_width = st.sidebar.slider(
        "Label Max Width (px)",
        min_value=80,
        max_value=320,
        value=180,
        help="Long labels will wrap to multiple lines"
    )
    
    # Export quality controls
    st.sidebar.header("🖨️ Export Quality")
    png_export_scale = st.sidebar.slider(
        "PNG export scale (x)",
        min_value=1,
        max_value=6,
        value=4,
        help="Higher scale = sharper PNG for PPT (larger file size)"
    )
    svg_non_scaling_stroke = st.sidebar.checkbox(
        "SVG non-scaling strokes (crisper lines)",
        True
    )
    svg_rendering_hints = st.sidebar.checkbox(
        "SVG rendering hints (optimize legibility)",
        True
    )
    
    # Sorting & manual re-order options
    sort_mode = st.sidebar.selectbox(
        "Sort nodes by",
        [
            "None",
            "Value (High → Low)",
            "Value (Low → High)",
            "Percentage (High → Low)",
            "Percentage (Low → High)",
            "Name (A → Z)",
            "Name (Z → A)"
        ],
        index=0,
        help="Automatic sorting of sibling nodes."
    )
    manual_reorder = st.sidebar.checkbox(
        "Enable manual re-order (drag siblings)",
        False,
        help="Drag nodes at the same level to change their order. Disables auto sort while active."
    )
    
    # Map sort mode for JavaScript
    sort_mode_map = {
        "None": "none",
        "Value (High → Low)": "value_desc",
        "Value (Low → High)": "value_asc",
        "Percentage (High → Low)": "percentage_desc",
        "Percentage (Low → High)": "percentage_asc",
        "Name (A → Z)": "name_asc",
        "Name (Z → A)": "name_desc",
    }
    sort_mode_js = sort_mode_map.get(sort_mode, "none")
    manual_reorder_js = "true" if manual_reorder else "false"
    svg_non_scaling_stroke_js = "true" if svg_non_scaling_stroke else "false"
    svg_rendering_hints_js = "true" if svg_rendering_hints else "false"
    
    # Node color is derived from bottleneck percentage within the visualization (no status-based colors)
    
    agg_method = st.sidebar.selectbox("Aggregation method", ["Count", "Sum", "Average"])
    value_col = None
    if agg_method == "Count":
        df["__value__"] = 1
        value_col = "__value__"
    elif agg_method in ["Sum", "Average"]:
        value_col = st.sidebar.selectbox("Select value column", numeric_cols if numeric_cols else all_cols, index=0)
        df["__value__"] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
        value_col = "__value__"

    df = kpi_panel(df, time_comparison)

    # Check if hierarchy is empty and provide user guidance
    if not hierarchy:
        st.error("⚠️ **No columns selected for hierarchy!**")
        st.info("""
        **Please select at least one column** from the "Select hierarchy columns" dropdown in the sidebar.
        
        💡 **Tip:** The hierarchy determines how your data will be organized in the tree structure.
        - First column = Root level
        - Second column = Second level
        - And so on...
        
        **Recommended:** Start with your main categories (e.g., Project, Status, Region, etc.)
        """)
        st.stop()
    
    # Day-only mode, keep hierarchy as selected
    updated_hierarchy = list(hierarchy)
    
    tree_data = build_tree(df, updated_hierarchy, value_col, tooltip_cols, time_comparison)
    if tree_data and len(tree_data) > 0:
        if len(tree_data) == 1:
            d3_tree_data = tree_data[0]
        else:
            d3_tree_data = {
                "name": "Root",
                "children": tree_data,
                "level": -1,
                "value": sum(node.get("value", 0) for node in tree_data),
                "tooltip_data": {},
                "color": "#3B82F6",
                "raw_data": convert_pandas_to_json_serializable(df.to_dict('records'))
            }
    else:
        d3_tree_data = {"name": "No Data", "children": [], "level": 0, "value": 0, "tooltip_data": {}, "color": "#9CA3AF", "raw_data": []}

    # Convert the entire tree data to JSON serializable format
    try:
        d3_tree_data_serializable = convert_pandas_to_json_serializable(d3_tree_data)
        tree_data_json = json.dumps(d3_tree_data_serializable, ensure_ascii=False).replace('</', r'<\/')
    except Exception as e:
        st.error(f"Error converting data to JSON: {str(e)}")
        # Fallback to a simple structure without raw_data
        d3_tree_data_simple = {
            "name": d3_tree_data.get("name", "Error"),
            "children": d3_tree_data.get("children", []),
            "level": d3_tree_data.get("level", 0),
            "value": d3_tree_data.get("value", 0),
            "tooltip_data": d3_tree_data.get("tooltip_data", {}),
            "color": d3_tree_data.get("color", "#9CA3AF"),
            "raw_data": []
        }
        tree_data_json = json.dumps(d3_tree_data_simple, ensure_ascii=False).replace('</', r'<\/')

    d3_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <script src="https://d3js.org/d3.v7.min.js"></script>
      <script>
        // Node shape and size configuration
        const nodeShape = "{node_shape}";
        const nodeSize = {node_size};
        
        // Connection line configuration
        const lineWidth = {line_width};
        const lineColor = "{line_color}";
        const lineOpacity = {line_opacity};
        
        // Font configuration
        const fontSize = {font_size};
        const fontWeight = "{font_weight}";
        
        // Export quality configuration
        const exportScale = {png_export_scale};
        const svgNonScalingStroke = {svg_non_scaling_stroke_js};
        const svgRenderingHints = {svg_rendering_hints_js};

        // Bottleneck color configuration (darker = higher percentage share)
        const baseColor = "{bottleneck_base_color}";
        function getNodeFill(d) {{
          const base = d3.color(baseColor) || d3.color('#2563EB');
          const hsl = d3.hsl(base);
          const pct = Math.max(0, Math.min(100, d.data.percentage || 0)) / 100;
          const minL = 0.35, maxL = 0.82; // lightness range
          hsl.l = maxL - (maxL - minL) * pct;
          return hsl.formatHex();
        }}

        // Node shape functions
        function createNodeShape(selection, size) {{
          switch(nodeShape) {{
            case "Circle":
              selection.append("circle")
                .attr("r", size)
                .attr("fill", d => getNodeFill(d))
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
              break;
            case "Square":
              selection.append("rect")
                .attr("width", size * 2)
                .attr("height", size * 2)
                .attr("x", -size)
                .attr("y", -size)
                .attr("fill", d => getNodeFill(d))
                .attr("stroke", "#fff")
                .attr("stroke-width", 3)
                .attr("rx", 2);
              break;
            case "Diamond":
              selection.append("polygon")
                .attr("points", d => {{
                  const s = size;
                  return `0,-${{s}} ${{s}},0 0,${{s}} -${{s}},0`;
                }})
                .attr("fill", d => getNodeFill(d))
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
              break;
            case "Triangle":
              selection.append("polygon")
                .attr("points", d => {{
                  const s = size;
                  return `0,-${{s}} -${{s}},${{s}} ${{s}},${{s}}`;
                }})
                .attr("fill", d => getNodeFill(d))
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
              break;
            case "Star":
              selection.append("path")
                .attr("d", d => {{
                  const s = size;
                  const points = [];
                  for (let i = 0; i < 10; i++) {{
                    const angle = (i * Math.PI) / 5;
                    const r = i % 2 === 0 ? s : s * 0.5;
                    points.push(`${{Math.cos(angle) * r}},${{Math.sin(angle) * r}}`);
                  }}
                  return `M ${{points.join(' L ')}} Z`;
                }})
                .attr("fill", d => getNodeFill(d))
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
              break;
            case "Hexagon":
              selection.append("polygon")
                .attr("points", d => {{
                  const s = size;
                  const points = [];
                  for (let i = 0; i < 6; i++) {{
                    const angle = (i * Math.PI) / 3;
                    points.push(`${{Math.cos(angle) * s}},${{Math.sin(angle) * s}}`);
                  }}
                  return points.join(' ');
                }})
                .attr("fill", d => getNodeFill(d))
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
              break;
            case "Cross":
              selection.append("g")
                .each(function(d) {{
                  const g = d3.select(this);
                  const s = size;
                  // Vertical line
                  g.append("rect")
                    .attr("x", -2)
                    .attr("y", -s)
                    .attr("width", 4)
                    .attr("height", s * 2)
                    .attr("fill", d => getNodeFill(d))
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 3);
                  // Horizontal line
                  g.append("rect")
                    .attr("x", -s)
                    .attr("y", -2)
                    .attr("width", s * 2)
                    .attr("height", 4)
                    .attr("fill", d => getNodeFill(d))
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 3);
                }});
              break;
            case "Plus":
              selection.append("g")
                .each(function(d) {{
                  const g = d3.select(this);
                  const s = size;
                  // Vertical line
                  g.append("rect")
                    .attr("x", -2)
                    .attr("y", -s)
                    .attr("width", 4)
                    .attr("height", s * 2)
                    .attr("fill", d => getNodeFill(d))
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 3);
                  // Horizontal line
                  g.append("rect")
                    .attr("x", -s)
                    .attr("y", -2)
                    .attr("width", s * 2)
                    .attr("height", 4)
                    .attr("fill", d => getNodeFill(d))
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 3);
                }});
              break;
            default:
              selection.append("circle")
                .attr("r", size)
                .attr("fill", d => getNodeFill(d))
                .attr("stroke", "#fff")
                .attr("stroke-width", 3);
          }}
        }}
      </script>
      <style>
      .node circle {{ stroke: #fff; stroke-width: 3px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.10)); }}
      .node text {{ font-family: Calibri, Arial, sans-serif; font-size: {font_size}px; font-weight: {font_weight}; fill: #111; }}
      .link {{ fill: none; stroke: {line_color}; stroke-width: {line_width}px; stroke-opacity: {line_opacity}; }}
      .tooltip {{
        position: absolute; background: #1e293b; color: #fff;
        padding: 12px 16px; border-radius: 8px; font-size: 13px; font-family: Calibri, Arial, sans-serif;
        pointer-events: none; z-index: 1000; max-width: 320px; line-height: 1.5; box-shadow: 0 8px 32px rgba(0,0,0,0.10);
      }}
      .controls {{
        position: absolute; top: 10px; left: 10px; z-index: 1001;
        background: rgba(255,255,255,0.95); padding: 10px; border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: Calibri, Arial, sans-serif;
      }}
      .control-btn {{
        background: #3B82F6; color: white; border: none; padding: 8px 12px;
        margin: 2px; border-radius: 4px; cursor: pointer; font-size: 12px;
        transition: background 0.2s;
      }}
      .control-btn:hover {{ background: #2563EB; }}
      .control-btn:active {{ background: #1D4ED8; }}
      .zoom-info {{
        position: absolute; top: 10px; right: 10px; z-index: 1001;
        background: rgba(255,255,255,0.95); padding: 8px 12px; border-radius: 6px;
        font-size: 12px; font-family: Calibri, Arial, sans-serif;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      }}
      .download-panel {{
        position: absolute; bottom: 10px; left: 10px; z-index: 1001;
        background: rgba(255,255,255,0.95); padding: 12px; border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: Calibri, Arial, sans-serif;
        display: flex; flex-direction: column; gap: 8px;
      }}
      .download-btn {{
        background: #10B981; color: white; border: none; padding: 8px 12px;
        border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600;
        transition: background 0.2s; display: flex; align-items: center; gap: 6px;
      }}
      .download-btn:hover {{ background: #059669; }}
      .download-btn:active {{ background: #047857; }}
      .download-btn.svg {{ background: #8B5CF6; }}
      .download-btn.svg:hover {{ background: #7C3AED; }}
      .download-btn.svg:active {{ background: #6D28D9; }}
      .download-btn.transparent {{ background: #F59E0B; }}
      .download-btn.transparent:hover {{ background: #D97706; }}
      .download-btn.transparent:active {{ background: #B45309; }}
      .context-menu {{
        position: absolute; background: #1e293b; color: #fff;
        padding: 8px 0; border-radius: 8px; font-size: 13px; font-family: Calibri, Arial, sans-serif;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15); z-index: 1002; min-width: 180px;
        display: none;
      }}
      .context-menu-item {{
        padding: 8px 16px; cursor: pointer; transition: background 0.2s;
        display: flex; align-items: center; gap: 8px;
      }}
      .context-menu-item:hover {{ background: #374151; }}
      .context-menu-separator {{
        height: 1px; background: #4B5563; margin: 4px 0;
      }}
      .node-data-panel {{
        position: absolute; top: 10px; left: 50%; transform: translateX(-50%); z-index: 1001;
        background: rgba(255,255,255,0.95); padding: 12px; border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: Calibri, Arial, sans-serif;
        display: none; max-width: 400px;
      }}
      .node-data-panel h4 {{ margin: 0 0 8px 0; color: #374151; font-size: 14px; }}
      .node-data-panel .data-item {{ margin: 4px 0; font-size: 12px; }}
      .node-data-panel .data-label {{ font-weight: 600; color: #6B7280; }}
      .node-data-panel .data-value {{ color: #111; }}
      </style>
    </head>
    <body>
    <div id="tree"></div>
    <div id="contextMenu" class="context-menu">
      <div class="context-menu-item" onclick="downloadNodeData()">
        📊 Download Node Data (CSV)
      </div>
      <div class="context-menu-item" onclick="downloadNodeDataExcel()">
        📈 Download Node Data (Excel)
      </div>
      <div class="context-menu-separator"></div>
      <div class="context-menu-item" onclick="showNodeDetails()">
        🔍 Show Node Details
      </div>
      <div class="context-menu-item" onclick="downloadNodeTree()">
        🌳 Download Node Tree (JSON)
      </div>
    </div>
    <div id="nodeDataPanel" class="node-data-panel">
      <h4>📋 Node Information</h4>
      <div id="nodeDataContent"></div>
    </div>
    <div class="controls">
      <button class="control-btn" onclick="expandAll()">🔽 Expand All</button>
      <button class="control-btn" onclick="collapseAll()">🔼 Collapse All</button>
      <button class="control-btn" onclick="resetZoom()">🎯 Reset View</button>
      <div style="margin-top: 8px; font-size: 11px; color: #666;">
        <div>🖱️ Drag to pan</div>
        <div>🔍 Scroll to zoom</div>
        <div>👆 Click nodes to expand/collapse</div>
        <div>🖱️ Right-click nodes for data download</div>
      </div>
    </div>
    <div class="zoom-info" id="zoomInfo">Zoom: 100%</div>
    <div class="download-panel">
      <div style="font-size: 11px; font-weight: 600; color: #374151; margin-bottom: 4px;">📥 Download Chart</div>
      <button class="download-btn" onclick="downloadPNG()">🖼️ PNG (Complete Tree)</button>
      <button class="download-btn transparent" onclick="downloadPNGTransparent()">🖼️ PNG (White Bg)</button>
      <button class="download-btn svg" onclick="downloadSVG()">📐 SVG (Complete Tree)</button>
      <button class="download-btn svg transparent" onclick="downloadSVGTransparent()">📐 SVG (White Bg)</button>
      <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #E5E7EB;">
        <div style="font-size: 10px; color: #6B7280; margin-bottom: 4px;">Current View Export:</div>
        <button class="download-btn" onclick="downloadCurrentViewPNG()" style="font-size: 11px; padding: 6px 10px;">🖼️ PNG (Current View)</button>
        <button class="download-btn svg" onclick="downloadCurrentViewSVG()" style="font-size: 11px; padding: 6px 10px;">📐 SVG (Current View)</button>
      </div>
    </div>
    <script>
    const data = {tree_data_json};
    const width = 1100, height = 800, dx = {vertical_spacing}, dy = {horizontal_spacing};
    const tree = d3.tree().nodeSize([dx, dy]);
    const diagonal = d3.linkHorizontal().x(d => d.y).y(d => d.x);
    const root = d3.hierarchy(data);
    
    // Stable key generator for nodes based on full ancestry path
    function getNodeKey(d) {{
      if (!d) return '';
      if (d.__key) return d.__key;
      const parts = d.ancestors().reverse().map(n => (n.data && n.data.name) || 'Root');
      d.__key = parts.join(' > ');
      return d.__key;
    }}
    // Precompute stable keys for all nodes
    root.each(d => {{ getNodeKey(d); }});
    
    // Sorting configuration from Streamlit
    const sortMode = "{sort_mode_js}";
    const manualReorderEnabled = {manual_reorder_js};
    
    // Global variables for context menu
    let selectedNode = null;
    let contextMenu = null;
    let nodeDataPanel = null;
    
    // Initialize all nodes with _children for expand/collapse
    root.descendants().forEach(d => {{
      if (d.children) d._children = d.children;
      if (d.depth > 1) d.children = null; // Start collapsed for deeper levels
    }});
    
    const svg = d3.select("#tree").append("svg")
      .attr("width", width).attr("height", height)
      .attr("viewBox", [0, 0, width, height])
      .style("font", "15px Calibri");
    
    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 3])
      .on("zoom", (event) => {{
        g.attr("transform", event.transform);
        updateZoomInfo(event.transform.k);
      }});
    
    svg.call(zoom);
    
    // Center the tree by default
    const g = svg.append("g");
    const gLink = g.append("g").attr("stroke", lineColor).attr("stroke-opacity", lineOpacity);
    const gNode = g.append("g").attr("cursor", "pointer");
    const tooltip = d3.select("body").append("div").attr("class", "tooltip").style("opacity", 0);
    
    function updateZoomInfo(scale) {{
      document.getElementById("zoomInfo").textContent = `Zoom: ${{Math.round(scale * 100)}}%`;
    }}
    
    function expandAll() {{
      // Create a fresh complete tree from the original data
      const completeRoot = d3.hierarchy(data);
      
      // Recursively restore all children to the current root
      function restoreChildren(currentNode, completeNode) {{
        if (completeNode.children) {{
          currentNode._children = completeNode.children;
          currentNode.children = completeNode.children;
          
          // Recursively restore children for each child node
          currentNode.children.forEach((child, index) => {{
            if (completeNode.children[index]) {{
              restoreChildren(child, completeNode.children[index]);
            }}
          }});
        }}
      }}
      
      // Restore the complete structure
      restoreChildren(root, completeRoot);
      
      update(root);
      // Center the expanded tree
      setTimeout(() => {{
        const nodes = root.descendants();
        if (nodes.length > 0) {{
          const minX = d3.min(nodes, d => d.x);
          const maxX = d3.max(nodes, d => d.x);
          const minY = d3.min(nodes, d => d.y);
          const maxY = d3.max(nodes, d => d.y);
          const treeWidth = maxY - minY;
          const treeHeight = maxX - minX;
          const centerX = width / 2 - (minY + treeWidth / 2);
          const centerY = height / 2 - (minX + treeHeight / 2);
          svg.transition().duration(750).call(
            zoom.transform,
            d3.zoomIdentity.translate(centerX, centerY).scale(1)
          );
        }}
      }}, 100);
    }}
    
    function collapseAll() {{
      root.descendants().forEach(d => {{
        if (d.children) {{
          d._children = d.children;
          d.children = null;
        }}
      }});
      update(root);
      // Center the collapsed tree
      setTimeout(() => {{
        const nodes = root.descendants();
        if (nodes.length > 0) {{
          const minX = d3.min(nodes, d => d.x);
          const maxX = d3.max(nodes, d => d.x);
          const minY = d3.min(nodes, d => d.y);
          const maxY = d3.max(nodes, d => d.y);
          const treeWidth = maxY - minY;
          const treeHeight = maxX - minX;
          const centerX = width / 2 - (minY + treeWidth / 2);
          const centerY = height / 2 - (minX + treeHeight / 2);
          svg.transition().duration(750).call(
            zoom.transform,
            d3.zoomIdentity.translate(centerX, centerY).scale(1)
          );
        }}
      }}, 100);
    }}
    
    function resetZoom() {{
      const nodes = root.descendants();
      if (nodes.length > 0) {{
        const minX = d3.min(nodes, d => d.x);
        const maxX = d3.max(nodes, d => d.x);
        const minY = d3.min(nodes, d => d.y);
        const maxY = d3.max(nodes, d => d.y);
        const treeWidth = maxY - minY;
        const treeHeight = maxX - minX;
        const centerX = width / 2 - (minY + treeWidth / 2);
        const centerY = height / 2 - (minX + treeHeight / 2);
        svg.transition().duration(750).call(
          zoom.transform,
          d3.zoomIdentity.translate(centerX, centerY).scale(1)
        );
      }}
    }}
    
    function downloadPNG() {{
      // Create a complete tree with all nodes expanded for export
      const exportRoot = d3.hierarchy(data);
      exportRoot.descendants().forEach(d => {{
        if (d._children) d.children = d._children;
      }});
      
      // Calculate tree layout for export
      const exportTree = d3.tree().nodeSize([dx, dy]);
      exportTree(exportRoot);
      
      const nodes = exportRoot.descendants();
      if (nodes.length === 0) return;
      
      // Calculate tree bounds with tight symmetric margins
      const minX = d3.min(nodes, d => d.x);
      const maxX = d3.max(nodes, d => d.x);
      const minY = d3.min(nodes, d => d.y);
      const maxY = d3.max(nodes, d => d.y);
      const margin = 24;
      const treeWidth = (maxY - minY) + margin * 2;
      const treeHeight = (maxX - minX) + margin * 2;
      
      // Create high-resolution temporary SVG for rendering (scaled)
      const tempSvg = d3.create('svg')
        .attr('width', treeWidth * scale)
        .attr('height', treeHeight * scale)
        .attr('viewBox', `0 0 ${{treeWidth * scale}} ${{treeHeight * scale}}`)
        .attr('xmlns', 'http://www.w3.org/2000/svg');
      if (svgRenderingHints) {{
        tempSvg.append('style').text(`*{{shape-rendering:geometricPrecision; text-rendering:optimizeLegibility; image-rendering:optimizeQuality}}`);
      }}
      
      // Clone the tree structure
      const tempG = tempSvg.append('g')
        .attr('transform', `translate(${{(-minY + margin) * scale}}, ${{(-minX + margin) * scale}}) scale(${{scale}})`);
      
      // Use the already calculated export tree
      const tempLinks = exportRoot.links();
      tempG.selectAll('path')
        .data(tempLinks)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity);
      
      // Render nodes
      const tempNodes = exportRoot.descendants();
      const nodeGroups = tempG.selectAll('g')
        .data(tempNodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')  // Position text above the node
        .attr('x', 0)           // Center align horizontally
        .attr('text-anchor', 'middle')  // Center align the text
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => d.data.name + (d.data.value ? ` (${{d.data.value}}, ${{d.data.percentage}}%)` : ''));

      // Compute tight bounds including text and adjust SVG/canvas sizes
      const bbox = tempG.node().getBBox();
      const contentWidth = bbox.width;
      const contentHeight = bbox.height;
      const scale = exportScale; // user-controlled scale for crisp images
      const finalPixelWidth = Math.ceil((contentWidth + margin * 2) * scale);
      const finalPixelHeight = Math.ceil((contentHeight + margin * 2) * scale);
      tempG.attr('transform', `translate(${{(-bbox.x + margin) * scale}}, ${{(-bbox.y + margin) * scale}}) scale(${{scale}})`);
      tempSvg.attr('width', finalPixelWidth).attr('height', finalPixelHeight).attr('viewBox', `0 0 ${{finalPixelWidth}} ${{finalPixelHeight}}`);

      // Create high-resolution canvas after measuring
      const canvas = document.createElement('canvas');
      canvas.width = finalPixelWidth;
      canvas.height = finalPixelHeight;
      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = true;
      if (ctx.imageSmoothingQuality) ctx.imageSmoothingQuality = 'high';
      
      // Convert SVG to data URL and download
      const svgData = new XMLSerializer().serializeToString(tempSvg.node());
      const svgBlob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(svgBlob);
      
      const img = new Image();
      img.onload = function() {{
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function(blob) {{
          const link = document.createElement('a');
          link.download = `decomposition_tree_${{new Date().toISOString().slice(0,10)}}.png`;
          link.href = URL.createObjectURL(blob);
          link.click();
          URL.revokeObjectURL(url);
          URL.revokeObjectURL(link.href);
        }}, 'image/png', 1.0);
      }};
      img.src = url;
    }}
    
    function downloadPNGTransparent() {{
      // Create a complete tree with all nodes expanded for export
      const exportRoot = d3.hierarchy(data);
      exportRoot.descendants().forEach(d => {{
        if (d._children) d.children = d._children;
      }});
      
      // Calculate tree layout for export
      const exportTree = d3.tree().nodeSize([dx, dy]);
      exportTree(exportRoot);
      
      const nodes = exportRoot.descendants();
      if (nodes.length === 0) return;
      
      // Calculate tree bounds with tight symmetric margins
      const minX = d3.min(nodes, d => d.x);
      const maxX = d3.max(nodes, d => d.x);
      const minY = d3.min(nodes, d => d.y);
      const maxY = d3.max(nodes, d => d.y);
      const margin = 24;
      const treeWidth = (maxY - minY) + margin * 2;
      const treeHeight = (maxX - minX) + margin * 2;
      
      // Create high-resolution temporary SVG for rendering (scaled)
      const tempSvg = d3.create('svg')
        .attr('width', treeWidth * scale)
        .attr('height', treeHeight * scale)
        .attr('viewBox', `0 0 ${{treeWidth * scale}} ${{treeHeight * scale}}`)
        .attr('xmlns', 'http://www.w3.org/2000/svg')
        .style('background', '#ffffff');
      if (svgRenderingHints) {{
        tempSvg.append('style').text(`*{{shape-rendering:geometricPrecision; text-rendering:optimizeLegibility; image-rendering:optimizeQuality}}`);
      }}
      
      // Clone the tree structure
      const tempG = tempSvg.append('g')
        .attr('transform', `translate(${{(-minY + margin) * scale}}, ${{(-minX + margin) * scale}}) scale(${{scale}})`);
      
      // Use the already calculated export tree
      const tempLinks = exportRoot.links();
      tempG.selectAll('path')
        .data(tempLinks)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity);
      
      // Render nodes
      const tempNodes = exportRoot.descendants();
      const nodeGroups = tempG.selectAll('g')
        .data(tempNodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')  // Position text above the node
        .attr('x', 0)           // Center align horizontally
        .attr('text-anchor', 'middle')  // Center align the text
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => d.data.name + (d.data.value ? ` (${{d.data.value}}, ${{d.data.percentage}}%)` : ''));

      // Compute tight bounds including text and adjust SVG/canvas sizes
      const bbox = tempG.node().getBBox();
      const contentWidth = bbox.width;
      const contentHeight = bbox.height;
      const scale = exportScale; // user-controlled scale for crisp images
      const finalPixelWidth = Math.ceil((contentWidth + margin * 2) * scale);
      const finalPixelHeight = Math.ceil((contentHeight + margin * 2) * scale);
      tempG.attr('transform', `translate(${{(-bbox.x + margin) * scale}}, ${{(-bbox.y + margin) * scale}}) scale(${{scale}})`);
      tempSvg.attr('width', finalPixelWidth).attr('height', finalPixelHeight).attr('viewBox', `0 0 ${{finalPixelWidth}} ${{finalPixelHeight}}`);

      // Create high-resolution canvas after measuring (white background)
      const canvas = document.createElement('canvas');
      canvas.width = finalPixelWidth;
      canvas.height = finalPixelHeight;
      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = true;
      if (ctx.imageSmoothingQuality) ctx.imageSmoothingQuality = 'high';
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Convert SVG to data URL and download
      const svgData = new XMLSerializer().serializeToString(tempSvg.node());
      const svgBlob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(svgBlob);
      
      const img = new Image();
      img.onload = function() {{
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function(blob) {{
          const link = document.createElement('a');
          link.download = `decomposition_tree_transparent_${{new Date().toISOString().slice(0,10)}}.png`;
          link.href = URL.createObjectURL(blob);
          link.click();
          URL.revokeObjectURL(url);
          URL.revokeObjectURL(link.href);
        }}, 'image/png', 1.0);
      }};
      img.src = url;
    }}
    
    function downloadSVG() {{
      // Create a complete tree with all nodes expanded for export
      const exportRoot = d3.hierarchy(data);
      exportRoot.descendants().forEach(d => {{
        if (d._children) d.children = d._children;
      }});
      
      // Calculate tree layout for export
      const exportTree = d3.tree().nodeSize([dx, dy]);
      exportTree(exportRoot);
      
      const nodes = exportRoot.descendants();
      if (nodes.length === 0) return;
      
      // Calculate tree bounds with tight symmetric margins
      const minX = d3.min(nodes, d => d.x);
      const maxX = d3.max(nodes, d => d.x);
      const minY = d3.min(nodes, d => d.y);
      const maxY = d3.max(nodes, d => d.y);
      const margin = 24;
      const treeWidth = (maxY - minY) + margin * 2;
      const treeHeight = (maxX - minX) + margin * 2;
      
      // Create SVG with transparent background
      const svg = d3.create('svg')
        .attr('width', treeWidth)
        .attr('height', treeHeight)
        .attr('viewBox', `0 0 ${{treeWidth}} ${{treeHeight}}`)
        .attr('xmlns', 'http://www.w3.org/2000/svg');
      if (svgRenderingHints) {{
        svg.append('style').text(`*{{shape-rendering:geometricPrecision; text-rendering:optimizeLegibility; image-rendering:optimizeQuality}}`);
      }}
      
      // Clone the tree structure
      const g = svg.append('g')
        .attr('transform', `translate(${{-minY + margin}}, ${{-minX + margin}})`);
      
      // Use the already calculated export tree
      const links = exportRoot.links();
      g.selectAll('path')
        .data(links)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity)
        .attr('vector-effect', svgNonScalingStroke ? 'non-scaling-stroke' : null);
      
      // Render nodes
      const tempNodes = exportRoot.descendants();
      const nodeGroups = g.selectAll('g')
        .data(tempNodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      if (svgNonScalingStroke) {{
        nodeGroups.selectAll('circle,rect,polygon,path').attr('vector-effect', 'non-scaling-stroke');
      }}
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')  // Position text above the node
        .attr('x', 0)           // Center align horizontally
        .attr('text-anchor', 'middle')  // Center align the text
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => d.data.name + (d.data.value ? ` (${{d.data.value}}, ${{d.data.percentage}}%)` : ''));
      
      // Compute tight bounds and set viewBox so content is centered and tightly fit
      const bbox = g.node().getBBox();
      svg.attr('viewBox', `${{bbox.x - margin}} ${{bbox.y - margin}} ${{bbox.width + 2*margin}} ${{bbox.height + 2*margin}}`);
      
      // Download SVG
      const svgData = new XMLSerializer().serializeToString(svg.node());
      const blob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.download = `decomposition_tree_${{new Date().toISOString().slice(0,10)}}.svg`;
      link.href = url;
      link.click();
      URL.revokeObjectURL(url);
    }}
    
    function downloadSVGTransparent() {{
      // Create a complete tree with all nodes expanded for export
      const exportRoot = d3.hierarchy(data);
      exportRoot.descendants().forEach(d => {{
        if (d._children) d.children = d._children;
      }});
      
      // Calculate tree layout for export
      const exportTree = d3.tree().nodeSize([dx, dy]);
      exportTree(exportRoot);
      
      const nodes = exportRoot.descendants();
      if (nodes.length === 0) return;
      
      // Calculate tree bounds with tight symmetric margins
      const minX = d3.min(nodes, d => d.x);
      const maxX = d3.max(nodes, d => d.x);
      const minY = d3.min(nodes, d => d.y);
      const maxY = d3.max(nodes, d => d.y);
      const margin = 24;
      const treeWidth = (maxY - minY) + margin * 2;
      const treeHeight = (maxX - minX) + margin * 2;
      
      // Create SVG with white background
      const svg = d3.create('svg')
        .attr('width', treeWidth)
        .attr('height', treeHeight)
        .attr('viewBox', `0 0 ${{treeWidth}} ${{treeHeight}}`)
        .attr('xmlns', 'http://www.w3.org/2000/svg')
        .style('background', '#ffffff');
      if (svgRenderingHints) {{
        svg.append('style').text(`*{{shape-rendering:geometricPrecision; text-rendering:optimizeLegibility; image-rendering:optimizeQuality}}`);
      }}
      
      // Add white background rectangle (kept, viewBox will be adjusted later)
      svg.append('rect')
        .attr('width', '100%')
        .attr('height', '100%')
        .attr('fill', '#ffffff');
      
      // Clone the tree structure
      const g = svg.append('g')
        .attr('transform', `translate(${{-minY + margin}}, ${{-minX + margin}})`);
      
      // Use the already calculated export tree
      const links = exportRoot.links();
      g.selectAll('path')
        .data(links)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity)
        .attr('vector-effect', svgNonScalingStroke ? 'non-scaling-stroke' : null);
      
      // Render nodes
      const tempNodes = exportRoot.descendants();
      const nodeGroups = g.selectAll('g')
        .data(tempNodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      if (svgNonScalingStroke) {{
        nodeGroups.selectAll('circle,rect,polygon,path').attr('vector-effect', 'non-scaling-stroke');
      }}
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')  // Position text above the node
        .attr('x', 0)           // Center align horizontally
        .attr('text-anchor', 'middle')  // Center align the text
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => d.data.name + (d.data.value ? ` (${{d.data.value}}, ${{d.data.percentage}}%)` : ''));
      
      // Compute tight bounds and set viewBox to fit content + margin
      const bbox = g.node().getBBox();
      svg.attr('viewBox', `${{bbox.x - margin}} ${{bbox.y - margin}} ${{bbox.width + 2*margin}} ${{bbox.height + 2*margin}}`);
      
      // Download SVG
      const svgData = new XMLSerializer().serializeToString(svg.node());
      const blob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.download = `decomposition_tree_transparent_${{new Date().toISOString().slice(0,10)}}.svg`;
      link.href = url;
      link.click();
      URL.revokeObjectURL(url);
    }}
    
    // New functions for current view export
    function downloadCurrentViewPNG() {{
      // Use the current tree state (with collapsed/expanded nodes as they are)
      const currentRoot = root.copy();
      
      // Calculate tree layout for current view
      const currentTree = d3.tree().nodeSize([dx, dy]);
      currentTree(currentRoot);
      
      const nodes = currentRoot.descendants();
      if (nodes.length === 0) return;
      
      // Calculate tree bounds with tight symmetric margins
      const minX = d3.min(nodes, d => d.x);
      const maxX = d3.max(nodes, d => d.x);
      const minY = d3.min(nodes, d => d.y);
      const maxY = d3.max(nodes, d => d.y);
      const margin = 24;
      const treeWidth = (maxY - minY) + margin * 2;
      const treeHeight = (maxX - minX) + margin * 2;
      
      // Create high-resolution canvas
      const scale = exportScale; // use configured scale for crisp images
      const canvas = document.createElement('canvas');
      canvas.width = treeWidth * scale;
      canvas.height = treeHeight * scale;
      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = true;
      if (ctx.imageSmoothingQuality) ctx.imageSmoothingQuality = 'high';
      
      // Clear canvas (transparent background)
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Create high-resolution temporary SVG for rendering
      const tempSvg = d3.create('svg')
        .attr('width', treeWidth * scale)
        .attr('height', treeHeight * scale)
        .attr('viewBox', `0 0 ${{treeWidth * scale}} ${{treeHeight * scale}}`)
        .attr('xmlns', 'http://www.w3.org/2000/svg');
      // Rendering hints skipped to simplify export markup
      
      // Clone the tree structure
      const tempG = tempSvg.append('g')
        .attr('transform', `translate(${{(-minY + margin) * scale}}, ${{(-minX + margin) * scale}}) scale(${{scale}})`);
      
      // Use the current tree links
      const currentLinks = currentRoot.links();
      tempG.selectAll('path')
        .data(currentLinks)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity);
      
      // Render nodes
      const nodeGroups = tempG.selectAll('g')
        .data(nodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')
        .attr('x', 0)
        .attr('text-anchor', 'middle')
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => d.data.name + (d.data.value ? ` (${{d.data.value}}, ${{d.data.percentage}}%)` : ''));
      
      // Convert SVG to data URL and download
      const svgData = new XMLSerializer().serializeToString(tempSvg.node());
      const svgBlob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(svgBlob);
      
      const img = new Image();
      img.onload = function() {{
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function(blob) {{
          const link = document.createElement('a');
          link.download = `decomposition_tree_current_view_${{new Date().toISOString().slice(0,10)}}.png`;
          link.href = URL.createObjectURL(blob);
          link.click();
          URL.revokeObjectURL(url);
          URL.revokeObjectURL(link.href);
        }}, 'image/png', 1.0);
      }};
      img.src = url;
    }}
    
    function downloadCurrentViewSVG() {{
      // Use the current tree state (with collapsed/expanded nodes as they are)
      const currentRoot = root.copy();
      
      // Calculate tree layout for current view
      const currentTree = d3.tree().nodeSize([dx, dy]);
      currentTree(currentRoot);
      
      const nodes = currentRoot.descendants();
      if (nodes.length === 0) return;
      
      // Calculate tree bounds with tight symmetric margins
      const minX = d3.min(nodes, d => d.x);
      const maxX = d3.max(nodes, d => d.x);
      const minY = d3.min(nodes, d => d.y);
      const maxY = d3.max(nodes, d => d.y);
      const margin = 24;
      const treeWidth = (maxY - minY) + margin * 2;
      const treeHeight = (maxX - minX) + margin * 2;
      
      // Create SVG with transparent background
      const svg = d3.create('svg')
        .attr('width', treeWidth)
        .attr('height', treeHeight)
        .attr('viewBox', `0 0 ${{treeWidth}} ${{treeHeight}}`)
        .attr('xmlns', 'http://www.w3.org/2000/svg');
      
      // Clone the tree structure
      const g = svg.append('g')
        .attr('transform', `translate(${{-minY + margin}}, ${{-minX + margin}})`);
      
      // Use the current tree links
      const links = currentRoot.links();
      g.selectAll('path')
        .data(links)
        .enter().append('path')
        .attr('d', diagonal)
        .attr('fill', 'none')
        .attr('stroke', lineColor)
        .attr('stroke-width', lineWidth)
        .attr('stroke-opacity', lineOpacity);
      
      // Render nodes
      const nodeGroups = g.selectAll('g')
        .data(nodes)
        .enter().append('g')
        .attr('transform', d => `translate(${{d.y}}, ${{d.x}})`);
      
      // Use custom node shapes for export
      nodeGroups.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      // Add text with clean styling and proper positioning
      nodeGroups.append('text')
        .attr('dy', '-0.5em')
        .attr('x', 0)
        .attr('text-anchor', 'middle')
        .attr('font-family', 'Calibri, Arial, sans-serif')
        .attr('font-size', fontSize + 'px')
        .attr('font-weight', fontWeight)
        .attr('fill', '#111')
        .text(d => d.data.name + (d.data.value ? ` (${{d.data.value}}, ${{d.data.percentage}}%)` : ''));
      
      // Compute tight bounds and set viewBox to fit content + margin
      const bbox = g.node().getBBox();
      svg.attr('viewBox', `${{bbox.x - margin}} ${{bbox.y - margin}} ${{bbox.width + 2*margin}} ${{bbox.height + 2*margin}}`);
      
      // Download SVG
      const svgData = new XMLSerializer().serializeToString(svg.node());
      const blob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.download = `decomposition_tree_current_view_${{new Date().toISOString().slice(0,10)}}.svg`;
      link.href = url;
      link.click();
      URL.revokeObjectURL(url);
    }}
    
    // Context menu functions
    function showContextMenu(event, node) {{
      event.preventDefault();
      selectedNode = node;
      
      if (!contextMenu) {{
        contextMenu = document.getElementById('contextMenu');
        nodeDataPanel = document.getElementById('nodeDataPanel');
      }}
      
      contextMenu.style.display = 'block';
      contextMenu.style.left = event.pageX + 'px';
      contextMenu.style.top = event.pageY + 'px';
    }}
    
    function hideContextMenu() {{
      if (contextMenu) {{
        contextMenu.style.display = 'none';
      }}
      if (nodeDataPanel) {{
        nodeDataPanel.style.display = 'none';
      }}
    }}
    
    function downloadNodeData() {{
      if (!selectedNode) return;
      
      // Get all data for this node and its descendants
      const nodeData = getNodeData(selectedNode);
      
      // Convert to CSV
      const csvContent = convertToCSV(nodeData);
      
      // Download CSV
      const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `node_data_${{selectedNode.data.name.replace(/[^a-zA-Z0-9]/g, '_')}}_${{new Date().toISOString().slice(0,10)}}.csv`;
      link.click();
      URL.revokeObjectURL(link.href);
      
      hideContextMenu();
    }}
    
    function downloadNodeDataExcel() {{
      if (!selectedNode) return;
      
      // Get all data for this node and its descendants
      const nodeData = getNodeData(selectedNode);
      
      // Convert to Excel format (CSV with BOM for Excel compatibility)
      const csvContent = '\ufeff' + convertToCSV(nodeData);
      
      // Download Excel
      const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `node_data_${{selectedNode.data.name.replace(/[^a-zA-Z0-9]/g, '_')}}_${{new Date().toISOString().slice(0,10)}}.xlsx`;
      link.click();
      URL.revokeObjectURL(link.href);
      
      hideContextMenu();
    }}
    
    function showNodeDetails() {{
      if (!selectedNode || !nodeDataPanel) return;
      
      const nodeData = getNodeData(selectedNode);
      const content = document.getElementById('nodeDataContent');
      
      let html = `<div class="data-item"><span class="data-label">Node:</span> <span class="data-value">${{selectedNode.data.name}}</span></div>`;
      html += `<div class="data-item"><span class="data-label">Value:</span> <span class="data-value">${{selectedNode.data.value || 0}}</span></div>`;
      html += `<div class="data-item"><span class="data-label">Records:</span> <span class="data-value">${{nodeData.length}}</span></div>`;
      
      // Show tooltip data
      if (selectedNode.data.tooltip_data) {{
        for (const [key, value] of Object.entries(selectedNode.data.tooltip_data)) {{
          html += `<div class="data-item"><span class="data-label">${{key}}:</span> <span class="data-value">${{value}}</span></div>`;
        }}
      }}
      
      content.innerHTML = html;
      nodeDataPanel.style.display = 'block';
      
      // Auto-hide after 5 seconds
      setTimeout(() => {{
        nodeDataPanel.style.display = 'none';
      }}, 5000);
      
      hideContextMenu();
    }}
    
    function downloadNodeTree() {{
      if (!selectedNode) return;
      
      // Get the subtree structure
      const subtree = getNodeSubtree(selectedNode);
      
      // Download JSON
      const jsonContent = JSON.stringify(subtree, null, 2);
      const blob = new Blob([jsonContent], {{ type: 'application/json;charset=utf-8;' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `node_tree_${{selectedNode.data.name.replace(/[^a-zA-Z0-9]/g, '_')}}_${{new Date().toISOString().slice(0,10)}}.json`;
      link.click();
      URL.revokeObjectURL(link.href);
      
      hideContextMenu();
    }}
    
    function getNodeData(node) {{
      // This function would need to be implemented based on your data structure
      // For now, we'll return a placeholder that shows the node's aggregated data
      const data = [];
      
      // Add the node's own data
      if (node.data.raw_data) {{
        data.push(...node.data.raw_data);
      }}
      
      // Add data from all descendants
      node.descendants().forEach(descendant => {{
        if (descendant !== node && descendant.data.raw_data) {{
          data.push(...descendant.data.raw_data);
        }}
      }});
      
      return data;
    }}
    
    function getNodeSubtree(node) {{
      // Create a clean subtree structure for JSON export
      const subtree = {{
        name: node.data.name,
        value: node.data.value,
        level: node.data.level,
        column: node.data.column,
        node_value: node.data.node_value,
        color: node.data.color,
        tooltip_data: node.data.tooltip_data,
        children: []
      }};
      
      if (node.children) {{
        node.children.forEach(child => {{
          subtree.children.push(getNodeSubtree(child));
        }});
      }}
      
      return subtree;
    }}
    
    function convertToCSV(data) {{
      if (!data || data.length === 0) {{
        return "No data available for this node";
      }}
      
      // Get all unique keys from the data
      const keys = new Set();
      data.forEach(item => {{
        Object.keys(item).forEach(key => keys.add(key));
      }});
      
      const headers = Array.from(keys);
      const csvRows = [headers.join(',')];
      
      data.forEach(item => {{
        const row = headers.map(header => {{
          const value = item[header] || '';
          // Escape commas and quotes in CSV
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {{
            return `"${{value.replace(/"/g, '""')}}"`;
          }}
          return value;
        }});
        csvRows.push(row.join(','));
      }});
      
      return csvRows.join('\\n');
    }}
    
    // Hide context menu when clicking elsewhere
    document.addEventListener('click', hideContextMenu);
    
    function applySort(node) {{
      if (!node || !node.children) return;
      switch (sortMode) {{
        case 'value_desc':
          node.children.sort((a,b) => (b.data.value||0) - (a.data.value||0));
          break;
        case 'value_asc':
          node.children.sort((a,b) => (a.data.value||0) - (b.data.value||0));
          break;
        case 'percentage_desc':
          node.children.sort((a,b) => (b.data.percentage||0) - (a.data.percentage||0));
          break;
        case 'percentage_asc':
          node.children.sort((a,b) => (a.data.percentage||0) - (b.data.percentage||0));
          break;
        case 'name_asc':
          node.children.sort((a,b) => (a.data.name||'').localeCompare(b.data.name||''));
          break;
        case 'name_desc':
          node.children.sort((a,b) => (b.data.name||'').localeCompare(a.data.name||''));
          break;
        default:
          break;
      }}
      node.children.forEach(applySort);
    }}

    function wrapText(textSel, width) {{
      textSel.each(function() {{
        const text = d3.select(this);
        const words = text.text().split(/\s+/).reverse();
        let line = [], lineNumber = 0;
        const lineHeight = 1.2; // ems
        const y = text.attr('y');
        const dyTxt = parseFloat(text.attr('dy')) || 0;
        let tspan = text.text(null).append('tspan').attr('x', 0).attr('y', y).attr('dy', dyTxt + 'em');
        let word;
        while (word = words.pop()) {{
          line.push(word);
          tspan.text(line.join(' '));
          if (tspan.node().getComputedTextLength() > width) {{
            line.pop();
            tspan.text(line.join(' '));
            line = [word];
            tspan = text.append('tspan').attr('x', 0).attr('y', y).attr('dy', ++lineNumber * lineHeight + dyTxt + 'em').text(word);
          }}
        }}
      }});
    }}

    function update(source) {{
      if (!manualReorderEnabled && sortMode !== 'none') {{
        applySort(root);
      }}
      tree(root);
      const nodes = root.descendants();
      const links = root.links();
      
      // Update links
      const link = gLink.selectAll("path").data(links, d => getNodeKey(d.target));
      link.enter().append("path")
        .attr("class", "link")
        .attr("d", diagonal)
        .attr("stroke-width", lineWidth)
        .merge(link)
        .transition().duration(750)
        .attr("d", diagonal)
        .attr("stroke-width", lineWidth);
      link.exit().remove();
      
      // Update nodes
      const node = gNode.selectAll("g").data(nodes, d => getNodeKey(d));
      
      // Enter new nodes
      const nodeEnter = node.enter().append("g")
        .attr("class", "node")
        .attr("transform", d => `translate(${{source.y0 || 0}},${{source.x0 || 0}})`)
        .on("click", (event, d) => {{
          if (window.__draggingNode) return; // prevent toggle when dragging
          if (d._children) {{
            d.children = d.children ? null : d._children;
          }}
          update(d);
        }})
        .on("contextmenu", (event, d) => {{
          showContextMenu(event, d);
        }})
        .on("mouseover", (event, d) => {{
          let t = `<b>${{d.data.name}}</b><br>`;
          for (const [k,v] of Object.entries(d.data.tooltip_data||{{}}))
            t += `${{k}}: <span style='color:#38bdf8;font-weight:600'>${{v}}</span><br>`;
          tooltip.transition().duration(200).style("opacity", .95);
          tooltip.html(t).style("left", (event.pageX+15) + "px").style("top", (event.pageY-20) + "px");
        }})
        .on("mouseout", () => tooltip.transition().duration(400).style("opacity", 0));
      
      // Add shapes to new nodes using the custom shape function and enable drag for manual reordering
      nodeEnter.each(function(d) {{
        createNodeShape(d3.select(this), nodeSize);
      }});
      
      if (manualReorderEnabled) {{
        const drag = d3.drag()
          .on('start', (event, d) => {{
            window.__draggingNode = true;
            d3.select(event.sourceEvent.target.closest('g.node')).raise();
          }})
          .on('drag', (event, d) => {{
            // Follow pointer vertically for clearer feedback
            const pointer = d3.pointer(event, g.node());
            const pointerY = pointer[1];
            const nodeEl = d3.select(event.sourceEvent.target.closest('g.node'));
            nodeEl.attr('transform', `translate(${{d.y}},${{pointerY}})`);
          }})
          .on('end', (event, d) => {{
            const parent = d.parent;
            if (parent && parent.children) {{
              // Determine new index using midpoints between sibling centers
              const pointer = d3.pointer(event, g.node());
              const pointerY = pointer[1];
              const siblings = parent.children.slice().sort((a,b) => a.x - b.x);
              const currentIndex = siblings.indexOf(d);
              const centers = siblings.map(s => s.x);
              let newIndex = centers.length - 1;
              for (let i = 0; i < centers.length - 1; i++) {{
                const mid = (centers[i] + centers[i+1]) / 2;
                if (pointerY < mid) {{ newIndex = i; break; }}
              }}
              newIndex = Math.max(0, Math.min(newIndex, siblings.length - 1));
              if (newIndex !== currentIndex) {{
                parent.children.splice(currentIndex, 1);
                parent.children.splice(newIndex, 0, d);
                // Keep hidden children order in sync if present
                if (parent._children) {{
                  const keyOrder = parent.children.map(getNodeKey);
                  parent._children.sort((a,b) => keyOrder.indexOf(getNodeKey(a)) - keyOrder.indexOf(getNodeKey(b)));
                }}
              }}
            }}
            window.__draggingNode = false;
            update(parent || d);
          }});
        nodeEnter.call(drag);
      }}
      
      // Add text to new nodes with clean styling and proper positioning
      const label = nodeEnter.append("text")
        .attr("font-family", "Calibri, Arial, sans-serif")
        .attr("font-size", fontSize + "px")
        .attr("font-weight", fontWeight)
        .attr("fill", "#111")
        .attr("pointer-events", "none")
        .text(d => d.data.name + (d.data.value ? ` (${{d.data.value}}, ${{d.data.percentage}}%)` : ""));

      if ("{label_position}" === "Right of node") {{
        label
          .attr("dy", "0.32em")
          .attr("x", nodeSize + 8)
          .attr("text-anchor", "start")
          .call(wrapText, {label_max_width});
      }} else {{
        label
          .attr("dy", "-0.8em")
          .attr("x", 0)
          .attr("text-anchor", "middle")
          .call(wrapText, {label_max_width});
      }}
      
      // After labels are created and wrapped, nudge labels to avoid vertical overlaps (right-of-node mode)
      if ("{label_position}" === "Right of node") {{
        const padding = 2;
        const labelsArr = [];
        gNode.selectAll('g.node text').each(function(nd) {{
          const selElem = d3.select(this);
          const bbox = this.getBBox();
          labelsArr.push({{ sel: selElem, y: nd.x, height: bbox.height, baseY: parseFloat(selElem.attr('y')) || 0 }});
        }});
        labelsArr.sort((a,b) => a.y - b.y);
        let lastBottom = -Infinity;
        labelsArr.forEach(l => {{
          const desiredTop = l.y - l.height / 2;
          const newTop = Math.max(desiredTop, lastBottom + padding);
          const shift = newTop - desiredTop;
          l.sel.attr('y', l.baseY + shift);
          lastBottom = newTop + l.height;
        }});
      }}

      // Update existing nodes
      node.merge(nodeEnter)
        .transition().duration(700)
        .attr("transform", d => `translate(${{d.y}},${{d.x}})`);
      
      // Remove old nodes
      node.exit().remove();
      
      // Store positions for next update
      root.each(d => {{ d.x0 = d.x; d.y0 = d.y; }});
    }}
    
    // Initial update
    update(root);
    
    // Center the tree initially
    setTimeout(() => {{
      const nodes = root.descendants();
      if (nodes.length > 0) {{
        const minX = d3.min(nodes, d => d.x);
        const maxX = d3.max(nodes, d => d.x);
        const minY = d3.min(nodes, d => d.y);
        const maxY = d3.max(nodes, d => d.y);
        const treeWidth = maxY - minY;
        const treeHeight = maxX - minX;
        const centerX = width / 2 - (minY + treeWidth / 2);
        const centerY = height / 2 - (minX + treeHeight / 2);
        svg.call(zoom.transform, d3.zoomIdentity.translate(centerX, centerY).scale(1));
      }}
    }}, 100);
    </script>
    </body>
    </html>
    """
    st.header("🎯 Interactive Decomposition Tree")
    st.markdown("*Color intensity shows bottlenecks: darker nodes represent higher share (%).*")
    st.info("💡 **Right-click on any node** to download data, view details, or export the subtree structure!")
    
    # Add export explanation
    with st.expander("📥 Export Options Explained"):
        st.markdown("""
        **Export Options:**
        
        🖼️ **Complete Tree Export** (PNG/SVG):
        - Shows ALL nodes expanded regardless of current view
        - Best for comprehensive reports and data sharing
        - Ensures no information is missed
        
        🖼️ **Current View Export** (PNG/SVG):
        - Shows only what you currently see (expanded/collapsed state)
        - Best for focused presentations and specific analysis
        - Respects your current tree navigation
        
        **Recommendation:** Use "Complete Tree" for official reports and "Current View" for focused presentations.
        """)
    
    # Day-only mode: hide Week/Month debug sections
    st.components.v1.html(d3_html, height=900)
    csv = df.to_csv(index=False)
    st.sidebar.download_button("📥 Download All Data CSV", csv, "all_sites.csv", "text/csv")
else:
    st.info("Please upload an Excel file to start analysis.")
