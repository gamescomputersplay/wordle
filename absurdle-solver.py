''' Absurdle solver
Go through top guesses to find shortest solutions (4 guesses) to Absurdle
(https://qntm.org/files/absurdle/absurdle.html)
'''

import wordle
import wordle_tree

import time


def answer_weight(answer):
    weight = 0
    weight += answer.count(2) * 10000
    weight += answer.count(1) * 1000
    weight += answer.count(0) * 100
    return weight

def sort_possible_answers_by_value(answers):
    ''' Sort possible answers by Absurdle's weight
    N of green yellow greys
    Then it should be compare from left to right, but if we reverse
    the initial list, it already works as is.
    '''
    
    answers = list(answers)
    answers.reverse()
    answers = sorted(answers, key = answer_weight)
    new_answers = {}
    for n, answer in enumerate(answers):
        new_answers[answer] = n
    return new_answers

def absurdle_answer(remaining_words, guess, possible_answers, matrix):
    ''' Return worst (as per absurdle rules) answer
    and count of remaining words for this answer
    given the remaining list and the guess
    '''
    answers = {i:0 for i in range(243)}
    words = {i:[] for i in range(243)}
    for n in remaining_words:
        answers[matrix[n][guess]] += 1
        words[matrix[n][guess]].append(guessing_words.word_list[n])
    worst_answer = -1
    highest_count = -1

    for n, count in answers.items():
        # This is <, not <= because
        # answers already sorted by worth, so earlier ones shoudl prevail
        # in case the count is the same
        if count >  highest_count:
            worst_answer = n
            highest_count = count
    return worst_answer, highest_count

def find_best_guesses(remaining_words, guess_list, n_guesses, possible_answers, matrix):
    ''' Find the guesses that generate smallest largest group.
    Return n_guesses best options
    '''
    best_guesses = []
    for guess in guess_list:
        new_remaining = absurdle_answer(remaining_words, guess,
                                        possible_answers, matrix)[1]
        if best_guesses:
            if new_remaining <  best_guesses[-1][1]:
                for n, (one_best_guess, one_best_remaining) in enumerate(best_guesses):
                    if new_remaining < one_best_remaining:
                        break
                best_guesses.insert(n, (guess, new_remaining))
                best_guesses = best_guesses[:n_guesses]
        else:
            best_guesses.append([guess, new_remaining])
    return best_guesses

def generate_remaining(remaining, guess, possible_answers, matrix):
    ''' Keep only valid guesses from remaining after guess
    '''
    answer = absurdle_answer(remaining, guess, possible_answers, matrix)[0]
    new_remaining = []
    for word in remaining:
        if matrix[word][guess] == answer:
            new_remaining.append(word)
    return new_remaining
    
def find_top_paths(prev_paths, branches,
                   puzzle_word_ns, guess_words_ns, possible_answers, matrix):
    ''' Given current paths (guesses so far), come up with the same number of paths
    branching at each one by the factor of branches
    '''
    total_best_guesses = []
    for prev_path in prev_paths:

        remaining = puzzle_word_ns.copy()
        for prev_guess in prev_path[:-1]:
            remaining = generate_remaining(remaining, prev_guess, possible_answers, matrix)

        best_guesses = find_best_guesses(remaining, guess_words_ns,
                                     branches, possible_answers, matrix)
        
        # This part is a bit messy, but basically what it does is to keep
        # top nest guesses generated by all previous guesses
        for best_guess in best_guesses:
            if total_best_guesses:
                if best_guess[-1] < total_best_guesses[-1][-1] \
                    or best_guess[-1] == 1:
                    for n, one_best_guess in enumerate(total_best_guesses):
                        if best_guess[-1] < one_best_guess[-1]:
                            break
                    new_guess = prev_path[:-1] + best_guess
                    total_best_guesses.insert(n, new_guess)
                    total_best_guesses = total_best_guesses[:len(prev_paths)]
            else:
                new_guess = prev_path[:-1] + best_guess
                total_best_guesses.append(new_guess)

    return total_best_guesses

def print_guesses(guesses, guessing_words, puzzle_word_ns, possible_answers, matrix):
    ''' Guesses come as [(guess1, guess2, n_of_remainingwords),...]
    Let's print them nicely, including final answer
    '''
    for guess in guesses:
        for nword in guess[:-1]:
            print(guessing_words.word_list[nword], end=" ")
        print(guess[-1], end=" ")
        if guess[-1] == 1:
            remaining = puzzle_word_ns.copy()
            for prev_guess in guess[:-1]:
                remaining = generate_remaining(remaining, prev_guess, possible_answers, matrix)
            print(":", guessing_words.word_list[remaining[0]])
        else:
            print ()
            
if __name__ == "__main__":

    t = time.time()
    
    puzzle_words = wordle.WordList("words-guess.txt")
    #guessing_words = wordle.WordList("words-guess.txt", "words-all.txt") 
    guessing_words = wordle.WordList("words-guess.txt") 
    possible_answers = wordle_tree.generate_all_possible_answers()
    possible_answers = sort_possible_answers_by_value(possible_answers)

    matrix = wordle_tree.get_the_matrix(
        puzzle_words, guessing_words, possible_answers)

    guess_words_ns = [n for n in range(len(guessing_words))]
    puzzle_word_ns = [n for n in range(len(puzzle_words))]

    TEST_WIDTH = 20

    # Level 1
    best_guesses_1 = find_best_guesses(puzzle_word_ns, guess_words_ns,
                                     TEST_WIDTH, possible_answers, matrix)
    print_guesses(best_guesses_1, guessing_words, puzzle_word_ns, possible_answers, matrix)
    
    #Level 2
    best_guesses_2 = find_top_paths(best_guesses_1, TEST_WIDTH,
                   puzzle_word_ns, guess_words_ns, possible_answers, matrix)
    print_guesses(best_guesses_2, guessing_words, puzzle_word_ns, possible_answers, matrix)

    #Level 3
    best_guesses_3 = find_top_paths(best_guesses_2, TEST_WIDTH,
                   puzzle_word_ns, guess_words_ns, possible_answers, matrix)
    print_guesses(best_guesses_3, guessing_words, puzzle_word_ns, possible_answers, matrix)

    print(time.time() - t)
