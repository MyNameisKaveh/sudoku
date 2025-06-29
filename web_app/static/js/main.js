// web_app/static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    const SIDE = 9;
    let currentBoard = []; // The board user interacts with
    let initialPuzzle = []; // The original puzzle, to identify pre-filled cells
    // let solutionBoard = []; // Not strictly needed to store globally on client if backend handles it
    let selectedCell = null; // { row, col, element }
    let undoStack = []; // For undo functionality
    let timerInterval = null;
    let timerSeconds = 0;

    // DOM Elements
    const boardContainer = document.getElementById('sudoku-board-container');
    const numbersPanel = document.getElementById('numbers-panel');
    const newGameBtn = document.getElementById('new-game-btn');
    const difficultySelect = document.getElementById('difficulty');
    const checkBtn = document.getElementById('check-btn');
    const solveBtn = document.getElementById('solve-btn');
    const hintBtn = document.getElementById('hint-btn');
    const undoBtn = document.getElementById('undo-btn');
    const messageArea = document.getElementById('message-area');
    const timerDisplay = document.getElementById('timer');

    // --- Helper Functions ---
    async function fetchAPI(url, method = 'GET', body = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        };
        if (body) {
            options.body = JSON.stringify(body);
        }
        try {
            const response = await fetch(url, options);
            const responseData = await response.json();
            if (!response.ok) {
                throw new Error(responseData.error || `HTTP error! status: ${response.status}`);
            }
            return responseData;
        } catch (error) {
            console.error('API Error:', error);
            showMessage(`خطا در ارتباط با سرور: ${error.message}`, 'error');
            return null;
        }
    }

    function showMessage(message, type = 'info') {
        messageArea.textContent = message;
        messageArea.className = 'message-area visible';
        messageArea.classList.add(`message-${type}`);
    }

    function clearMessage() {
        messageArea.textContent = '';
        messageArea.className = 'message-area';
    }

    function toggleActionButtons(disabled) {
        checkBtn.disabled = disabled;
        solveBtn.disabled = disabled;
        hintBtn.disabled = disabled;
        undoBtn.disabled = disabled || undoStack.length === 0;
    }

    // --- Timer Functions ---
    function startTimer() {
        stopTimer();
        timerSeconds = 0;
        updateTimerDisplay();
        timerInterval = setInterval(() => {
            timerSeconds++;
            updateTimerDisplay();
        }, 1000);
    }

    function stopTimer() {
        clearInterval(timerInterval);
        timerInterval = null;
    }

    function updateTimerDisplay() {
        const minutes = Math.floor(timerSeconds / 60);
        const seconds = timerSeconds % 60;
        timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }

    // --- Undo Functionality ---
    function pushToUndoStack(row, col, oldValue, newValue) {
        undoStack.push({ row, col, oldValue, newValue });
        undoBtn.disabled = false;
    }

    function handleUndo() {
        if (undoStack.length === 0) return;
        const lastAction = undoStack.pop();

        currentBoard[lastAction.row][lastAction.col] = lastAction.oldValue;
        updateCellOnBoard(lastAction.row, lastAction.col, lastAction.oldValue);

        if (selectedCell && selectedCell.row === lastAction.row && selectedCell.col === lastAction.col) {
            selectedCell.element.querySelector('input').value = lastAction.oldValue !== 0 ? lastAction.oldValue : '';
        }
        // showMessage(`حرکت قبلی بازگردانده شد.`, 'info');
        if (undoStack.length === 0) {
            undoBtn.disabled = true;
        }
    }

    // --- Board Rendering and Interaction ---
    function renderBoard(boardData, initialPuzzleData) {
        boardContainer.innerHTML = '';
        currentBoard = JSON.parse(JSON.stringify(boardData));
        initialPuzzle = JSON.parse(JSON.stringify(initialPuzzleData));

        for (let r = 0; r < SIDE; r++) {
            for (let c = 0; c < SIDE; c++) {
                const cell = document.createElement('div');
                cell.classList.add('sudoku-cell');
                cell.dataset.row = r;
                cell.dataset.col = c;

                const input = document.createElement('input');
                input.type = 'text';
                input.maxLength = 1;

                const isPreFilled = initialPuzzle[r][c] !== 0;
                if (isPreFilled) {
                    input.value = initialPuzzle[r][c];
                    input.readOnly = true;
                    cell.classList.add('pre-filled');
                } else {
                    input.value = boardData[r][c] !== 0 ? boardData[r][c] : '';
                }

                input.addEventListener('focus', (e) => handleCellFocus(e, cell, r, c));
                input.addEventListener('input', (e) => handleCellInput(e, r, c));
                input.addEventListener('keydown', (e) => handleCellKeyDown(e, r, c));
                // Click is handled by focus generally, but explicit click can also select
                cell.addEventListener('click', (e) => handleCellFocus(e, cell, r, c));


                cell.appendChild(input);
                boardContainer.appendChild(cell);
            }
        }
    }

    function updateCellOnBoard(row, col, value, isHint = false) {
        const cellElement = boardContainer.querySelector(`.sudoku-cell[data-row='${row}'][data-col='${col}']`);
        if (cellElement) {
            const inputElement = cellElement.querySelector('input');
            inputElement.value = value !== 0 ? value : '';

            document.querySelectorAll('.hint-cell').forEach(hc => hc.classList.remove('hint-cell'));
            if (isHint) {
                cellElement.classList.add('hint-cell');
                // Auto-remove highlight after animation completes (CSS animation is ~1s)
                setTimeout(() => cellElement.classList.remove('hint-cell'), 1500);
            }
            // Clear any error styling on this cell if a new value is set
            cellElement.classList.remove('error');
        }
    }

    function handleCellFocus(event, cellElement, row, col) {
        event.stopPropagation();
        if (selectedCell && selectedCell.element) {
            selectedCell.element.classList.remove('selected');
        }

        const isPreFilled = initialPuzzle[row][col] !== 0;
        if (isPreFilled) {
            selectedCell = null;
            cellElement.querySelector('input').blur();
            return;
        }

        selectedCell = { row, col, element: cellElement };
        cellElement.classList.add('selected');
        // input already focused by click or tab
    }

    function handleCellInput(event, row, col) {
        const value = event.target.value;
        let num = parseInt(value);

        if (value === '') {
            num = 0;
        } else if (isNaN(num) || num < 1 || num > 9) {
            event.target.value = currentBoard[row][col] !== 0 ? currentBoard[row][col] : '';
            showMessage('لطفاً یک عدد بین ۱ تا ۹ وارد کنید.', 'error');
            return;
        }

        const oldValue = currentBoard[row][col];
        if (oldValue !== num) {
            fillCellWithValue(row, col, num, oldValue);
        }
    }

    function handleCellKeyDown(event, row, col) {
        const inputElement = event.target;
        if (event.key === "Backspace" || event.key === "Delete") {
            event.preventDefault();
            if (currentBoard[row][col] !== 0 && initialPuzzle[row][col] === 0) { // Can only clear non-pre-filled
                 fillCellWithValue(row, col, 0, currentBoard[row][col]);
            }
        } else if (event.key >= '1' && event.key <= '9') {
            // Let input event handle this, but ensure focus remains for direct typing
            inputElement.value = ''; // Clear previous to allow new single digit input
        } else if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Tab", "Enter"].includes(event.key)) {
            // Prevent other characters if not navigation or number
            if (event.key.length === 1 && !event.ctrlKey && !event.altKey && !event.metaKey) {
                 event.preventDefault();
            }
        }
        // Add arrow key navigation later if desired
    }


    function renderNumbersPanel() {
        numbersPanel.innerHTML = '';
        for (let i = 1; i <= 9; i++) {
            const btn = document.createElement('button');
            btn.textContent = i;
            btn.addEventListener('click', () => handleNumberPanelClick(i));
            numbersPanel.appendChild(btn);
        }
        const clearBtn = document.createElement('button');
        clearBtn.textContent = 'پاک';
        clearBtn.title = "پاک کردن خانه انتخاب شده";
        clearBtn.addEventListener('click', () => handleNumberPanelClick(0));
        numbersPanel.appendChild(clearBtn);
    }

    function handleNumberPanelClick(num) {
        if (!selectedCell || (initialPuzzle[selectedCell.row][selectedCell.col] !== 0) ) {
            showMessage('لطفاً ابتدا یک خانه خالی را از جدول انتخاب کنید.', 'info');
            return;
        }
        const { row, col } = selectedCell;
        const oldValue = currentBoard[row][col];

        if (oldValue !== num) {
             fillCellWithValue(row, col, num, oldValue);
        }
        // Keep focus on the cell after number panel click for convenience
        selectedCell.element.querySelector('input').focus();
    }

    async function fillCellWithValue(row, col, num, oldValue) {
        currentBoard[row][col] = num; // Optimistic UI update
        updateCellOnBoard(row, col, num);
         if (selectedCell && selectedCell.row === row && selectedCell.col === col) {
             selectedCell.element.querySelector('input').value = num !== 0 ? num : '';
        }

        pushToUndoStack(row, col, oldValue, num);

        const response = await fetchAPI('/api/fill_cell', 'POST', { row, col, num });
        if (response) {
            if (response.error) {
                currentBoard[row][col] = oldValue; // Revert
                updateCellOnBoard(row, col, oldValue);
                 if (selectedCell && selectedCell.row === row && selectedCell.col === col) {
                    selectedCell.element.querySelector('input').value = oldValue !== 0 ? oldValue : '';
                }
                if(undoStack.length > 0 && undoStack[undoStack.length-1].row === row && undoStack[undoStack.length-1].col === col && undoStack[undoStack.length-1].newValue === num) {
                    undoStack.pop();
                    if(undoStack.length === 0) undoBtn.disabled = true;
                }
                showMessage(response.error, 'error');
            } else {
                currentBoard = response.current_board; // Ensure client board is in sync with server's perspective
                clearMessage();
            }
        } else { // Network or other major error
            currentBoard[row][col] = oldValue; // Revert
            updateCellOnBoard(row, col, oldValue);
            if (selectedCell && selectedCell.row === row && selectedCell.col === col) {
                 selectedCell.element.querySelector('input').value = oldValue !== 0 ? oldValue : '';
            }
            if(undoStack.length > 0 && undoStack[undoStack.length-1].row === row && undoStack[undoStack.length-1].col === col && undoStack[undoStack.length-1].newValue === num) {
                undoStack.pop();
                 if(undoStack.length === 0) undoBtn.disabled = true;
            }
        }
    }

    // --- Game Actions ---
    async function handleNewGame() {
        stopTimer();
        const difficulty = difficultySelect.value;
        showMessage('در حال ایجاد بازی جدید...', 'info');
        toggleActionButtons(true); // Disable buttons during load
        newGameBtn.disabled = true; // Disable new game btn itself too
        undoStack = [];
        undoBtn.disabled = true;
        selectedCell = null;

        const data = await fetchAPI('/api/new_game', 'POST', { difficulty });
        newGameBtn.disabled = false; // Re-enable new game btn
        if (data && data.puzzle_board) {
            renderBoard(data.current_board, data.puzzle_board);
            showMessage(`بازی جدید با سطح ${difficultySelect.options[difficultySelect.selectedIndex].text} شروع شد!`, 'success');
            startTimer();
            toggleActionButtons(false);
        } else {
            showMessage('خطا در شروع بازی جدید. لطفاً دوباره تلاش کنید.', 'error');
            toggleActionButtons(false); // Re-enable if failed, except undo
            undoBtn.disabled = true;
        }
    }

    async function handleCheckGame() {
        showMessage('در حال بررسی جدول...', 'info');
        const data = await fetchAPI('/api/check_game', 'GET');
        if (data) {
            if (data.is_solved) {
                showMessage(data.message || 'تبریک! شما سودوکو را حل کردید!', 'success');
                stopTimer();
                toggleActionButtons(true);
            } else {
                showMessage(data.message || 'جدول هنوز کامل یا صحیح نیست.', 'error');
                 // Future: Could add logic to highlight incorrect cells if backend provides them
            }
        }
    }

    async function handleSolveGame() {
        if (!confirm('آیا مطمئن هستید که می‌خواهید راه‌حل نمایش داده شود؟ بازی فعلی شما تمام می‌شود.')) {
            return;
        }
        showMessage('در حال دریافت راه‌حل...', 'info');
        const data = await fetchAPI('/api/solve_game', 'GET');
        if (data && data.current_board) {
            renderBoard(data.current_board, initialPuzzle);
            showMessage('راه‌حل نمایش داده شد.', 'success');
            stopTimer();
            toggleActionButtons(true);
            undoStack = []; // Clear undo stack as game is over/solved
        } else {
            showMessage('خطا در دریافت راه‌حل.', 'error');
        }
    }

    async function handleHint() {
        showMessage('در حال دریافت راهنمایی...', 'info');
        const data = await fetchAPI('/api/hint', 'GET');
        if (data) {
            if (data.hint) {
                const { row, col, value } = data.hint;
                const oldValue = currentBoard[row][col];
                currentBoard[row][col] = value; // Update client model
                updateCellOnBoard(row, col, value, true);
                pushToUndoStack(row, col, oldValue, value);
                showMessage(data.message, 'info');

                // Check if board is now solved after hint
                if(data.current_board){ // Server sends updated board after hint
                    currentBoard = data.current_board; // Sync with server
                    const checkData = await fetchAPI('/api/check_game', 'GET');
                    if (checkData && checkData.is_solved) {
                         showMessage(checkData.message || 'تبریک! با این راهنمایی، سودوکو حل شد!', 'success');
                         stopTimer();
                         toggleActionButtons(true);
                    }
                }
            } else {
                showMessage(data.message || 'راهنمایی‌ای موجود نیست.', 'info');
            }
        }
    }

    // --- Initialization ---
    function init() {
        newGameBtn.addEventListener('click', handleNewGame);
        checkBtn.addEventListener('click', handleCheckGame);
        solveBtn.addEventListener('click', handleSolveGame);
        hintBtn.addEventListener('click', handleHint);
        undoBtn.addEventListener('click', handleUndo);

        document.addEventListener('click', (event) => {
            if (!boardContainer.contains(event.target) && !numbersPanel.contains(event.target) && selectedCell) {
                 if(selectedCell.element && !selectedCell.element.contains(event.target)) {
                    selectedCell.element.classList.remove('selected');
                    selectedCell = null;
                 }
            }
        });

        renderNumbersPanel();
        handleNewGame();
    }

    init();
});
