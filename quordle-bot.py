''' Quordle bot (practice mode)
https://www.quordle.com/#/practice
Open the game, F10 to start playing
'''

import pyautogui
import keyboard
import random
import time

from PIL import Image

import wordle
import wordle_tree

def find_edge(im, color, begins=True):
    ''' Find the top border (most pixels where "color" starts)
    begins=False to find where it ends
    '''
    # number of lines to test
    lines = 30
    # list of all occasions black turn gray
    found = {}
    
    wid, hgt = im.size
    px = im.load()
    
    for i in range(10, wid, wid // lines):
        for j in range(1, hgt):
            if begins and px[i,j] == color and px[i,j-1] != color or \
               not begins  and px[i,j] != color and px[i,j-1] == color:
                if j in found:
                    found[j] += 1
                else:
                    found[j] = 1
    maxcount = 0
    edge = None
    for j, count in found.items():
        if count > maxcount:
            maxcount = count
            edge = j
    return edge
    
def find_game(im):
    ''' Find the location of the game (area with guesses)
    from a screenshot
    '''

    black = (17, 24, 39)
    blue = (22, 78, 99)

    top = find_edge(im, black, False)
    bottom = find_edge(im, blue, True)
    sideways = im.transpose(Image.ROTATE_270)
    right = find_edge(sideways, blue, False)
    left = find_edge(sideways, blue, True)

    return (left, top, right, bottom)

def get_quarters(im):
    ''' break down cropped image into quarters
    '''
    corners = [(0,0),  (im.size[0]//2-5, 0), (0, im.size[1]//2),
               (im.size[0]//2-5, im.size[1]//2)]
    quarters = []
    for x, y in corners:
        quarters.append(im.crop((x, y, x + im.size[0]//2,
                                y + im.size[1]//2)))
    return quarters

def color_diff(pix1, pix2):
    ''' Color different between 2 pixels)
    '''
    total = 0
    for p1, p2 in zip(pix1, pix2):
        total += abs(p2 - p1)
    return total

def read_board(im):
    ''' Receives image of one board. Returns list of
    answers in form of [(0,1,0,1,2), ... ]
    '''
    px = im.load()
    result = []

    columns = [1,3,5,7,9]
    columns_coords = [int(col / 10 * im.size[0]) for col in columns]

    # Color codes for gray, yellow, green 
    pix_colors = [(55, 65, 81), (255, 204, 0), (0, 204, 136)]

    for column in columns_coords:
        i = column
        for j in range(im.size[1]-1, 0, -1):
            
            pixel = tuple(px[i, j])
            
            found = False
            for n, pix_color in enumerate(pix_colors):
                if color_diff(pix_color, pixel) < 20:
                    result.append(n)
                    found = True
            if found:
                break

    return result

def get_answers(im):
    ''' Take a screenshot, crop to borders
    Read the answers. Keep only those for the turn "turn".
    Return them in a list
    '''
    quarters = get_quarters(im)
    answers = []
    for quarter in quarters:
        answers.append(read_board(quarter))

    return answers

def click_out_achievements(im, borders):
    ''' Search for green achievements popup.
    Click out of it if needed
    '''
    green = (22, 101, 52)
    top = find_edge(im, green, begins=True)
    # Green found - there is an achievement popup
    if top is not None:
        bottom = find_edge(im, green, begins=False)
        sideways = im.transpose(Image.ROTATE_270)
        right = find_edge(sideways, green, begins=False)
        close_popup = (borders[0] + right - (bottom - top) // 2,
                       borders[1] + top + (bottom - top) // 2)
        print ("Clicking out of the popup")
        pyautogui.click(close_popup)
        time.sleep(.5)
        return True
    return False

def did_we_lose(im, borders):
    ''' Check if we lost on the end game screen, by looking for red pixels
    (Because I can't read the answer to the 9th guess)
    '''
    red = (232, 18, 36)
    results_area_coords = ((borders[0] + borders[2]) // 2 - 50, borders[3],
                   (borders[0] + borders[2]) // 2 + 50, borders[3] + 100)
    results_area = im.crop(results_area_coords)
    results_area.save("results.png")
    px = results_area.load()
    for i in range(0, results_area.size[0], 10):
        for j in range(0, results_area.size[1], 10):
            if px[i, j] == red:
                return True
    return False
    

def click_letter(letter, click_coords):
    ''' click the keyboard
    corner is the top left corner of the keybord (same as
    bottom left corner of the game)
    '''
    x, y = click_coords[letter]
    pyautogui.click(x, y)

def generate_click_coords(corner):
    ''' Generate dict of click coords, to click on letters:\
    {"a":(100,120), ...}
    '''
    corner_x, corner_y = corner
    letters = ["qwertyuiop", "asdfghjkl", "zxcvbnm="]
    offset_x = [41, 73, 140]
    offset_y = [40, 115, 185]
    size = (68, 71)
    coords = {}
    for row_n, (oy, letter_row) in enumerate(zip(offset_y, letters)):
        for col_n, letter in enumerate(letter_row):
            coords[letter] = (offset_x[row_n] + size[0]*col_n + corner_x,
                   offset_y[row_n] + corner_y)
    return coords

def reduce_guesses(remaining_guesses, guess, answers, matrix):
    ''' Filter the list of potential remaining words
    '''
    for i, remaining_guess in enumerate(remaining_guesses):

        # it if is already None - skip
        if remaining_guess is None:
            continue

        # if answer is (22222), remove this list
        if answers[i] == 242:
            remaining_guesses[i] = None
            continue

        # otherwise filter which words it still can be
        new_remaining = set()
        for secret in remaining_guess:
            if matrix[secret][guess] == answers[i]:
                new_remaining.add(secret)
        remaining_guesses[i] = new_remaining

def find_best_guess(remaining_guesses, puzzle_word_ns, matrix):
    ''' given the list of possibke remaining words for all boards,
    find which word is the best way to go
    '''
    # if one of them is narrowed to 1 - return it
    for remaining_guess in remaining_guesses:
        if remaining_guess is not None and len(remaining_guess) == 1:
            return list(remaining_guess)[0]

    longest_dist = 0
    best_word = None

    # Only select remaining lists smaller than MAX_SELECTED
    # bigger number is slower, but more accurate
    MAX_SELECTED = 100
    # minimum selected words, to start using full list
    # smaller is faster, but less accurate
    MIN_USE_FULL_LIST = 100
    
    # All combined remaining guesses
    all_remaining_guesses = set()
    # Combined guesses from lists of <MAX_SELECTED
    selected_remaining_guesses = set()
    
    for remaining_guess in remaining_guesses:
        if remaining_guess is not None:
            all_remaining_guesses = all_remaining_guesses.union(remaining_guess)
            if len(remaining_guess) < MAX_SELECTED:
                selected_remaining_guesses = selected_remaining_guesses.union(remaining_guess)

    # If all lists are > MAX_SELECTED, just pick a random word
    if not selected_remaining_guesses:
        return random.choice(list(all_remaining_guesses))
    
    if len(all_remaining_guesses) < MIN_USE_FULL_LIST:
        candidates = all_remaining_guesses
    else:
        candidates = selected_remaining_guesses
        
    for candidate in candidates:
        total_dist = 0
        for remaining_guess in remaining_guesses:
            if remaining_guess is not None:
                dist = wordle_tree.get_distribution(remaining_guess, candidate, matrix)
                total_dist += len (dist)
        if total_dist > longest_dist or best_word is None:
            best_word = candidate
            longest_dist = total_dist

    return best_word

def play_one_game(borders, matrix, puzzle_words, click_coords):
    ''' Play one game of Quordle
    '''
    N = 4

    puzzle_word_ns = [n for n in range(len(puzzle_words))]    
    possible_answers = wordle_tree.generate_all_possible_answers()
    remaining_guesses = [set(puzzle_word_ns) for _ in range(N)]
    turns_count = [1 for _ in range(N)]
    is_solved = [False for _ in range(N)]
    
    while True:

        # Pick a guessing word
        if max(turns_count) == 1:
            guess = random.choice(puzzle_word_ns)
        else:
            guess = find_best_guess(remaining_guesses, puzzle_word_ns, matrix)
        guess_word = puzzle_words.word_list[guess]
        print (f"\nGuess word: {guess_word}")
        
        for letter in guess_word + "=":
            click_letter(letter, click_coords)
        time.sleep(.3)

        # I can't read the results of 9th guess
        # I assume if there was only one option left, I must have won
        # Otherwise I lost
        if max(turns_count) == 9:
            time.sleep(.2)
            im = pyautogui.screenshot()

            if did_we_lose(im, borders):
                print ("I think I lost")
                return 10
            else:
                print ("I think I won")
                break


        # Read the screen for answers
        im = pyautogui.screenshot()
        im = im.crop(borders)

        while click_out_achievements(im, borders):
            im = pyautogui.screenshot()
            im = im.crop(borders)
        answers = get_answers(im)
        print (f"Answers: {answers}")
        
        # Encode them into 0-242 format
        coded_answers = [possible_answers[tuple(answer)]
                         if answer is not None else None
                         for answer in answers]
        #print (f"Encoded answers: {coded_answers}")

        # Reduce the remaining guesses
        reduce_guesses(remaining_guesses, guess, coded_answers, matrix)

        # Mark solved ones
        for n in range(N):
            if coded_answers[n] == 242 or not remaining_guesses[n] \
               or len(remaining_guesses[n]) == 0:
                is_solved[n] = True

        # Game over if solved out
        if all(is_solved):
            break

        # Keep track of counting attempts   
        for i, solved in enumerate(is_solved):
            if not solved:
                turns_count[i] += 1

        # Print the size of teh remaining options
        print ("Remaining options:",
               [len(one_rem_guess)
                if one_rem_guess is not None else "-"
                for one_rem_guess in remaining_guesses])
        

    print (f"\nResults: {turns_count}")
    return max(turns_count)

def main():
    ''' Main function. read the screen, find the game
    play the game
    '''
    puzzle_words = wordle.WordList("quordle-guess.txt")
    possible_answers = wordle_tree.generate_all_possible_answers()
    
    matrix = wordle_tree.get_the_matrix(
                            puzzle_words, puzzle_words, possible_answers)
    
    im = pyautogui.screenshot()
    
    # Find the game on the screen
    borders = find_game(im)
    print (f"Found game at: {borders}")
    # Calculate where keys on the keyboard are
    click_coords = generate_click_coords((borders[0], borders[3]))

    wins = 0

    for game in range(MAX_GAMES):
        
        print (f"\nGAME {game+1}\n=======")
        result = play_one_game(borders, matrix, puzzle_words, click_coords)

        if result <= 9:
            wins += 1
        print (f" Wins: {wins}/{game+1}, {wins/(game+1):.1%}")

        # Click "New game"
        if game != MAX_GAMES - 1:
            pyautogui.click((borders[0]+borders[2]) // 2, borders[1]+100)
            time.sleep(.3)

# How many games to play
MAX_GAMES = 10


# Run on F10
keyboard.add_hotkey('f10', main)
keyboard.wait('esc')
