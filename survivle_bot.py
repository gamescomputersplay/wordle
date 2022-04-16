''' Survivle bot
https://lazyguyy.github.io/survivle/
'''

import time
import random
import keyboard
import pyautogui
from PIL import Image

import wordle
import wordle_tree


def find_game(im):
    ''' Find the location of the game (area with guesses)
    from a screenshot
    '''

    kw_black = (34, 34, 34)
    white = (255, 255, 255)

    def find_edge_survivle(im, color, begins=True, only_first=False):
        ''' Find the top border (most pixels where "color" starts)
        begins=False to find where it ends
        Modified for Survivle
        '''
        # number of lines to test
        lines = 30
        # list of all occasions black turn gray
        found = {}
        
        wid, hgt = im.size
        px = im.load()
        
        for i in range(10, wid, wid // lines):
            for j in range(1, hgt):
                
                if begins and px[i,j] == color and px[i,j-1] == white or \
                   not begins  and px[i,j] == white and px[i,j-1] == color:
                    if j in found:
                        found[j] += 1
                    else:
                        found[j] = 1
                    if only_first:
                        break
                    
        maxcount = 0
        edge = None
        for j, count in found.items():
            if count > maxcount:
                maxcount = count
                edge = j
        return edge

    # top and bottom
    kw_top = find_edge_survivle(im, kw_black)
    kw_bottom = im.size[1] - find_edge_survivle(im.rotate(180), kw_black, only_first=True)
    print (kw_top, kw_bottom)
    
    # left and right
    px = im.load()
    j = kw_top
    for i in range(10, im.size[0]-10):
        if px[i,j] == white and px[i+1,j] == kw_black and \
           px[i+2,j] == kw_black and px[i+3,j] == kw_black:
            left = i+1
            break
    for i in range(im.size[0]-10, 10, -1):
        if px[i,j] == white and px[i-1,j] == kw_black and \
           px[i-2,j] == kw_black and px[i-3,j] == kw_black:
            right = i-1
            break
    
    return left, kw_top, right, kw_bottom

def generate_click_coords(borders):
    ''' Generate dict of click coords, to click on letters:\
    {"a":(100,120), ...}
    '''
    left, top, right, bottom = borders

    letters = ["qwertyuiop", "asdfghjkl", "=zxcvbnm"]
    letter_wid = (right - left) // 10
    letter_hgt = (bottom - top) // 3
    
    offset_x = [letter_wid // 2, letter_wid, letter_wid]
    offset_y = [int(letter_hgt * (i + 0.5)) for i in range(4)]

    coords = {}
    for row_n, (oy, letter_row) in enumerate(zip(offset_y, letters)):
        for col_n, letter in enumerate(letter_row):
            coords[letter] = (offset_x[row_n] + letter_wid * col_n + left,
                   offset_y[row_n] + top)
    return coords

def get_result_columns(borders):
    ''' Coordinates of columns with the game board,
    will be used to read answers
    '''
    left, _, right, _ = borders
    width = (right - left) * .7 / 4
    start = (right - left) * 0.15 + left
    coords = [int(start + width * i) for i in range(5)]
    return coords

def find_new_game_button(im, borders):
    ''' Find coords of the "new game" button
    This is quite a makeshift approach, it will not work for
    Daily Challenge (maybe for the best?)
    '''
    black = (26, 26, 26)
    white = (255, 255, 255)
    mid = (borders[0] + borders[2]) // 2
    i = mid
    
    count_whites = 0
    px = im.load()
    
    for j in range(borders[1] - 10, 10, -1):
        #print (i,j, px[i,j], count_whites)
        if px[i,j-1] == black and px[i,j] == white and px[i,j+1] == black:
            count_whites += 1
            continue
        if count_whites == 2 and px[i,j] != black:
            new_game_y = j+20
            break
    for i in range(mid, 0, -1):
        if px[i, new_game_y] == white:
            new_game_x = i
            break
    return new_game_x, new_game_y
        

def read_answer(im, borders, result_columns):
    ''' Look at the screenshot and read the result of teh last guess
    '''
    grey = (112, 128, 144)
    yellow = (255, 165, 0)
    green = (34, 139, 34)
    colors = [grey, yellow, green]
    
    result = []

    px = im.load()
    for col in range(5):
        i = result_columns[col]
        for j in range(borders[1]-1, 0 , -1):
            if px[i,j] in colors:
                result.append(colors.index(px[i,j]))
                break
    return tuple(result)
                
def click_letter(letter, click_coords):
    ''' click the keyboard
    corner is the top left corner of the keybord (same as
    bottom left corner of the game)
    '''
    x, y = click_coords[letter]
    pyautogui.click(x, y)
    
def click_word(word, click_coords):
    ''' Do the clicking according to the current word
    '''
    word_to_click = word + "="
    for letter in word_to_click:
        click_letter(letter, click_coords)
    time.sleep(.1)
    return
  


## These are the functions to actually get the guesses

def get_a_guess(attempts, puzzle_word_ns, guess_words_ns, matrix):
    ''' Get a "good" first guess. By good I means do attempts attempts
    and return one with the best (shortest) distribution
    '''
    best_guess = None
    best_distribution_len = None
    for n in range(attempts):
        guess_n = random.choice(guess_words_ns)
        dist = wordle_tree.get_distribution(puzzle_word_ns, guess_n, matrix)
        if best_guess is None or len(dist) < best_distribution_len:
            best_guess = guess_n
            best_distribution_len = len(dist)
    return best_guess, best_distribution_len

def get_remaining_puzzles(cur_puzzle, guess, answer, matrix):
    ''' Generate the list of valid secret words, given the current list
    and latest guess and answer
    '''
    new_list = []
    for word_n in cur_puzzle:
        if matrix[word_n][guess] == answer:
            new_list.append(word_n)
    return new_list

def words_to_numbers(words, full_list):
    ''' Return list of numbers of words in full_list
    Used to convert list of words into list of nunbers of those words
    '''
    numbers = []
    wordsset = set(words)
    for n, word in enumerate(full_list):
        if word in wordsset:
            numbers.append(n)
    return numbers

def play_one_game(puzzle_word_ns, guess_words_ns, puzzle_words, guessing_words,
                    possible_answers, matrix, borders, click_coords,
                    result_columns):
    ''' One Survivle game, returns turn count
    '''
    # Starting the game
    # Keep track of valid secret words
    remaining_puzzles = puzzle_word_ns
    # Keep track of valid allowes guesses
    remaining_guesses = guess_words_ns
    
    # Keep track of valid guesses
    # For that we need not numbers, but actual words, to do the filtering
    # by word mask. For that we use some stuff from Wordle modile
    player = wordle.Player(guessing_words)
    turn_count = 0
    
    while  True:

        # Choose random (but frombest from the 10 atyempts) word
        guess_n, guess_len = get_a_guess(
            ATTEMPTS, remaining_puzzles, remaining_guesses, matrix)
        guess = guessing_words.word_list[guess_n]
        print (f"\nGuess is {guess}")
        click_word(guess, click_coords)
        turn_count += 1
        
        # read answer
        im = pyautogui.screenshot()
        im.save("answer.png")
        answer = read_answer(im, borders, result_columns)
        print (f"Reply is {answer}")
        answer_n = possible_answers[answer]
        # out on correct guess
        if answer == (2,2,2,2,2):
            break

        # Purge the list of possible answers
        remaining_puzzles = get_remaining_puzzles(
            remaining_puzzles, guess_n, answer_n, matrix)
        print (f"Remaining puzzles ({len(remaining_puzzles)}): ", end = "")
        for word_n in random.sample(remaining_puzzles,
                                    min(len(remaining_puzzles), SHOW_REMAINING)):
            print (puzzle_words.word_list[word_n], end = " ")
        print("..." if len(remaining_puzzles) > SHOW_REMAINING else "")

        # Filter the guessing list. For that we reuse some functions from
        # wordle module.
        # We use just any (first) word from the remaining list,
        # because it will produce the correct "Guess" object
        guess_for_mask = wordle.Guess(guess,
                            puzzle_words.word_list[remaining_puzzles[0]])
        # use that Guess object to filter down the remaining list of guesses
        player.update_mask_with_guess(guess_for_mask)
        player.filter_word_list()
        remaining_guesses = words_to_numbers(player.remaining_words.word_list,
                                             guessing_words.word_list)
        print (f"Remaining guesses ({len(player.remaining_words)}): ", end = "")
        for word in random.sample(player.remaining_words.word_list,
                            min(len(player.remaining_words), SHOW_REMAINING)):
            print (word, end = " ")
        print("..." if len(player.remaining_words) > SHOW_REMAINING else "")

    return turn_count
    
def main():
    ''' Main function. Get screenshots and play
    Turned out to be a bit messy
    '''
    
    t = time.time()

    #  Finding the game on the screen
    im = pyautogui.screenshot()
    im.save("screen.png")
    #im = Image.open("screen.png")
    borders = find_game(im)
    print (f"Found game at: {borders}")
    im.crop(borders).save("cropped.png")
    click_coords = generate_click_coords(borders)
    result_columns = get_result_columns(borders)
    new_game_button = find_new_game_button(im, borders)
    
    # Initializing
    puzzle_words = wordle.WordList("survivle_secret.txt")
    guessing_words = wordle.WordList("survivle_secret.txt", "survivle_all.txt") 
    possible_answers = wordle_tree.generate_all_possible_answers()
    matrix = wordle_tree.get_the_matrix(
        puzzle_words, guessing_words, possible_answers)

    puzzle_word_ns = [n for n in range(len(puzzle_words))]
    guess_words_ns = [n for n in range(len(guessing_words))]

    results = []
    wins = 0
    for n in range(N_GAMES):

        print(f"\n\nGAME {n+1}\n======")   
        result = play_one_game(puzzle_word_ns, guess_words_ns, puzzle_words, guessing_words,
                possible_answers, matrix, borders, click_coords, result_columns)
        print(f"\nGame length: {result}")
        
        results.append(result)
        if result > 6:
            wins += 1

        time.sleep(.5)
        if n != N_GAMES - 1:
            pyautogui.click(new_game_button)
        time.sleep(.1)

    print (f"\n\nWinrate: {wins/N_GAMES}")
    print (f"Average: {sum(results)/N_GAMES}")
    print(time.time() - t)

# Games to play
N_GAMES = 10
# Examples of remaining words to show
SHOW_REMAINING = 8
# Attemots to find the best word
ATTEMPTS = 50

keyboard.add_hotkey('f10', main)
keyboard.wait('esc')

