
import matplotlib.pyplot as plt
import numpy as np
import dbscan_merge, Data.Database_access.loadFromDb as loadFromDb, grid_merge,optics_merge

def plot_with_density(points, title="Point Distribution", 
                      bins=30, bandwidth=None, 
                      show_scatter=True, show_contour=True,
                      figsize=(14, 6)):
    """
    Create a plot with points and density map side by side.
    
    Args:
        points: List of (x, y) points
        title: Main title for the plot
        bins: Number of bins for histogram (int or [x_bins, y_bins])
        bandwidth: Bandwidth for KDE (None for automatic)
        show_scatter: Whether to show scatter plot alongside density
        show_contour: Whether to show contour lines on density plot
        figsize: Figure size (width, height)
    """
    # Convert to numpy array for easier manipulation
    points = np.array(points)
    x = points[:, 0]
    y = points[:, 1]
    
    if show_scatter:
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # Plot 1: Scatter plot
        ax1.scatter(x, y, c='blue', alpha=0.6, s=1, edgecolors='white', linewidth=0.5)
        ax1.set_xlabel('X')
        ax1.set_ylabel('Y')
        ax1.set_title(f'Scatter Plot (n={len(points)})')
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect('equal', adjustable='box')
        
        # Plot 2: Density map
        ax2 = create_density_plot(ax2, x, y, bins, bandwidth, show_contour)
        
    else:
        # Just create density plot
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        ax = create_density_plot(ax, x, y, bins, bandwidth, show_contour)
    
    plt.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()
    
    return fig

def create_density_plot(ax, x, y, bins=30, bandwidth=None, show_contour=True):
    """Helper function to create density plot on given axis."""
    
    # Create density map using 2D histogram
    if isinstance(bins, int):
        hist_bins = bins
    else:
        hist_bins = bins
    
    # Calculate 2D histogram
    hist, xedges, yedges = np.histogram2d(x, y, bins=hist_bins, density=True)
    
    # Create meshgrid for plotting
    X, Y = np.meshgrid(xedges[:-1] + (xedges[1] - xedges[0])/2,
                       yedges[:-1] + (yedges[1] - yedges[0])/2)
    
    # Plot heatmap
    im = ax.pcolormesh(X, Y, hist.T, cmap='hot', shading='auto')
    plt.colorbar(im, ax=ax, label='Density')
    
    if show_contour:
        # Add contour lines
        contour = ax.contour(X, Y, hist.T, colors='white', alpha=0.5, linewidths=1)
        ax.clabel(contour, inline=True, fontsize=8, fmt='%.2f')
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_title('Density Heatmap')
    ax.set_aspect('equal', adjustable='box')
    
    return ax

def main():
    walk_points,obstacles = loadFromDb.fetch_points()


    print("="*80)
    print("WALK POINTS: ",walk_points)
    print("="*80)
    print("OBSTACLES: ",obstacles)
    
    print("="*80)
    filtered_points = loadFromDb.remove_near_zero_outliers(walk_points)
    print("raw points: ", len(filtered_points))
    squares = grid_merge.intoGrid(filtered_points,10)
    merged_points = grid_merge.findCentroid(squares)
    print("grid merged points: ", len(merged_points))

    # optics_merged_points = merge_points_optics(filtered_points)
    # dbscan_merged_points = dbscan_merge.merge_points_dbscan(filtered_points, eps=4.0)
    # print("DBSCAN merged points: ", len(dbscan_merged_points))

    simple_dbscan_merged_points3 = dbscan_merge.merge_points_simpleDbscan(filtered_points, eps=3, min_samples=1)
    print("simple DBSCAN merged points eps 3: ", len(simple_dbscan_merged_points3))
    simple_dbscan_merged_points5 = dbscan_merge.merge_points_simpleDbscan(filtered_points, eps=5, min_samples=1)
    print("simple DBSCAN merged points eps 5: ", len(simple_dbscan_merged_points5))
    simple_dbscan_merged_points8 = dbscan_merge.merge_points_simpleDbscan(filtered_points, eps=8, min_samples=1)
    print("simple DBSCAN merged points eps 8: ", len(simple_dbscan_merged_points8))
    
    

    # print("optics merged points", len(optics_merged_points))



    plot_with_density(filtered_points)
    plot_with_density(merged_points)
    # plot_with_density(optics_merged_points)
    # plot_with_density(dbscan_merged_points)
    plot_with_density(simple_dbscan_merged_points3)
    plot_with_density(simple_dbscan_merged_points5)
    plot_with_density(simple_dbscan_merged_points8)


if __name__ == "__main__":
    main()