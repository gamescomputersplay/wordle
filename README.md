# Wordle solver / simulator

This is a simple Python Wordle simulator that can use different strategies, play thousands of games to test those strategies (or 2315 if a strategy is deterministic).

## Source words
Words are stored in two files
* words-guess.txt are all the *secret words*
* words-all.txt are all *additional* words that program can use

## Simple approach + Strategies (wordle.py)

Strategies can be switched on and off in the “param” list

### “naive” or “basic” or “greedy” strategy
This is a default strategy based on the colors of letters in answers. This  one cannot be switched off, this is the basis for all others

### “scored"
Weigh words by the frequency of the words

###  "recount"
Recalculate weights for every guess. Obviously, it only makes sense if “scored" is on.

###   "position"
Use letter weights that also consider letters’ positions

### "easymode"
With this strategy the program doesn't use the word from a narrowed down list of possible answers, but instead tries to reuse green spaces to get more information about the word.

### Results
Strategies would get winning rate from 89% (naive) to 99.6% (“easymode” a.k.a. “ reuse green)”.

## Building answers tree (wordle_tree.py)

This is a different approach to solving this problem. We try to find the most efficient way to break down the answers space by guesses. We do it by building a tree, where nodes are guesses and branches – remaining possible answers.

We choose X best candidates for each node and after calculating the branch, keep the most one resulting in fewer guesses.
The best result is achieved with varying branching factors (see lines 87-94).
"Salet" is the third option in the root node, there is on option to override and set it on the beginning for max fast generation. In this case the program runs under an hour on a fast PC.

Result for this one is a 100% winning rate. Best average game length is 3.421 (same as 3b1b got in his video)

# Quordle Bot (quordle-bot.py)

Quordle (quordle.com) is a simultaneous Wordle on 4 boards. This solver plays the game from screenshots. Just launch the solver, open Quordle and press F10 to start it. 
The strategy is selected to be reasonably fast (1 second of calculations per game on average, not counting clicking/reaction time), with the winning rate somewhere between 99% and 100%.

# Absurdle Solver (absurdle-solver.py)

Absurdle (https://qntm.org/files/absurdle/absurdle.html) a.k.a "Evil Wordle" is a version of Wordle that does not have one secret word, but instead provides an answer that leaves the player farthest from the victory. This game is deterministic (no random elements, game answers only depend on player's guesses).
The Solver finds the 4-guess solution to the game (3-guess is impossible).

## Absurdle Challenge Bot (absurdle_challenge_bot.py)

Challenge  Mode of Absurdle gives the player the  target word. Player's goal is to manipulate the game into having that word as the final answer.
The bot plays the game from screenshots.
