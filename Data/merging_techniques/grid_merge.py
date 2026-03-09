def intoGrid(points,SQUARE_SIZE = 5):
    squares = {}
    for x, y in points:
        # Calculate which square this point belongs to
        # Integer division to find the grid coordinates
        grid_x = x // SQUARE_SIZE
        grid_y = y // SQUARE_SIZE
        
        # Create a unique key for this square
        square_key = (grid_x, grid_y)
        
        # If this square doesn't exist yet, create it
        if square_key not in squares:
            squares[square_key] = []
        
        # Add the point to its square
        squares[square_key].append((x, y))
    return squares

def printSquare(squares,SQUARE_SIZE = 5):
    print("Points sorted into 5×5 squares:")
    print("-" * 40)
    stoppoint = 10
    i=0
    for square, pts in sorted(squares.items()):
        i+=1
        if i >= stoppoint: break
        grid_x, grid_y = square
        x_range = f"[{grid_x*SQUARE_SIZE}, {(grid_x+1)*SQUARE_SIZE})"
        y_range = f"[{grid_y*SQUARE_SIZE}, {(grid_y+1)*SQUARE_SIZE})"
        print(f"Square {square} (x:{x_range}, y:{y_range}): {pts}")

def findCentroid(squares):
    centroids = []
    for square_points in squares.values():
        if square_points:  # Skip empty squares
            # Calculate centroid (average of x and y coordinates)
            n = len(square_points)
            sum_x = sum(p[0] for p in square_points)
            sum_y = sum(p[1] for p in square_points)
            
            centroid_x = sum_x / n
            centroid_y = sum_y / n
            
            centroids.append((centroid_x, centroid_y))
    
    return centroids