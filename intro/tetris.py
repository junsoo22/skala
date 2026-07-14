import random
import sys

import pygame

COLS = 10
ROWS = 20
CELL_SIZE = 30
BOARD_WIDTH = COLS * CELL_SIZE
BOARD_HEIGHT = ROWS * CELL_SIZE
SIDE_PANEL_WIDTH = 150
WINDOW_WIDTH = BOARD_WIDTH + SIDE_PANEL_WIDTH
WINDOW_HEIGHT = BOARD_HEIGHT

FALL_EVENT = pygame.USEREVENT + 1
FALL_INTERVAL_MS = 500

BLACK = (0, 0, 0)
GRAY = (40, 40, 40)
WHITE = (255, 255, 255)

# 각 테트로미노의 회전 상태별 (row, col) 오프셋
SHAPES = {
    "I": [
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 0), (1, 0), (2, 0), (3, 0)],
    ],
    "O": [
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    ],
    "T": [
        [(0, 0), (0, 1), (0, 2), (1, 1)],
        [(0, 1), (1, 0), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (0, 1)],
        [(0, 0), (1, 0), (2, 0), (1, 1)],
    ],
    "S": [
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
    ],
    "Z": [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
    ],
    "J": [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (0, 1), (1, 0), (2, 0)],
        [(0, 0), (0, 1), (0, 2), (1, 2)],
        [(0, 1), (1, 1), (2, 0), (2, 1)],
    ],
    "L": [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (1, 0), (2, 0), (2, 1)],
        [(0, 0), (0, 1), (0, 2), (1, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
    ],
}

SHAPE_COLORS = {
    "I": (0, 255, 255),
    "O": (255, 255, 0),
    "T": (160, 32, 240),
    "S": (0, 255, 0),
    "Z": (255, 0, 0),
    "J": (0, 0, 255),
    "L": (255, 165, 0),
}


class Piece:
    def __init__(self, shape_key):
        self.shape_key = shape_key
        self.rotation = 0
        self.row = 0
        self.col = COLS // 2 - 2

    def cells(self, rotation=None, row=None, col=None):
        rotation = self.rotation if rotation is None else rotation
        row = self.row if row is None else row
        col = self.col if col is None else col
        rotations = SHAPES[self.shape_key]
        offsets = rotations[rotation % len(rotations)]
        return [(row + dr, col + dc) for dr, dc in offsets]

    @property
    def color(self):
        return SHAPE_COLORS[self.shape_key]


def new_piece():
    return Piece(random.choice(list(SHAPES.keys())))


def create_board():
    return [[None for _ in range(COLS)] for _ in range(ROWS)]


def is_valid_position(board, cells):
    for row, col in cells:
        if col < 0 or col >= COLS or row >= ROWS:
            return False
        if row >= 0 and board[row][col] is not None:
            return False
    return True


def lock_piece(board, piece):
    for row, col in piece.cells():
        if row >= 0:
            board[row][col] = piece.color


def clear_full_lines(board):
    remaining_rows = [row for row in board if any(cell is None for cell in row)]
    cleared = ROWS - len(remaining_rows)
    for _ in range(cleared):
        remaining_rows.insert(0, [None for _ in range(COLS)])
    board[:] = remaining_rows
    return cleared


def try_move(board, piece, drow, dcol):
    new_cells = piece.cells(row=piece.row + drow, col=piece.col + dcol)
    if is_valid_position(board, new_cells):
        piece.row += drow
        piece.col += dcol
        return True
    return False


def try_rotate(board, piece):
    new_rotation = (piece.rotation + 1) % len(SHAPES[piece.shape_key])
    new_cells = piece.cells(rotation=new_rotation)
    if is_valid_position(board, new_cells):
        piece.rotation = new_rotation
        return True
    return False


def hard_drop(board, piece):
    while try_move(board, piece, 1, 0):
        pass


def draw_board(screen, board, piece, score, game_over, font):
    screen.fill(BLACK)

    for row in range(ROWS):
        for col in range(COLS):
            rect = pygame.Rect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            color = board[row][col]
            if color is not None:
                pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, GRAY, rect, 1)

    if not game_over:
        for row, col in piece.cells():
            if row >= 0:
                rect = pygame.Rect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(screen, piece.color, rect)
                pygame.draw.rect(screen, GRAY, rect, 1)

    score_text = font.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (BOARD_WIDTH + 10, 20))

    if game_over:
        over_text = font.render("GAME OVER", True, WHITE)
        screen.blit(over_text, (BOARD_WIDTH + 10, 60))

    pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Tetris")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 28)

    board = create_board()
    piece = new_piece()
    score = 0
    game_over = False

    pygame.time.set_timer(FALL_EVENT, FALL_INTERVAL_MS)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == FALL_EVENT and not game_over:
                if not try_move(board, piece, 1, 0):
                    lock_piece(board, piece)
                    score += clear_full_lines(board) * 100
                    piece = new_piece()
                    if not is_valid_position(board, piece.cells()):
                        game_over = True

            elif event.type == pygame.KEYDOWN and not game_over:
                if event.key == pygame.K_LEFT:
                    try_move(board, piece, 0, -1)
                elif event.key == pygame.K_RIGHT:
                    try_move(board, piece, 0, 1)
                elif event.key == pygame.K_DOWN:
                    try_move(board, piece, 1, 0)
                elif event.key == pygame.K_UP:
                    try_rotate(board, piece)
                elif event.key == pygame.K_SPACE:
                    hard_drop(board, piece)
                    lock_piece(board, piece)
                    score += clear_full_lines(board) * 100
                    piece = new_piece()
                    if not is_valid_position(board, piece.cells()):
                        game_over = True

        draw_board(screen, board, piece, score, game_over, font)
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
