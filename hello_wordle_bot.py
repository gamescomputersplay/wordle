''' Bot that plays Hello Wordle (https://hellowordl.net)
Only works in dark mode.
F10 to start reading the screen and playing the game
'''

import time
import pyautogui
import keyboard
from PIL import Image

import hello_wordle_sim
import hello_wordle_bot_vis

class WordleBot:
    ''' Class to keep main functions to interact with the game on screen: find the game,
    type word and read answer. And play a single game, of course.
    '''

    def __init__(self, use_screenshot=None):

        # This is for debugging, please ignore
        if use_screenshot is not None:
            screenshot = use_screenshot
        else:
            screenshot = pyautogui.screenshot()
            # screenshot.save("screen.png")

        # Find the game coordinates on the screenshot
        self.game_x, self.game_y = self.find_game(screenshot)
        self.word_length = len(self.game_x)

        if min(len(self.game_x), len(self.game_y)) < 4:
            raise RuntimeError("Can't find the game")

        print(f"Found {self.word_length}-letter Wordle game")
        print(f"at {self.game_x}, {self.game_y}")

        # Load the necessary data for solver
        self.secrets, self.guesses, self.data = \
            hello_wordle_sim.init_data(self.word_length)

        print("Wordle solver data loaded")

    @staticmethod
    def find_game(screenshot):
        ''' Given the screenshot, locate the Hello Wordle game
        return array of x and y coordinates to look for answers
        '''

        def find_grid(screenshot):
            ''' Find black-grey horizontal lines on the screenshot,
            return their coordinates.
            '''
            # Color samples to match
            black = (64, 64, 64)
            grey = (115, 115, 115)

            # Number columns to look at
            probes = 50
            # Dict to store matching results
            matches = {}

            pix = screenshot.load()
            # Analyze "probes" columns
            for i in range(0, screenshot.size[0], screenshot.size[0] // probes):

                # For each column, look at all pixels
                for j in range(3, screenshot.size[1] - 10):

                    # Particularly, look for
                    # (black, black, grey, grey, black, black) pixel pattern
                    for k in range(6):
                        if k in (2, 3) and pix[i, j + k] != grey:
                            break
                        elif k not in (2, 3) and pix[i, j + k] != black:
                            break
                    else:
                        # Pattern found
                        matches[j + 4] = matches.get(j + 4, 0) + 1

            return matches

        def validate_grid(matches_raw):
            ''' Given the found black-grey grid, eliminate noise and check validity
            Return empty list if invalid or list of 1st pixels if valid
            '''

            # Only keep the max matches. There might be false positives,
            # but it is unlikely there will be as many as tru positives
            max_value = max(list(matches_raw.values()))
            matches = {key:value for key, value in matches_raw.items() if value == max_value}

            # There should be an even number of lines (2 from each cell)
            if len(matches) % 2 == 1:
                return []

            # If all is fine, keep only odd matches (top/left coordinates of the cell)
            result = [key for n, key in enumerate(matches.keys()) if n % 2 == 0]

            return result

        matches_raw_y = find_grid(screenshot)
        matches_y = validate_grid(matches_raw_y)

        sideways = screenshot.transpose(Image.Transpose.ROTATE_270)

        matches_raw_x = find_grid(sideways)
        matches_x = validate_grid(matches_raw_x)

        return matches_x, matches_y

    def read_answer(self, turn, use_screenshot=None):
        ''' Read the result of turn "turn"
        '''
        if use_screenshot is not None:
            screenshot = use_screenshot
        else:
            screenshot = pyautogui.screenshot()
            #screenshot.save("screen.png")

        colors = {(162, 162, 162): 0,
                  (233, 198, 1): 1,
                  (87, 172, 120): 2}
        pix = screenshot.load()
        result = []
        for letter in range(self.word_length):
            found_pixel = pix[self.game_x[letter], self.game_y[turn]]
            if found_pixel not in colors:
                raise RuntimeError("Error reading the guess result")
            result.append(colors[found_pixel])
        return tuple(result)

    def type_word(self, word):
        ''' Type the word (+ Enter in the end)
        '''
        # I have no idea why it doesn't work without this one
        pyautogui.click(self.game_x[0], self.game_y[0])

        for letter in word:
            keyboard.press_and_release(letter)
        keyboard.press_and_release("Enter")

    def start_new_game(self):
        ''' Start a new game. It's just pressing Enter, actually
        '''
        # click in case focus is lost
        pyautogui.click(self.game_x[0], self.game_y[0])
        keyboard.press_and_release("Enter")

    def switch_to_15_again(self):
        ''' For 15-letter game: move the slider to 15 again
        '''
        from_x, from_y = self.game_x[0] + 235, self.game_y[0] - 40
        to_x, to_y = from_x + 180, from_y

        pyautogui.moveTo(from_x, from_y)
        pyautogui.dragTo(to_x, to_y, .3, button='left')
        #time.sleep(.5)

    def play_one_game(self, difficulty=0, strength=100):
        ''' Bot plays one game of Hello Wordle
        return number of turns to win or -1 if lost
        '''

        # We'll be deleting invalid items, so let's make a copy
        # of both word lists first
        secrets = self.secrets.copy()
        guesses = self.guesses.copy()

        for turn in range(6):

            if not secrets:
                print("EMPTY SECRETS")
                raise RuntimeError

            guess_n, _ = secrets.find_best_guess(guesses, self.data, strength=strength)
            guess = guesses.words[guess_n]
            print(f"{turn + 1}. ({len(secrets)} secrets remains). Guess: {guess} ")
            self.type_word(guess)

            # Pause to give Hello Wordle time to display the result
            time.sleep(.2)
            answer = self.read_answer(turn)

            # If we answer is all green: we are done
            if 0 not in answer and 1 not in answer:
                break

            # Only keep secret words that comply with the last guess and answer
            secrets.reduce_by_guess(guess_n, self.data.pos_answers[answer], self.data)
            # Remove secrets and guesses according to the chosen difficulty
            if difficulty != 0:
                guesses.reduce_by_difficulty(guess, answer, difficulty)
                secrets.reduce_by_difficulty(guess, answer, difficulty)

        else:
            return -1
        return turn + 1

def main():
    ''' Main simulation function
    Find the game, play the game repeatedly
    '''

    # Simulation settings
    runs = 1000
    strength = 1
    difficulty = 2

    # Variables to store results
    wins = []
    turns = []

    wordle_bot = WordleBot()
    graph = hello_wordle_bot_vis.Visualization()

    for game_n in range(runs):

        print(f"\nStarting game #{game_n + 1}")

        result = wordle_bot.play_one_game(strength=strength,
                                         difficulty=difficulty)

        if result > 0:
            print(f"Game won in {result} turns")
            wins.append(1)
            turns.append(result)
        else:
            wins.append(0)
            print("Game lost :(")

        print(f"Win rate: {sum(wins)/(game_n+1):.2%}, " +
              f"Average length: {0 if sum(wins) == 0 else sum(turns)/sum(wins):.2f}")
        graph.show(wins[-1], turns[-1] if result > 0 else -1)

        wordle_bot.start_new_game()

        # This is only needed for 12-15-letter games,
        # as Hello Wordle keeps resetting non-standard game length
        # wordle_bot.switch_to_15_again()

    print("\nDone")
    graph.pause(5)

if __name__ == "__main__":

    keyboard.add_hotkey('f10', main)
    keyboard.wait('esc')
