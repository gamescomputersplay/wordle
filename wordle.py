''' Wordle simulator
'''

import random
import time

class WordList:
    ''' Class to load the list of words from file
    '''

    def __init__(self, *files):
        # list of all the words
        self.word_list = []
        for file in files:
            with open(file, "r", encoding="UTF-8") as in_file:
                for line in in_file:
                    self.word_list.append(line.strip())

        # letter counts in all words in the list: {"a": 100, "b": 200, ...}
        self.letter_count = {}

        # words' scores: {"apple": 100, "fruit": 200} etc
        # score is the sum of all letters' frequences
        self.word_scores = {}
        
        # Gererate the scores
        self.gen_word_scores()
        
    def copy(self):
        ''' Copy of existing wordlist
        '''
        new_word_list = WordList()
        new_word_list.word_list = self.word_list.copy()
        new_word_list.word_scores = self.word_scores.copy()
        return new_word_list

    def get_random_word(self):
        ''' Return random word from the word list
        '''
        return random.choice(self.word_list)

    def get_hiscore_word(self):
        ''' return the word with the highest score
        '''
        best_word = ""
        best_score = 0
        for word in self.word_list:
            if self.word_scores[word] > best_score:
                best_score = self.word_scores[word]
                best_word = word
        return best_word

    def gen_letter_count(self):
        ''' calculate counts of all letters in the word_list
        return dict with such counts
        '''
        self.letter_count = {c:0 for c in "abcdefghijklmnopqrstuvwxyz"}
        for word in self.word_list:
            for letter in word:
                self.letter_count[letter] += 1

    def gen_word_scores(self):
        ''' Calculate scores for each word
        '''
        self.gen_letter_count()
        self.word_scores = {}
        for word in self.word_list:
            word_score = 0
            for letter in set(list(word)):
                word_score += self.letter_count[letter]
            self.word_scores[word] = word_score


class Guess:
    ''' Class for one guess attempt
    Contains the guessed word and list of results
    '''

    def __init__(self, guess_word, correct_word):
        self.word = guess_word
        # Set to True, but will be swithed
        self.guessed_correctly = True
        self.result = self.get_result(correct_word)

    def __str__(self):
        ''' String representation looks like: ducky: G__Y_
        G, Y, _ is for green / yellow / grey
        '''
        out = f"{self.word}: "
        for letter_result in self.result:
            if letter_result == 2:
                out += "G"
            elif letter_result == 1:
                out += "Y"
            if letter_result == 0:
                out += "_"
        return out


    def get_result(self, correct_word):
        ''' Given the guessed and the right word
        generate the list of letter results:
        0/1/2 meaning no/misplaced/correct
        '''
        result = []
        for i, guessed_char in enumerate(self.word):
            if self.word[i] == correct_word[i]:
                result.append(2)
            elif guessed_char in correct_word:
                result.append(1)
                self.guessed_correctly = False
            else:
                result.append(0)
                self.guessed_correctly = False
        return result


class Wordle:
    ''' Class representing one wordle game.
    methods include initiating a secret word,
    returning green/yellow/grey results,
    keeping track of guessed letters
    '''

    def __init__(self):
        # the word to guess
        self.correct_word = puzzle_words.get_random_word()
        # list of guesses so far
        self.guesses = []

    def __str__(self):
        out = f"::{self.correct_word}::"
        for i, guess in enumerate(self.guesses):
            out += f"\n{i+1}. {guess}"
        return out

    def guess(self, word):
        ''' One turn of the game
        get guessed word, add new Guess in guesses list
        if guessed correctly, return True, esle False
        '''
        self.guesses.append(Guess(word, self.correct_word))
        # Return True/False if you got the word right
        return self.guesses[-1].guessed_correctly


class Player:
    ''' Default player (random)
        Guesses a random word from the whole list
    '''

    def __init__(self, params):
        self.params = params
        # five lists: which letters ae allowed in each spot
        self.mask = [list('abcdefghijklmnopqrstuvwxyz') for _ in range(5)]
        # which letter has to be in the word (in non-specified places)
        self.must_use = set()
        # copy of the global wordset (we'll be removing unfit word from it)
        self.remaining_words = guessing_words.copy()

    def filter_word_list(self):
        ''' Removing words from the word list, that don't fit with
        what we know about the word (using mask and must_use)
        '''
        # I feel if would be faster to just create a new list instead of
        # deleting in-place
        new_words = WordList()
        for word in self.remaining_words.word_list:
            # check if all the letters from must_use are present
            for letter in self.must_use:
                if letter not in word:
                    break
            else:
                # check if the word complies to the mask
                for i, letter in enumerate(word):
                    if letter not in self.mask[i]:
                        break
                else:
                    new_words.word_list.append(word)
        new_words.word_scores = self.remaining_words.word_scores.copy()
        self.remaining_words = new_words


    def make_guess(self):
        ''' Pick the word from the list
        '''
        self.filter_word_list()
        if "scored" in self.params:
            if "recount" in  self.params:
                self.remaining_words.gen_word_scores()
            return self.remaining_words.get_hiscore_word()
        return self.remaining_words.get_random_word()

    def update_mask_green(self, guess):
        ''' Use Green result: delete all other letters in this mask
        '''
        for i, letter_result in enumerate(guess.result):
            if letter_result == 2: # green: right letter and place
                self.mask[i] = [guess.word[i],]

    def update_mask_grey(self, guess):
        ''' Use Grey results. Delete this letter from all masks
        '''
        letters_to_delete = []
        for i, letter_result in enumerate(guess.result):
            if letter_result == 0: # gray: no letter in this word
                letters_to_delete.append(guess.word[i])
        for one_mask in self.mask:
            for letter_to_delete in letters_to_delete:
                if letter_to_delete in one_mask:
                    del one_mask[one_mask.index(letter_to_delete)]

    def update_mask_yellow(self, guess):
        ''' Use Yellow
        1. Delete this letter in this mask
        2. Add it to "must use"
        '''
        # reset must_use (in case some became green)
        self.must_use = set()
        # Delete the letter in the same place in the mask
        for i, letter_result in enumerate(guess.result):
            if letter_result == 1:
                del self.mask[i][self.mask[i].index(guess.word[i])]
                self.must_use.add(guess.word[i])

    def update_mask(self, guess):
        ''' Combine mask updating functions
        according to parameters
        '''
        if "green" in self.params:
            self.update_mask_green(guess)
        if "grey" in self.params:
            self.update_mask_grey(guess)
        if "yellow" in self.params:
            self.update_mask_yellow(guess)


def play_one_game(params, quiet=True):
    ''' Playing one round of Wordle using player strategy
    from PlayerType
    '''

    game = Wordle()
    player = Player(params)
    done = False
    while not done:
        players_guess = player.make_guess()
        if game.guess(players_guess):
            done = True
        player.update_mask(game.guesses[-1])
    if not quiet:
        print (game)
    if game.guesses[-1].guessed_correctly:
        return game.guesses
    return -1 # This shouldn't happen


def parse_results(results):
    ''' Get couple of main statistics from the list of results
    '''
    frequencies = {}
    lengths = []
    complete = 0
    turns_sum = 0
    for result in results:
        length = len(result)
        lengths.append(length)
        if length in frequencies:
            frequencies[length] += 1
        else:
            frequencies[length] = 1
        turns_sum += length
        if length <= MAX_TURNS:
            complete += 1

    print (f"Winrate: {complete*100/len(results):.1f}%")

    if complete > 0:
        print (f"Average length: {turns_sum/len(results):.1f}")
    
    print (f"Median length: {sorted(lengths)[len(results) // 2]}")


def write_log(results):
    with open("wordle_log.txt", "w", encoding="utf-8") as fs:
        for result in results:
            for i, guess in enumerate(result):
                fs.write (guess.word)
                if i != len(result) - 1:
                    fs.write(" ")
                else:
                    fs.write("\n")
                
    

def simulation(params, number_of_runs):
    ''' play the game number_of_runs times
    return the list with all results
    '''
    print (f"Parameters: {params}, Runs: {number_of_runs}")
    simulation_results = []
    for _ in range(number_of_runs):
        simulation_results.append(play_one_game(params))

    parse_results(simulation_results)
    write_log(simulation_results)

def main():
    ''' launch the simulation
    '''
    start_time = time.time()

    # Parameters of the player:
    # green: uses green letters info
    # grey: uses grey letters info
    # yellow: uses yellow letters info
    # scored: weight words by the frequency of the words
    # recount: recalculate weights for every guess
    params = ["green", "yellow", "grey", "scored", "recount"]

    #play_one_game(params, quiet=False)

    simulation(params, 1000)

    print (f"Time: {time.time()-start_time}")

# Global Vars
# Word lists to use:
puzzle_words = WordList("words-guess.txt")
guessing_words = WordList("words-guess.txt", "words-all.txt")

# Game length (the game will go on, but it will affect the % of wins)
MAX_TURNS = 6

if __name__ == "__main__":
    main()
