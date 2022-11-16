''' Visualization (graphs and stuff) function for Hello Wordle Bot
'''
import time
import random
import math
import matplotlib.pyplot as plt

class Visualization:
    ''' Class to display and update Hello World Bot's results
    '''

    def __init__(self):
        # Plot area. Defined here for the first time, but will be redefined on each call
        self.fig, (self.ax_wins, self.ax_turns) = plt.subplots(2, 1)

        # Move the resulting window to those coordinates
        self.fig.canvas.manager.window.wm_geometry("+%d+%d" % (10, 10))
        # Set the graph area size
        self.fig.set_size_inches(6, 8)

        # Move axes a little
        bbox = self.ax_wins.get_position()
        new_bbox = (bbox.x0, bbox.y0+0.15, bbox.width, bbox.height-0.05)
        self.ax_wins.set_position(new_bbox)

        bbox = self.ax_turns.get_position()
        new_bbox = (bbox.x0, bbox.y0+.07, bbox.width, bbox.height-0.05)
        self.ax_turns.set_position(new_bbox)

        # List and dict to store the current graphs
        self.wins_count = 0
        self.wins_graph = []

        # Gray area to show margin of error
        self.upper_error_margin = []
        self.lower_error_margin = []

        # 0 will be unused, 1..6 to represent game lengths
        self.turns = [0 for _ in range(7)]

    def reset_graphs(self):
        ''' Reset the pyplot figure (otherwise it would write on top of it)
        '''
        # clear the Axes
        self.ax_wins.clear()
        self.ax_turns.clear()

    def draw_wins(self):
        ''' Win rate graph'''
        y_axis = self.wins_graph
        x_axis = list(range(1, len(self.wins_graph) + 1))

        self.ax_wins.plot(x_axis, y_axis, color="#57ac78")

        self.ax_wins.fill_between(x_axis, self.upper_error_margin,
                                  self.lower_error_margin,
                                  color='gray', alpha=0.2)


        # Set axis limits
        self.ax_wins.set(ylim=(0, 1.05))

        # Set ticks as percents
        y_tick_vals = self.ax_wins.get_yticks()
        # This line doesn't do much, but pyplot scolds you if you don't do that
        self.ax_wins.set_yticks(y_tick_vals)
        self.ax_wins.set_yticklabels([f"{x:.0%}" for x in y_tick_vals])

    def draw_turns(self):
        ''' Game length bar graph '''
        x_axis = list(range(1, 7))
        heights = [turns_count/len(self.wins_graph) for turns_count in self.turns[1:]]
        self.ax_turns.bar(x_axis, heights, color="#4d0f28")

        # Set ticks as percents
        y_tick_vals = self.ax_turns.get_yticks()
        self.ax_turns.set_yticks(y_tick_vals)
        self.ax_turns.set_yticklabels([f"{x:.0%}" for x in y_tick_vals])

        # Add Bar labels
        max_height = max(heights)
        for rect_n, rect in enumerate(self.ax_turns.patches):
            y_value = rect.get_height()
            if y_value == 0:
                continue
            x_value = rect.get_x() + rect.get_width() / 2
            label = f"{y_value:.1%}\n({self.turns[rect_n+1]})"
            if y_value < max_height / 2:
                self.ax_turns.annotate(label,
                                       (x_value, y_value + .02),
                                       ha='center')
            else:
                self.ax_turns.annotate(label,
                                       (x_value, y_value - .02),
                                       ha='center', va="top", color="w")

    def draw_annotations(self):
        ''' Draw things like winning  rate and average game length
        '''
        plt.annotate("Winning rate:", (120, 430), xycoords='figure pixels',
                     fontsize=20)
        plt.annotate(f"{self.wins_graph[-1]:.1%}", (320, 430), xycoords='figure pixels',
                     fontsize=30, fontweight=800, color="#57ac78")
        plt.annotate("Average game length:", (90, 70), xycoords='figure pixels',
                     fontsize=20)
        all_turns_sum = sum([turn * count for turn, count in enumerate(self.turns)])
        ave_game = (all_turns_sum / sum(self.turns)) if sum(self.turns) > 0 else 0
        plt.annotate(f"{ave_game:.1f}", (430, 70),
                     xycoords='figure pixels',
                     fontsize=30, fontweight=800, color="#4d0f28")

    def make_calculations(self, win, turns):
        ''' Populate internal list of wins progression and turns aggregation
        '''
        # Win rate
        self.wins_count += win
        win_rate = self.wins_count / (len(self.wins_graph) + 1)
        self.wins_graph.append(win_rate)

        #  Margin of  error
        margin = 1.96 * math.sqrt(win_rate * (1-win_rate) /
                                  (len(self.wins_graph)+1))
        self.upper_error_margin.append(min(1, win_rate + margin))
        self.lower_error_margin.append(max(0, win_rate - margin))

        # For bar  chart
        if turns != -1:
            self.turns[turns] += 1

    def show(self, win, turns):
        ''' Draw the part of the visualizations
        '''
        self.reset_graphs()
        self.make_calculations(win, turns)

        self.draw_wins()
        self.draw_turns()
        self.draw_annotations()

        plt.draw()
        plt.pause(0.0001)

    @staticmethod
    def pause(duration):
        ''' Pause playing for "duration" seconds
        Useful in the end of the simulation to keep the graph n screen'''
        plt.pause(duration)

if  __name__ == "__main__":
    TEST_DATA_SIZE = 10
    WINS = [random.randint(0, 1) for _ in range(TEST_DATA_SIZE)]
    TURNS = [random.randint(i % 4 + 1, 6) for i in range(TEST_DATA_SIZE)]

    GRAPH = Visualization()
    for this_win, this_turn in zip(WINS, TURNS):
        GRAPH.show(this_win, this_turn)
        time.sleep(.1)
    GRAPH.pause(10)
