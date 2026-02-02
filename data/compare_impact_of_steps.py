# Jupyter Notebook: Comparative Analysis of Metrics Across Multiple Setups
# CSV filenames match the standardized metric names exactly

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import gridspec
import warnings
from scipy import stats
warnings.filterwarnings('ignore')

# Set plot style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Configuration - UPDATE THESE BASED ON YOUR DATA
SETUPS_DIR = "./"  # Base directory containing setup folders
SETUP_NAMES = ["step_reuse_1000_baremetal_2026_01_30_17_10_11_5eed1ca3", "step_reuse_1000_baremetal_2026_01_30_17_18_33_4af725a0", "step_reuse_1000_baremetal_2026_01_30_17_22_48_bb1af4b5", "step_reuse_1000_baremetal_2026_01_30_17_36_04_23dd2ec9"]  # Your setup folder names

# List of all metric names based on your YAML
METRIC_NAMES = [
    # System and Kepler metrics
    "system_cpu_usage",
    "kepler_pod_cpu_power_watts",
    "kepler_pod_cpu_energy_joules",
    "cpu_usage_seconds_delta",
    "kepler_all_pod_cpu_power_watts",
    "kepler_all_pod_cpu_energy_joules",
    "kepler_node_cpu_power_raw",
    "kepler_node_cpu_power_sum",
    "wall_power",
    "apiserver_request_rate",
    "apiserver_latency_95th",
    "pod_memory_usage",
    "pod_network_receive_bytes",
    "pod_network_transmit_bytes",
    
    # Argo metrics
    "argo_workflows_total_created",
    "argo_workflows_error_count",
    "argo_workflows_operation_duration_p95",
    "argo_workflows_completed_by_phase",
    "argo_workflows_pods_created",
    "argo_workflows_average_queue_latency",
    "argo_workflows_workers_busy",
    "argo_workflows_queue_adds_rate",
    "argo_workflows_k8s_requests_rate"
]

def load_metric_from_csv(setup_path, metric_name):
    """
    Load a specific metric CSV file
    """
    csv_path = os.path.join(setup_path, f"{metric_name}.csv")
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            return df
        except Exception as e:
            print(f"    ✗ Error loading {metric_name}.csv: {e}")
            return None
    else:
        return None

def load_all_metrics(setup_names, base_dir):
    """
    Load all metrics from all setups
    """
    all_data = {}
    
    for setup in setup_names:
        setup_path = os.path.join(base_dir, setup)
        if not os.path.exists(setup_path):
            print(f"Warning: Setup directory '{setup_path}' not found. Skipping...")
            continue
            
        print(f"\n📂 Loading data for {setup}...")
        print(f"Directory: {setup_path}")
        
        setup_data = {}
        
        for metric_name in METRIC_NAMES:
            df = load_metric_from_csv(setup_path, metric_name)
            
            if df is not None and not df.empty:
                print(f"  ✓ Loaded: {metric_name}.csv ({len(df)} rows)")
                
                # Extract values from CSV
                # Assuming CSV has at least one column with numeric data
                if 'value' in df.columns:
                    values = df['value']
                elif 'Value' in df.columns:
                    values = df['Value']
                elif len(df.columns) == 1:
                    values = df.iloc[:, 0]
                else:
                    # Try to find a numeric column
                    numeric_cols = df.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        values = df[numeric_cols[0]]
                    else:
                        print(f"    ⚠ Warning: No numeric data found in {metric_name}.csv")
                        continue
                
                # Calculate statistics
                valid_values = values.dropna()
                if len(valid_values) > 0:
                    setup_data[metric_name] = {
                        'values': valid_values.values,
                        'mean': valid_values.mean(),
                        'std': valid_values.std(),
                        'min': valid_values.min(),
                        'max': valid_values.max(),
                        'median': valid_values.median(),
                        'q25': valid_values.quantile(0.25),
                        'q75': valid_values.quantile(0.75),
                        'file': f"{metric_name}.csv",
                        'sample_size': len(valid_values),
                        'full_data': df
                    }
                else:
                    print(f"    ⚠ Warning: No valid numeric values in {metric_name}.csv")
            else:
                print(f"  ✗ Missing: {metric_name}.csv")
        
        all_data[setup] = setup_data
    
    return all_data

def create_summary_dataframe(all_data):
    """
    Create summary DataFrames for each metric category
    """
    # Create DataFrames for statistics
    mean_df = pd.DataFrame(index=all_data.keys(), columns=METRIC_NAMES)
    std_df = pd.DataFrame(index=all_data.keys(), columns=METRIC_NAMES)
    median_df = pd.DataFrame(index=all_data.keys(), columns=METRIC_NAMES)
    count_df = pd.DataFrame(index=all_data.keys(), columns=METRIC_NAMES)
    
    for setup, setup_data in all_data.items():
        for metric in METRIC_NAMES:
            if metric in setup_data:
                mean_df.loc[setup, metric] = setup_data[metric]['mean']
                std_df.loc[setup, metric] = setup_data[metric]['std']
                median_df.loc[setup, metric] = setup_data[metric]['median']
                count_df.loc[setup, metric] = setup_data[metric]['sample_size']
            else:
                mean_df.loc[setup, metric] = np.nan
                std_df.loc[setup, metric] = np.nan
                median_df.loc[setup, metric] = np.nan
                count_df.loc[setup, metric] = 0
    
    # Convert to numeric
    mean_df = mean_df.astype(float)
    std_df = std_df.astype(float)
    median_df = median_df.astype(float)
    count_df = count_df.astype(int)
    
    return {
        'mean': mean_df,
        'std': std_df,
        'median': median_df,
        'count': count_df,
        'all_metrics': METRIC_NAMES
    }

def categorize_metrics(metric_names):
    """
    Categorize metrics into groups for better visualization
    """
    cpu_energy_metrics = []
    system_metrics = []
    argo_metrics = []
    
    for metric in metric_names:
        metric_lower = metric.lower()
        
        if any(keyword in metric_lower for keyword in ['cpu', 'power', 'energy', 'watts', 'joules']):
            cpu_energy_metrics.append(metric)
        elif any(keyword in metric_lower for keyword in ['apiserver', 'memory', 'network']):
            system_metrics.append(metric)
        elif any(keyword in metric_lower for keyword in ['argo', 'workflow', 'queue']):
            argo_metrics.append(metric)
        else:
            # Default to system metrics if uncategorized
            system_metrics.append(metric)
    
    return {
        'CPU & Energy': cpu_energy_metrics,
        'System Performance': system_metrics,
        'Argo Workflows': argo_metrics
    }

def plot_metric_comparison(mean_df, category_name, category_metrics, figsize=(15, 8)):
    """
    Create comparison plots for a specific metric category
    """
    # Filter metrics for this category
    category_df = mean_df[category_metrics].copy()
    
    # Create figure
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    
    # Plot 1: Grouped bar chart
    ax1 = axes[0]
    x = np.arange(len(category_df.index))
    width = 0.8 / len(category_df.columns)
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(category_df.columns)))
    
    # Create grouped bars
    for i, column in enumerate(category_df.columns):
        offset = (i - len(category_df.columns)/2 + 0.5) * width
        bars = ax1.bar(x + offset, category_df[column].values, width=width,
                      label=column.replace('_', ' ').title(), color=colors[i], alpha=0.8)
        
        # Add value labels on top of bars
        for j, bar in enumerate(bars):
            height = bar.get_height()
            if not pd.isna(height):
                ax1.text(bar.get_x() + bar.get_width()/2, height,
                        f'{height:.2f}', ha='center', va='bottom', fontsize=8)
    
    ax1.set_xlabel('Setup')
    ax1.set_ylabel('Mean Value')
    ax1.set_title(f'{category_name} - Grouped Bars', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(category_df.index, rotation=45)
    ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Normalized heatmap
    ax2 = axes[1]
    # Normalize by column (metric)
    normalized_df = category_df.div(category_df.max(), axis=1)
    im = ax2.imshow(normalized_df.values.T, cmap='RdYlBu_r', aspect='auto', vmin=0, vmax=1)
    
    ax2.set_title(f'{category_name} - Normalized Heatmap', fontweight='bold')
    ax2.set_xlabel('Setups')
    ax2.set_ylabel('Metrics')
    ax2.set_xticks(range(len(category_df.index)))
    ax2.set_yticks(range(len(category_df.columns)))
    ax2.set_xticklabels(category_df.index, rotation=45)
    ax2.set_yticklabels([col.replace('_', '\n').title()[:15] for col in category_df.columns])
    
    # Add text annotations
    for i in range(len(category_df.index)):
        for j in range(len(category_df.columns)):
            value = normalized_df.iloc[i, j]
            if not pd.isna(value):
                ax2.text(i, j, f'{value:.2f}', ha='center', va='center',
                        color='white' if value > 0.5 else 'black', fontsize=8)
    
    plt.colorbar(im, ax=ax2, label='Normalized Value')
    
    # Plot 3: Line plot for trend analysis
    ax3 = axes[2]
    
    for i, metric in enumerate(category_df.columns):
        values = category_df[metric].values
        if not all(pd.isna(values)):
            # Normalize for better comparison
            norm_values = values / np.nanmax(values)
            ax3.plot(category_df.index, norm_values, 'o-', label=metric.replace('_', ' ').title(),
                    linewidth=2, markersize=8, alpha=0.7)
    
    ax3.set_xlabel('Setup')
    ax3.set_ylabel('Normalized Value')
    ax3.set_title(f'{category_name} - Trend Lines', fontweight='bold')
    ax3.set_xticklabels(category_df.index, rotation=45)
    ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax3.grid(True, alpha=0.3)
    
    plt.suptitle(f'{category_name.upper()} METRICS COMPARISON', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.show()
    
    # Print summary table
    print(f"\n{'='*80}")
    print(f"{category_name.upper()} - SUMMARY TABLE")
    print(f"{'='*80}")
    print(category_df.round(3))
    
    # Calculate improvements if we have at least 2 setups
    if len(category_df) >= 2:
        print(f"\n{'='*80}")
        print(f"{category_name.upper()} - IMPROVEMENT ANALYSIS")
        print(f"{'='*80}")
        
        baseline = category_df.index[0]
        for setup in category_df.index[1:]:
            print(f"\n{setup} vs {baseline}:")
            for metric in category_df.columns:
                val_baseline = category_df.loc[baseline, metric]
                val_current = category_df.loc[setup, metric]
                
                if not pd.isna(val_baseline) and not pd.isna(val_current) and val_baseline != 0:
                    change_pct = ((val_current - val_baseline) / val_baseline) * 100
                    
                    # Determine if improvement or regression based on metric type
                    metric_lower = metric.lower()
                    if any(word in metric_lower for word in ['latency', 'error', 'power', 'energy', 'usage']):
                        # Lower is better
                        if change_pct < 0:
                            status = "✓ IMPROVED"
                            emoji = "📉"
                        else:
                            status = "✗ WORSENED"
                            emoji = "📈"
                    else:
                        # Higher is better
                        if change_pct > 0:
                            status = "✓ IMPROVED"
                            emoji = "📈"
                        else:
                            status = "✗ WORSENED"
                            emoji = "📉"
                    
                    if abs(change_pct) > 0.1:  # Only show changes > 0.1%
                        print(f"  {emoji} {metric.replace('_', ' ').title():<35}: {change_pct:+.2f}% ({status})")

def create_detailed_metric_analysis(all_data, metric_name, setups):
    """
    Create detailed analysis for a specific metric
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Collect data
    data_by_setup = {}
    for setup in setups:
        if setup in all_data and metric_name in all_data[setup]:
            data_by_setup[setup] = all_data[setup][metric_name]['values']
    
    if not data_by_setup:
        print(f"No data available for metric: {metric_name}")
        return
    
    # Plot 1: Box plot
    ax1 = axes[0, 0]
    box_data = [data_by_setup[setup] for setup in setups if setup in data_by_setup]
    box_labels = [setup for setup in setups if setup in data_by_setup]
    
    bp = ax1.boxplot(box_data, labels=box_labels, patch_artist=True)
    
    # Color the boxes
    colors = plt.cm.Set3(np.linspace(0, 1, len(box_data)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
    
    ax1.set_title(f'{metric_name.replace("_", " ").title()} - Distribution', fontweight='bold')
    ax1.set_ylabel('Value')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Violin plot
    ax2 = axes[0, 1]
    violin_data = []
    violin_labels = []
    
    for setup in setups:
        if setup in data_by_setup:
            violin_data.append(data_by_setup[setup])
            violin_labels.append(setup)
    
    vp = ax2.violinplot(violin_data, showmeans=True, showmedians=True)
    
    # Color the violins
    for i, pc in enumerate(vp['bodies']):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.7)
    
    ax2.set_xticks(range(1, len(violin_labels) + 1))
    ax2.set_xticklabels(violin_labels)
    ax2.set_title(f'{metric_name.replace("_", " ").title()} - Density', fontweight='bold')
    ax2.set_ylabel('Value')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Bar chart of statistics
    ax3 = axes[1, 0]
    stats_data = {
        'Mean': [np.mean(data_by_setup[setup]) for setup in setups if setup in data_by_setup],
        'Median': [np.median(data_by_setup[setup]) for setup in setups if setup in data_by_setup],
        'Std Dev': [np.std(data_by_setup[setup]) for setup in setups if setup in data_by_setup]
    }
    
    x = np.arange(len([setup for setup in setups if setup in data_by_setup]))
    width = 0.25
    multiplier = 0
    
    for stat_name, stat_values in stats_data.items():
        offset = width * multiplier
        rects = ax3.bar(x + offset, stat_values, width, label=stat_name, alpha=0.8)
        ax3.bar_label(rects, padding=3, fmt='%.2f', fontsize=8)
        multiplier += 1
    
    ax3.set_xlabel('Setup')
    ax3.set_ylabel('Value')
    ax3.set_title(f'{metric_name.replace("_", " ").title()} - Statistics', fontweight='bold')
    ax3.set_xticks(x + width, [setup for setup in setups if setup in data_by_setup])
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Statistical significance
    ax4 = axes[1, 1]
    
    # Perform t-tests between all pairs
    setup_pairs = []
    p_values = []
    
    setups_with_data = [setup for setup in setups if setup in data_by_setup]
    
    for i in range(len(setups_with_data)):
        for j in range(i + 1, len(setups_with_data)):
            setup1 = setups_with_data[i]
            setup2 = setups_with_data[j]
            
            if len(data_by_setup[setup1]) > 1 and len(data_by_setup[setup2]) > 1:
                t_stat, p_value = stats.ttest_ind(data_by_setup[setup1], data_by_setup[setup2])
                setup_pairs.append(f'{setup1} vs {setup2}')
                p_values.append(p_value)
    
    if p_values:
        bars = ax4.barh(setup_pairs, p_values, color=['green' if p < 0.05 else 'red' for p in p_values])
        ax4.axvline(x=0.05, color='r', linestyle='--', alpha=0.5, label='p=0.05 threshold')
        
        # Add p-value labels
        for bar, p_val in zip(bars, p_values):
            ax4.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                    f'p={p_val:.3e}', va='center', fontsize=8)
        
        ax4.set_xlabel('p-value')
        ax4.set_title('Statistical Significance (t-test)', fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    else:
        ax4.text(0.5, 0.5, 'Insufficient data\nfor statistical tests',
                ha='center', va='center', transform=ax4.transAxes, fontsize=12)
        ax4.set_title('Statistical Significance', fontweight='bold')
    
    plt.suptitle(f'DETAILED ANALYSIS: {metric_name.replace("_", " ").upper()}', 
                 fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.show()

def create_comprehensive_dashboard(mean_df, all_data, categories):
    """
    Create a comprehensive dashboard with key insights
    """
    fig = plt.figure(figsize=(18, 12))
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.3)
    
    setups = list(mean_df.index)
    
    # 1. Overall Performance Score
    ax1 = fig.add_subplot(gs[0, :])
    
    # Calculate normalized scores for each setup
    performance_scores = {}
    for setup in setups:
        scores = []
        for metric in mean_df.columns:
            if pd.isna(mean_df.loc[setup, metric]):
                continue
            
            # Normalize the value
            metric_values = mean_df[metric].dropna()
            if len(metric_values) > 1:
                normalized = (mean_df.loc[setup, metric] - metric_values.min()) / \
                            (metric_values.max() - metric_values.min() + 1e-10)
                
                # Invert for metrics where lower is better
                metric_lower = metric.lower()
                if any(word in metric_lower for word in ['latency', 'error', 'power', 'energy', 'usage']):
                    normalized = 1 - normalized
                
                scores.append(normalized)
        
        if scores:
            performance_scores[setup] = np.mean(scores)
    
    # Sort by performance
    sorted_scores = sorted(performance_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_setups = [s[0] for s in sorted_scores]
    sorted_values = [s[1] for s in sorted_scores]
    
    # Create gradient colors
    colors = plt.cm.RdYlGn(np.linspace(0, 1, len(sorted_setups)))
    
    bars = ax1.bar(sorted_setups, sorted_values, color=colors, edgecolor='black')
    ax1.set_title('Overall Performance Ranking (0-1 scale)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Performance Score')
    ax1.set_ylim(0, 1.1)
    
    # Add score labels
    for bar, score in zip(bars, sorted_values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, height + 0.02,
                f'{score:.3f}', ha='center', va='bottom', fontweight='bold')
    
    ax1.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='Average')
    ax1.legend()
    
    # 2. Best/Worst metrics for each setup
    ax2 = fig.add_subplot(gs[1, 0:2])
    
    best_worst_data = []
    for setup in setups:
        metric_performance = {}
        
        for metric in mean_df.columns:
            if pd.isna(mean_df.loc[setup, metric]):
                continue
            
            # Calculate z-score
            metric_values = mean_df[metric].dropna()
            if len(metric_values) > 1:
                z_score = (mean_df.loc[setup, metric] - metric_values.mean()) / metric_values.std()
                
                # Adjust sign based on whether higher is better
                metric_lower = metric.lower()
                if any(word in metric_lower for word in ['latency', 'error', 'power', 'energy', 'usage']):
                    z_score = -z_score  # Invert so higher z-score is better
                
                metric_performance[metric] = z_score
        
        if metric_performance:
            # Get top 3 best and worst
            sorted_perf = sorted(metric_performance.items(), key=lambda x: x[1])
            worst = sorted_perf[:3]
            best = sorted_perf[-3:]
            
            for metric, score in worst:
                best_worst_data.append([setup, metric, score, 'Worst'])
            for metric, score in best:
                best_worst_data.append([setup, metric, score, 'Best'])
    
    if best_worst_data:
        bw_df = pd.DataFrame(best_worst_data, columns=['Setup', 'Metric', 'Z-Score', 'Type'])
        
        # Plot
        for setup in setups:
            setup_data = bw_df[bw_df['Setup'] == setup]
            if not setup_data.empty:
                colors = ['red' if t == 'Worst' else 'green' for t in setup_data['Type']]
                ax2.scatter(setup_data['Z-Score'], setup_data['Metric'], 
                           label=setup, s=100, alpha=0.7)
        
        ax2.axvline(x=0, color='k', linestyle='--', alpha=0.3)
        ax2.set_xlabel('Z-Score (Higher is Better)')
        ax2.set_title('Best & Worst Performing Metrics', fontweight='bold')
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax2.grid(True, alpha=0.3)
    
    # 3. Data completeness
    ax3 = fig.add_subplot(gs[1, 2])
    
    completeness = {}
    for setup in setups:
        available = mean_df.loc[setup].notna().sum()
        total = len(mean_df.columns)
        completeness[setup] = available / total * 100
    
    colors = plt.cm.YlOrRd(np.array(list(completeness.values())) / 100)
    bars = ax3.bar(completeness.keys(), completeness.values(), color=colors, edgecolor='black')
    
    ax3.set_title('Data Completeness (%)', fontweight='bold')
    ax3.set_ylabel('Percentage Available')
    ax3.set_ylim(0, 110)
    
    # Add percentage labels
    for bar, perc in zip(bars, completeness.values()):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2, height + 2,
                f'{perc:.1f}%', ha='center', va='bottom', fontsize=10)
    
    # 4. Category performance comparison
    ax4 = fig.add_subplot(gs[2, :])
    
    category_performance = {}
    for category_name, metrics in categories.items():
        category_scores = {}
        for setup in setups:
            scores = []
            for metric in metrics:
                if metric in mean_df.columns and not pd.isna(mean_df.loc[setup, metric]):
                    # Normalize and score
                    metric_values = mean_df[metric].dropna()
                    normalized = (mean_df.loc[setup, metric] - metric_values.min()) / \
                                (metric_values.max() - metric_values.min() + 1e-10)
                    
                    metric_lower = metric.lower()
                    if any(word in metric_lower for word in ['latency', 'error', 'power', 'energy', 'usage']):
                        normalized = 1 - normalized
                    
                    scores.append(normalized)
            
            if scores:
                category_scores[setup] = np.mean(scores)
        
        category_performance[category_name] = category_scores
    
    # Create grouped bar chart
    x = np.arange(len(setups))
    width = 0.25
    multiplier = 0
    
    for category, scores in category_performance.items():
        offsets = x + width * multiplier
        values = [scores.get(setup, 0) for setup in setups]
        ax4.bar(offsets, values, width, label=category, alpha=0.8)
        multiplier += 1
    
    ax4.set_xlabel('Setup')
    ax4.set_ylabel('Performance Score')
    ax4.set_title('Performance by Metric Category', fontweight='bold')
    ax4.set_xticks(x + width, setups)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.suptitle('EXPERIMENT SETUP COMPARISON - DASHBOARD', 
                 fontsize=18, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.show()

# Main execution
print("=" * 100)
print("EXPERIMENTAL SETUP COMPARISON ANALYSIS")
print("=" * 100)
print(f"Analyzing {len(SETUP_NAMES)} setups: {', '.join(SETUP_NAMES)}")
print(f"Total metrics: {len(METRIC_NAMES)}")

# Load all data
print("\n📂 Loading data from all setups...")
all_data = load_all_metrics(SETUP_NAMES, SETUPS_DIR)

# Create summary dataframes
print("\n📊 Processing data and creating summaries...")
summary = create_summary_dataframe(all_data)

# Categorize metrics
categories = categorize_metrics(METRIC_NAMES)

print(f"\n📋 Metrics categorized:")
for category_name, metrics in categories.items():
    print(f"  • {category_name}: {len(metrics)} metrics")

# Display data completeness
print(f"\n📈 Data Availability:")
completeness = pd.DataFrame(index=summary['mean'].index, columns=['Available', 'Total', 'Percentage'])
for setup in summary['mean'].index:
    available = summary['mean'].loc[setup].notna().sum()
    total = len(summary['mean'].columns)
    percentage = (available / total) * 100
    completeness.loc[setup] = [available, total, f"{percentage:.1f}%"]

print(completeness)

# Generate category-wise comparisons
print("\n" + "=" * 100)
print("CATEGORY-WISE COMPARISONS")
print("=" * 100)

for category_name, metrics in categories.items():
    if metrics:
        print(f"\n📊 Analyzing {category_name} ({len(metrics)} metrics)...")
        plot_metric_comparison(summary['mean'], category_name, metrics)

# Create comprehensive dashboard
print("\n" + "=" * 100)
print("COMPREHENSIVE DASHBOARD")
print("=" * 100)
create_comprehensive_dashboard(summary['mean'], all_data, categories)

# Optional: Detailed analysis for specific metrics
print("\n" + "=" * 100)
print("DETAILED METRIC ANALYSIS")
print("=" * 100)

# Select top 3 metrics with highest variation for detailed analysis
variation = summary['mean'].std().sort_values(ascending=False)
top_metrics = variation.head(3).index.tolist()

for metric in top_metrics:
    print(f"\n🔍 Detailed analysis for: {metric}")
    create_detailed_metric_analysis(all_data, metric, SETUP_NAMES)

# Export results
print("\n" + "=" * 100)
print("EXPORTING RESULTS")
print("=" * 100)

# Create output directory
output_dir = "./analysis_results"
os.makedirs(output_dir, exist_ok=True)

# Export summary statistics
summary['mean'].to_csv(os.path.join(output_dir, "mean_values.csv"))
summary['median'].to_csv(os.path.join(output_dir, "median_values.csv"))
summary['std'].to_csv(os.path.join(output_dir, "std_values.csv"))
summary['count'].to_csv(os.path.join(output_dir, "sample_counts.csv"))

print(f"✓ Summary statistics exported to: {output_dir}/")

# Generate comprehensive report
with open(os.path.join(output_dir, "analysis_report.md"), "w") as f:
    f.write("# Experimental Setup Comparison Report\n\n")
    f.write(f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    f.write("## Setup Information\n")
    f.write(f"- Number of setups: {len(SETUP_NAMES)}\n")
    f.write(f"- Setups analyzed: {', '.join(SETUP_NAMES)}\n")
    f.write(f"- Total metrics: {len(METRIC_NAMES)}\n\n")
    
    f.write("## Data Completeness\n")
    f.write(completeness.to_markdown() + "\n\n")
    
    f.write("## Performance Ranking\n")
    
    # Calculate performance ranking
    performance_scores = {}
    for setup in summary['mean'].index:
        scores = []
        for metric in summary['mean'].columns:
            if pd.isna(summary['mean'].loc[setup, metric]):
                continue
            
            metric_values = summary['mean'][metric].dropna()
            normalized = (summary['mean'].loc[setup, metric] - metric_values.min()) / \
                        (metric_values.max() - metric_values.min() + 1e-10)
            
            metric_lower = metric.lower()
            if any(word in metric_lower for word in ['latency', 'error', 'power', 'energy', 'usage']):
                normalized = 1 - normalized
            
            scores.append(normalized)
        
        if scores:
            performance_scores[setup] = np.mean(scores)
    
    ranking_df = pd.DataFrame({
        'Setup': list(performance_scores.keys()),
        'Score': list(performance_scores.values())
    }).sort_values('Score', ascending=False)
    
    f.write(ranking_df.to_markdown(index=False) + "\n\n")
    
    f.write("## Key Recommendations\n\n")
    
    if len(performance_scores) > 0:
        best_setup = max(performance_scores, key=performance_scores.get)
        worst_setup = min(performance_scores, key=performance_scores.get)
        
        f.write(f"1. **Best Performing Setup:** {best_setup}\n")
        f.write(f"2. **Setup Needing Improvement:** {worst_setup}\n")
        
        # Find specific areas for improvement
        for setup in [worst_setup]:
            f.write(f"\n3. **Improvement areas for {setup}:**\n")
            for category_name, metrics in categories.items():
                cat_mean = summary['mean'][metrics].mean(axis=1)
                if setup in cat_mean.index:
                    setup_score = cat_mean[setup]
                    best_in_cat = cat_mean.max()
                    if setup_score < best_in_cat * 0.9:  # More than 10% worse than best
                        improvement_needed = ((best_in_cat - setup_score) / best_in_cat) * 100
                        f.write(f"   - {category_name}: {improvement_needed:.1f}% improvement needed\n")

print(f"\n✅ Analysis complete! Results saved to {output_dir}/")
print("\n📊 Generated visualizations:")
print("  • Category-wise comparison plots")
print("  • Comprehensive dashboard")
print("  • Detailed analysis for key metrics")
print("  • Exported CSV files with all statistics")
print("  • Markdown report with insights")