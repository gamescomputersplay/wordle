''' Absurdle challenge mode bot
(https://qntm.org/files/absurdle/absurdle.html)
'''

import time
import random
import keyboard
import pyautogui
from PIL import Image
import pytesseract
pytesseract.pytesseract.tesseract_cmd = "C:\\install\\tesseract\\tesseract.exe"

import wordle
import wordle_tree
import absurdle_solver


def find_game(im):
    ''' Find the location of the game (area with guesses)
    from a screenshot
    '''

    black = (22, 22, 22)
    grey = (57, 57, 57)

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

    def find_kw(im, bottom):
        ''' Find the left and right edges (of the keyboard)
        '''
        px = im.load()
        j = bottom + 5
        for i in range(10, im.size[0]-10):
            if px[i,j] == grey and px[i-1,j] != grey and px[i-2,j] != grey \
               and px[i-3,j] != grey and px[i-4,j] != grey:
                left = i
                break
        for i in range(im.size[0]-10, 10, -1):
            if px[i,j] != grey and px[i-1,j] == grey and px[i-2,j] == grey \
               and px[i-3,j] == grey and px[i-4,j] == grey:
                right = i
                break
        return left, right
        
    top = find_edge(im, black)
    # It is actually the top edge of teh keyboard
    bottom = find_edge(im, grey)
    left, right = find_kw(im, bottom)

    return left, top, right, bottom 

def generate_click_coords(borders):
    ''' Generate dict of click coords, to click on letters:\
    {"a":(100,120), ...}
    '''
    left, top, right, bottom = borders

    letters = ["qwertyuiop", "asdfghjkl", "zxcvbnm", "="]
    letter_wid = (right - left) // 10
    letter_hgt = 59
    
    offset_x = [letter_wid // 2, letter_wid, letter_wid * 3 // 2, letter_wid * 5]
    offset_y = [int(letter_hgt * (i + 0.5)) for i in range(4)]

    coords = {}
    for row_n, (oy, letter_row) in enumerate(zip(offset_y, letters)):
        for col_n, letter in enumerate(letter_row):
            coords[letter] = (offset_x[row_n] + letter_wid * col_n + left,
                   offset_y[row_n] + bottom)
    return coords

def get_target_word(im, borders):
    ''' get the target word from the picture
    Uses Tesseract to read the text on the image
    '''
    left, top, right, bottom = borders
    target_box = left + 300, top + 180, right - 300, top + 210
    target_im = im.crop(target_box)
    target_raw = pytesseract.image_to_string(target_im)
    target_word = target_raw.split("Target word:")[1].strip().lower()
    filtered_target_word = ""
    for letter in target_word:
        if letter in "abcdefghijklmnopqrstuvwxyz":
            filtered_target_word += letter
    return filtered_target_word

def click_letter(letter, click_coords):
    ''' click the keyboard
    corner is the top left corner of the keybord (same as
    bottom left corner of the game)
    '''
    x, y = click_coords[letter]
    pyautogui.click(x, y)
    
def do_click_solution(solution, click_coords):
    ''' Do the clicking according to the solution
    '''
    for word in solution:
        # "=" stands for enter
        word_to_click = word + "="
        for letter in word_to_click:
            click_letter(letter, click_coords)
        time.sleep(.1)
    return

## These are functions to solve the Absurdle with a given Target word

def get_word_n(word, word_list):
    ''' Get the number of the word in the list
    Try both upper and lower just in case
    '''
    word_lower = word.lower()
    n = word_list.index(word_lower)
    if n is not None:
        return n
    word_upper = word.upper()
    return word_list.index(word_upper)

def get_one_guess(remaining, target_word_n, guess_words_ns, possible_answers, matrix):
    ''' Get one guess that will keep game in progress
    (target word is still in the remaining list)
    Done by just randomly trying different guesses
    '''
    count= 0
    while True:
        count += 1
        guess = random.choice(guess_words_ns)
        
        test_remaining = absurdle_solver.generate_remaining(
                    remaining, guess, possible_answers, matrix)
        if target_word_n in test_remaining \
           and len(test_remaining) < len(remaining) \
           and guess != target_word_n:
            break    
    return guess

def get_one_guess(remaining, target_word_n, guess_words_ns, possible_answers, matrix):
    ''' Get one guess that will keep game in progress
    (target word is still in the remaining list)
    Done by just randomly trying different guesses
    '''
    count= 0
    best_guess = None
    best_remaining = None
    while True:
        count += 1
        # it has  to be full list, using only remaining words
        # may result in no solution at all
        guess = random.choice(guess_words_ns)
        
        test_remaining = absurdle_solver.generate_remaining(
                    remaining, guess, possible_answers, matrix)
        if target_word_n in test_remaining \
           and len(test_remaining) < len(remaining) \
           and guess != target_word_n:
            
            # Keep best guess (produce shortest remaining list)
            if not best_guess:
                best_guess = guess
                best_remaining = len(test_remaining)
            elif len(test_remaining) < best_remaining:
                best_guess = guess
                best_remaining = len(test_remaining)

        # Out if we spend too much time and already have something
        if count > MIN_RANDOM_ATTEMPTS and best_guess:
            break    

    return best_guess

def get_winning_sequence(target_word_n, puzzle_word_ns,
                         guess_words_ns, possible_answers, matrix):
    ''' Given the target word, generate list of guesses,
    that leads to this word [n1, n2, n3, n4, target]
    '''
    remaining = puzzle_word_ns.copy()
    winning_seq = []
    while True:
        guess = get_one_guess(remaining, target_word_n,
                                 guess_words_ns, possible_answers, matrix) 
        winning_seq.append(guess)
        remaining = absurdle_solver.generate_remaining(
                    remaining, guess, possible_answers, matrix)
        if len(remaining) == 1:
            winning_seq.append(remaining[0])
            break
    return winning_seq

def one_game(word, puzzle_words, guessing_words, puzzle_word_ns,
             guess_words_ns, possible_answers, matrix):
    ''' get the target word, out the squence of words (text)
    '''
    
    target_word_n = get_word_n(word, puzzle_words.word_list)
    winning_seq_n = get_winning_sequence(target_word_n, puzzle_word_ns,
                                       guess_words_ns, possible_answers, matrix)
    wining_seq = []
    for word_n in winning_seq_n:
        wining_seq.append(guessing_words.word_list[word_n])
    return wining_seq


def main():
    '''
    '''
    t = time.time()

    # Init all variables
    puzzle_words = wordle.WordList("absurdle-guess.txt")
    #guessing_words = wordle.WordList("words-guess.txt", "words-all.txt") 
    guessing_words = wordle.WordList("absurdle-guess.txt") 
    possible_answers = wordle_tree.generate_all_possible_answers()
    possible_answers = absurdle_solver.sort_possible_answers_by_value(
                                                    possible_answers)

    matrix = wordle_tree.get_the_matrix(
        puzzle_words, guessing_words, possible_answers)

    puzzle_word_ns = [n for n in range(len(puzzle_words))]
    guess_words_ns = [n for n in range(len(guessing_words))]


    im = pyautogui.screenshot()
    #im.save("screen1.png")
    #im = Image.open("screen1.png")

    borders = find_game(im)
    print (f"Found the game at {borders}")
    click_coords = generate_click_coords(borders)

    for n in range(MAX_GAMES):
        print (f"\nGAME {n+1}\n=========")

        # Get the target word from screenshot
        im = pyautogui.screenshot()
        target_word = get_target_word(im, borders)
        print (target_word)

        # Game started
        solution = one_game(target_word, puzzle_words, guessing_words, puzzle_word_ns,
                 guess_words_ns, possible_answers, matrix)
        print (f"Solution: {solution}")
        do_click_solution(solution, click_coords)
        
        # Start the new game
        time.sleep(.4)
        click_letter("g", click_coords)
        
    print(time.time() - t)


# Try at least this many times until find the best guess
MIN_RANDOM_ATTEMPTS = 100

# How many games to play
MAX_GAMES = 100

# Run on F10
keyboard.add_hotkey('f10', main)
keyboard.wait('esc')
