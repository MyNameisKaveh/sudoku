import random

import numpy as np

# Base pattern for Sudoku generation
BASE = 3
SIDE = BASE * BASE

# Helper to generate a base pattern (Fisher-Yates shuffle for rows within bands and columns within stacks)
def pattern(r, c): return (BASE * (r % BASE) + r // BASE + c) % SIDE

def shuffle(s): return random.sample(s, len(s))

def generate_full_board():
    """Generates a fully solved Sudoku board."""
    r_base = range(BASE)
    rows = [g * BASE + r for g in shuffle(r_base) for r in shuffle(r_base)]
    cols = [g * BASE + c for g in shuffle(r_base) for c in shuffle(r_base)]
    nums = shuffle(range(1, SIDE + 1))

    # Produce board using randomized baseline pattern
    board = [[nums[pattern(r, c)] for c in cols] for r in rows]
    return board

def remove_numbers(board, difficulty="easy", base_empties_override=None):
    """
    Removes numbers from a full board to create a puzzle.
    The number of cells to remove depends on the difficulty or override.
    Returns the puzzle (board with 0s for empty cells).
    """
    squares = SIDE * SIDE

    if base_empties_override is not None:
        empties = base_empties_override
    else:
        if difficulty == "easy":
            empties = squares * 3 // 7
        elif difficulty == "medium":
            empties = squares * 4 // 7
        elif difficulty == "hard":
            empties = squares * 5 // 7
        else: # Default to easy
            empties = squares * 3 // 7

    puzzle = [row[:] for row in board] # Create a mutable copy
    # Ensure unique solution by trying to remove cells and checking solvability
    # This is a simplified approach; true unique solution checking is complex.
    # For now, we just remove randomly. A more robust solution would involve
    # trying to solve the puzzle with each removal to ensure it still has one solution.
    # For now, we will use a simpler removal strategy: just remove 'empties' cells randomly.
    # This might not always produce puzzles with a unique solution, but our solver will find *a* solution.
    # The check_win function will compare against the original full board.

    puzzle = [row[:] for row in board] # Create a mutable copy

    # Create a list of all cell coordinates
    all_cells = []
    for r in range(SIDE):
        for c in range(SIDE):
            all_cells.append((r, c))

    random.shuffle(all_cells)

    # Remove numbers from the shuffled list of cells until 'empties' cells are cleared
    for i in range(empties):
        if i < len(all_cells):
            r, c = all_cells[i]
            puzzle[r][c] = 0
        else:
            break # Should not happen if empties <= SIDE*SIDE

    return puzzle

def generate_puzzle(difficulty: str = "easy"):
    """
    Generates a Sudoku puzzle and its solution.
    Difficulty levels: "easy", "medium", "hard".
    A cell with 0 means it's empty.
    """
    solution_board = generate_full_board()
    puzzle_board = remove_numbers(solution_board, difficulty)

    # Convert to list of lists if they are numpy arrays, or ensure they are lists
    solution_list = [list(row) for row in solution_board]
    puzzle_list = [list(row) for row in puzzle_board]


    # Ensure the generated puzzle, when solved, matches the original solution board.
    # This is a workaround for puzzles that might have multiple solutions if not carefully crafted.
    # We want our solver to arrive at the *specific* solution we started with.

    current_difficulty_settings = {
        "easy": {"empties_ratio": 3/7, "max_attempts": 100},
        "medium": {"empties_ratio": 4/7, "max_attempts": 150},
        "hard": {"empties_ratio": 5/7, "max_attempts": 300, "fallback_empties_ratio": 4.5/7} # Adjusted hard
    }

    settings = current_difficulty_settings.get(difficulty, current_difficulty_settings["easy"])
    max_attempts = settings["max_attempts"]
    empties_ratio = settings["empties_ratio"]
    fallback_empties_ratio = settings.get("fallback_empties_ratio")

    original_empties = int(SIDE * SIDE * empties_ratio)

    for attempt in range(max_attempts):
        # Adjust number of empties for 'hard' difficulty on later attempts if fallback is defined
        current_empties = original_empties
        if difficulty == "hard" and fallback_empties_ratio and attempt > max_attempts // 2:
            current_empties = int(SIDE * SIDE * fallback_empties_ratio)
            if attempt == max_attempts // 2 + 1 : # Log only once when fallback kicks in
                 pass # print(f"Info: Difficulty '{difficulty}', attempt {attempt+1}. Trying fallback empties: {current_empties}")


        # Regenerate puzzle and solution for each attempt to ensure freshness if previous failed
        if attempt > 0: # No need to regenerate on the first attempt as it's done outside the loop
            solution_board = generate_full_board()
            # Use current_empties for remove_numbers which might be adjusted
            puzzle_board = remove_numbers(solution_board, difficulty, base_empties_override=current_empties)
            solution_list = [list(row) for row in solution_board]
            puzzle_list = [list(row) for row in puzzle_board]


        temp_puzzle_to_solve = [row[:] for row in puzzle_list]
        solve_sudoku(temp_puzzle_to_solve) # solve_sudoku modifies in place

        match = True
        for r in range(SIDE):
            for c in range(SIDE):
                if temp_puzzle_to_solve[r][c] != solution_list[r][c]:
                    match = False
                    break
            if not match:
                break

        if match:
            # print(f"Generated a puzzle (diff: {difficulty}, empties: {current_empties}, attempt: {attempt+1}) whose solver solution matches original solution.")
            return puzzle_list, solution_list
        # else:
            # print(f"Warning: Puzzle generation attempt {attempt+1} for difficulty '{difficulty}' (empties: {current_empties}) did not yield a puzzle whose direct solution matches the base solution. Retrying.")


    print(f"Error: Could not generate a puzzle for difficulty '{difficulty}' where the solver's output matches the original solution after {max_attempts} attempts with current settings.")
    # Fallback: return the last generated one, even if it doesn't match. This might cause test failures.
    return puzzle_list, solution_list


def is_valid_move(grid: list[list[int]], row: int, col: int, num: int) -> bool:
    """
    Checks if placing a number in a given cell is a valid Sudoku move
    according to Sudoku rules (row, column, and 3x3 subgrid).
    """
    # Check row
    for x in range(SIDE):
        if grid[row][x] == num and x != col: # Added x != col to allow overwriting current cell if needed by solver
            return False
    # Check column
    for y in range(SIDE):
        if grid[y][col] == num and y != row: # Added y != row
            return False

    # Check 3x3 subgrid
    start_row, start_col = BASE * (row // BASE), BASE * (col // BASE)
    for i in range(BASE):
        for j in range(BASE):
            if grid[i + start_row][j + start_col] == num and (i + start_row != row or j + start_col != col):
                return False
    return True

def solve_sudoku(grid: list[list[int]]) -> bool:
    """
    Solves a Sudoku puzzle using backtracking.
    Modifies the grid in place. Returns True if a solution is found.
    """
    find = find_empty(grid)
    if not find:
        return True  # Puzzle is solved
    else:
        row, col = find

    for num in range(1, 10):
        if is_valid_move(grid, row, col, num):
            grid[row][col] = num
            if solve_sudoku(grid):
                return True
            grid[row][col] = 0  # Backtrack
    return False

def find_empty(grid: list[list[int]]):
    """Finds an empty cell (represented by 0) in the grid."""
    for i in range(SIDE):
        for j in range(SIDE):
            if grid[i][j] == 0:
                return (i, j)  # row, col
    return None

def check_win(current_grid: list[list[int]], solution_grid: list[list[int]]) -> bool:
    """
    Checks if the current grid matches the solution grid.
    Also ensures the grid is fully populated and valid according to Sudoku rules.
    """
    for i in range(SIDE):
        for j in range(SIDE):
            if current_grid[i][j] == 0 or current_grid[i][j] != solution_grid[i][j]:
                return False
            # Double check validity (although if it matches solution, it should be valid)
            # temp = current_grid[i][j]
            # current_grid[i][j] = 0 # Temporarily empty to check if 'temp' can be placed
            # if not is_valid_move(current_grid, i, j, temp):
            #     current_grid[i][j] = temp # Restore
            #     return False # Should not happen if solution_grid is correct
            # current_grid[i][j] = temp # Restore

    # Final check: ensure the completed board is valid by itself
    for r in range(SIDE):
        for c in range(SIDE):
            num = current_grid[r][c]
            # Temporarily remove the number to check its validity in its own context
            current_grid[r][c] = 0
            if not is_valid_move(current_grid, r, c, num):
                current_grid[r][c] = num # backtrack
                return False
            current_grid[r][c] = num # backtrack

    return True

def print_board_to_console(board: list[list[int]]):
    """Prints the Sudoku board to the console in a readable format."""
    """Prints the Sudoku board to the console in a readable format."""
    horiz_line = "  " + "+-------" * BASE + "+"
    for r in range(SIDE):
        if r % BASE == 0:
            print(horiz_line)
        row_str = ""
        for c in range(SIDE):
            if c % BASE == 0:
                row_str += "|| " if c == 0 else "| "
            num = board[r][c]
            row_str += str(num) if num != 0 else "."
            row_str += " "
        print(row_str + "||")
    print(horiz_line)


if __name__ == '__main__':
    print("Testing Sudoku Logic...")

    # Test puzzle generation for different difficulties
    for diff in ["easy", "medium", "hard"]:
        print(f"\n--- Testing Difficulty: {diff} ---")
        puzzle, solution = generate_puzzle(difficulty=diff)

        print(f"Generated {diff} Puzzle:")
        print_board_to_console(puzzle)
        # print("\nSolution:")
        # print_board_to_console(solution)

        # Validate that the generated puzzle has empty cells and solution is full
        empty_cells_puzzle = sum(row.count(0) for row in puzzle)
        empty_cells_solution = sum(row.count(0) for row in solution)
        print(f"Empty cells in puzzle: {empty_cells_puzzle}")
        assert empty_cells_puzzle > 0, f"{diff} puzzle should have empty cells."
        assert empty_cells_solution == 0, f"Solution for {diff} puzzle should have no empty cells."

        # Test check_win
        print(f"Is the initial {diff} puzzle a win state? {check_win(puzzle, solution)}") # Expected: False
        assert not check_win(puzzle, solution), f"Initial {diff} puzzle should not be a win state."

        # Create a copy of the solution to test check_win
        solution_copy_for_win_check = [row[:] for row in solution]
        print(f"Is the solution for {diff} a win state? {check_win(solution_copy_for_win_check, solution)}") # Expected: True
        assert check_win(solution_copy_for_win_check, solution), f"Solution for {diff} should be a win state."

        # Test solver
        puzzle_to_solve = [row[:] for row in puzzle] # Use a fresh copy
        print(f"Attempting to solve the {diff} puzzle...")
        if solve_sudoku(puzzle_to_solve):
            print(f"Solved {diff} Puzzle (using solver):")
            print_board_to_console(puzzle_to_solve)
            if check_win(puzzle_to_solve, solution): # check_win needs original solution
                print(f"Solver for {diff} matches the pre-defined solution.")
                assert check_win(puzzle_to_solve, solution), f"Solved {diff} puzzle should match its solution."
            else:
                print(f"Solver for {diff} does NOT match the pre-defined solution. This is an error.")
                # print("Solver output:")
                # print_board_to_console(puzzle_to_solve)
                # print("Expected solution:")
                # print_board_to_console(solution)
                assert False, f"Solver for {diff} failed to match solution."
        else:
            print(f"Could not solve the {diff} puzzle. This indicates an issue with generation or solver.")
            assert False, f"Failed to solve {diff} puzzle."

    print("\n--- Testing is_valid_move ---")
    sample_grid = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ]
    print("Sample grid for is_valid_move (no board print here):")
    # print_board_to_console(sample_grid) # Removed to avoid clutter during automated tests
    # Valid move
    print(f"Is placing 4 at (0,2) valid? {is_valid_move(sample_grid, 0, 2, 4)}") # True
    assert is_valid_move(sample_grid, 0, 2, 4)
    # Invalid (duplicate in row)
    print(f"Is placing 5 at (0,2) valid? {is_valid_move(sample_grid, 0, 2, 5)}") # False
    assert not is_valid_move(sample_grid, 0, 2, 5)
    # Invalid (duplicate in col)
    print(f"Is placing 9 at (0,2) valid? {is_valid_move(sample_grid, 0, 2, 9)}") # False
    assert not is_valid_move(sample_grid, 0, 2, 9)
    # Invalid (duplicate in 3x3 box - e.g. 6 from sample_grid[1][0] in box of (0,2))
    print(f"Is placing 6 at (0,1) valid (testing box)? {is_valid_move(sample_grid, 0, 1, 6)}") # False, 6 is at [1][0] in same box
    assert not is_valid_move(sample_grid, 0, 1, 6)
    # Valid (number not in row, col, or box)
    print(f"Is placing 1 at (0,2) valid? {is_valid_move(sample_grid, 0, 2, 1)}") # True
    assert is_valid_move(sample_grid, 0, 2, 1)


    print("\nAll Sudoku logic tests passed (if no assertions failed).")
